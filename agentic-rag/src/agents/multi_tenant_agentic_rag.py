"""Multi-tenant Agentic RAG - Dynamic company support."""

import json
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.config import settings
from src.config.company_manager import company_manager
from src.rag.multi_tenant_retrieval import MultiTenantRetriever, format_documents_for_prompt
from src.tools.leave_management import (
    check_leave_balance,
    apply_leave,
    get_holiday_calendar,
    calculate_working_days_tool,
    get_leave_history
)
from src.tools.email_tool import send_email
from src.tools.calendar_tool import (
    get_upcoming_holidays,
    is_working_day,
    get_next_working_day,
    get_month_info
)
from src.tools.hr_approval_tool import (
    submit_leave_request,
    check_leave_request_status,
    get_my_leave_requests,
)
from src.tools.onboarding_journey_tool import (
    get_onboarding_progress,
    complete_onboarding_step,
)


class MultiTenantAgenticRAG:
    """
    Multi-tenant Agentic RAG system.
    
    Supports multiple companies with isolated knowledge bases.
    Each company can upload their own policies and get customized responses.
    """
    
    def __init__(self):
        """Initialize the multi-tenant agentic RAG."""
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.1,
            max_tokens=4096,
            request_timeout=60,
        )
        self.retriever = MultiTenantRetriever()
        # Cache (tools, system_prompt) per company_id
        self._company_cache: Dict[str, Tuple[List, str]] = {}
        self.metrics = {
            "total_queries": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "tool_calls": 0,
            "companies_served": set()
        }
    
    def _create_tools(self, company_id: str) -> List:
        """Create company-specific tools."""
        
        @tool
        def query_company_policy(query: str) -> str:
            """
            Search company policy documents for specific information.
            
            Use this tool to find information about:
            - Leave policies (casual, sick, earned leave)
            - Working hours and attendance
            - Holiday calendar
            - Company procedures and rules
            - Any other company policy information
            
            Args:
                query: The specific question or topic to search for
                
            Returns:
                Relevant information from policy documents
            """
            try:
                documents = self.retriever.retrieve(
                    query=query,
                    company_id=company_id,
                    k=5
                )
                
                if not documents:
                    return f"No relevant policy information found for {company_id}. Please contact HR."
                
                return format_documents_for_prompt(documents)
            
            except Exception as e:
                logger.error(f"Error querying policy for {company_id}: {e}")
                return f"Error searching policy documents: {str(e)}"
        
        return [
            query_company_policy,
            tool(check_leave_balance),
            tool(apply_leave),
            tool(get_holiday_calendar),
            tool(calculate_working_days_tool),
            tool(get_leave_history),
            tool(send_email),
            tool(get_upcoming_holidays),
            tool(is_working_day),
            tool(get_next_working_day),
            tool(get_month_info),
            tool(submit_leave_request),
            tool(check_leave_request_status),
            tool(get_my_leave_requests),
            tool(get_onboarding_progress),
            tool(complete_onboarding_step),
        ]

    def _get_company_setup(self, company_id: str) -> Tuple[List, str]:
        """Return cached (tools, system_prompt) for a company."""
        if company_id in self._company_cache:
            return self._company_cache[company_id]

        company = company_manager.get_company(company_id)
        company_name = company.company_name if company else company_id

        # Create tools first so we can include their schemas in the prompt
        tools = self._create_tools(company_id)

        # Build a concise tool reference for the JSON calling instructions
        tool_lines = []
        for t in tools:
            try:
                params = ", ".join(
                    f"{k}: {v.get('type', 'string')}"
                    for k, v in (t.args or {}).items()
                )
            except Exception:
                params = "..."
            first_line = (t.description or "").split("\n")[0].strip()
            tool_lines.append(f"  {t.name}({params}) — {first_line}")
        tool_listing = "\n".join(tool_lines)

        system_prompt = f"""You are a professional HR assistant for {company_name}. You help employees with HR queries, leave management, and onboarding guidance.

RESPONSE RULES — follow strictly:
- Use a formal, professional tone at all times.
- Present complete, final answers. Never say "I will look that up", "details are on the way", "please wait", or any placeholder phrase.
- When you need data, call the appropriate tool silently and respond only with the final answer once you have the result.
- If information cannot be retrieved, say so clearly and direct the employee to HR.

LEAVE APPLICATION WORKFLOW:
When an employee requests leave: first retrieve the relevant policy, confirm their balance is sufficient, then submit the leave request. If the balance is insufficient explain and suggest alternatives. Always confirm submission with the request ID.

ONBOARDING QUERIES:
Retrieve the employee's onboarding progress and present the day-by-day plan showing completed and pending steps. Recommend the next pending step.

POLICY QUERIES:
Always retrieve policy information from {company_name}'s uploaded documents before answering. Never fabricate or assume policy details.

TOOL CALLING FORMAT:
When you need to retrieve data or perform an action, respond with ONLY the following JSON — no surrounding text, no explanation:
{{"call": "<tool_name>", "args": {{"<param>": "<value>"}}}}

After you receive the tool result, provide your complete final answer in plain text.

Available tools:
{tool_listing}"""

        self._company_cache[company_id] = (tools, system_prompt)
        return tools, system_prompt

    def _run_tool_loop(
        self,
        messages: List,
        tools: List,
        max_iterations: int = 8,
    ) -> Tuple[AIMessage, List[str]]:
        """
        JSON-based ReAct loop — does NOT use Groq's bind_tools / tool_calls API.

        The LLM is instructed (via the system prompt) to emit a plain JSON object
        when it wants to call a tool, or plain text when it has a final answer.
        We parse that JSON ourselves, execute the tool, and feed the result back
        as a HumanMessage.  This approach is model-agnostic and permanently
        eliminates the tool_use_failed / model_decommissioned class of errors.
        """
        tool_map = {t.name: t for t in tools}
        tools_used: List[str] = []
        current_messages = list(messages)
        last_response = AIMessage(content="I was unable to process your request. Please contact HR directly.")

        for _ in range(max_iterations):
            response: AIMessage = self.llm.invoke(current_messages)
            last_response = response
            content = response.content.strip() if isinstance(response.content, str) else ""

            tool_call_data = self._extract_tool_call(content)
            if tool_call_data and tool_call_data.get("call") in tool_map:
                tool_name = tool_call_data["call"]
                tool_args = tool_call_data.get("args", {})
                tools_used.append(tool_name)
                self.metrics["tool_calls"] += 1
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                    tool_result = str(result)
                except Exception as e:
                    logger.warning(f"Tool '{tool_name}' raised: {e}")
                    tool_result = f"Tool error: {str(e)}"

                current_messages.append(AIMessage(content=content))
                current_messages.append(
                    HumanMessage(content=f"[Tool result: {tool_name}]\n{tool_result}")
                )
            else:
                # Plain-text response — this is the final answer
                break

        return last_response, tools_used

    @staticmethod
    def _extract_tool_call(content: str) -> Optional[dict]:
        """
        Extract a JSON tool-call dict from LLM output.

        Handles the common cases:
        - entire response is a JSON object
        - JSON object is embedded somewhere in the text (e.g. prefixed by markdown)
        Returns None when no valid tool-call JSON is found.
        """
        if not content:
            return None

        # Fast path: entire content is a JSON object beginning with '{'
        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict) and "call" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

        # Slow path: find the outermost JSON object that contains a "call" key
        for key_str in ('"call"', '"call" :'):
            pos = content.find(key_str)
            if pos == -1:
                continue
            start = content.rfind("{", 0, pos)
            if start == -1:
                continue
            depth = 0
            for i in range(start, len(content)):
                ch = content[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            parsed = json.loads(content[start : i + 1])
                            if isinstance(parsed, dict) and "call" in parsed:
                                return parsed
                        except json.JSONDecodeError:
                            pass
                        break
        return None

    def query(
        self,
        query: str,
        company_id: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a query for a specific company.

        Args:
            query: User's question or request
            company_id: Company identifier
            session_id: Optional session identifier
            context: Optional context (e.g., employee_id)

        Returns:
            Dictionary containing answer, tools used, and metadata
        """
        try:
            self.metrics["total_queries"] += 1
            self.metrics["companies_served"].add(company_id)

            # Verify company exists
            company = company_manager.get_company(company_id)
            if not company:
                return {
                    "answer": f"Company '{company_id}' not found. Please ensure the company has been set up and policies have been uploaded.",
                    "company_id": company_id,
                    "status": "error",
                    "error": "Company not found",
                }

            tools, system_prompt = self._get_company_setup(company_id)

            # Optionally prefix the query with the employee ID
            if context and context.get("employee_id"):
                enhanced_query = f"[Employee ID: {context['employee_id']}] {query}"
            else:
                enhanced_query = query

            # Build initial message list: system prompt + user query.
            # We use a clean [SystemMessage, HumanMessage] sequence on every
            # call so the model always sees the instructions at position 0,
            # which is the format llama-3.3-70b-versatile expects.
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=enhanced_query),
            ]

            response, tools_used = self._run_tool_loop(messages, tools)

            # Extract text — handle both string and list content (Gemini format)
            if isinstance(response.content, list):
                answer = response.content[0].get("text", "") if response.content else ""
            else:
                answer = response.content

            self.metrics["successful_responses"] += 1
            logger.info(
                f"Query answered for {company_id}: {query[:50]}… "
                f"(tools: {', '.join(tools_used) if tools_used else 'none'})"
            )

            return {
                "answer": answer,
                "company_id": company_id,
                "company_name": company.company_name,
                "tools_used": tools_used,
                "session_id": session_id or "default",
                "confidence": 0.9 if tools_used else 0.7,
                "status": "success",
            }

        except Exception as e:
            import traceback
            logger.error(f"Error in multi-tenant agentic RAG: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.metrics["failed_responses"] += 1

            return {
                "answer": "I encountered an error while processing your request. Please try again or contact HR.",
                "company_id": company_id,
                "tools_used": [],
                "session_id": session_id,
                "status": "error",
                "error": str(e),
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            **{k: v for k, v in self.metrics.items() if k != "companies_served"},
            "companies_served": len(self.metrics["companies_served"]),
            "success_rate": (
                self.metrics["successful_responses"] / self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0 else 0
            ),
        }


# Global instance
multi_tenant_agent = MultiTenantAgenticRAG()
