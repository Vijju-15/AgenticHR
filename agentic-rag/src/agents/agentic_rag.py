"""Agentic RAG - Tool-augmented agent using LangGraph."""

from typing import Dict, Any, List, Optional, Annotated
from loguru import logger
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from src.config import settings
from src.rag.retrieval import DocumentRetriever, format_documents_for_prompt
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


class AgenticRAG:
    """
    Agentic RAG system with tool calling capabilities.
    
    This agent can:
    1. Answer questions from the knowledge base
    2. Perform actions using tools (apply leave, send emails, etc.)
    3. Make multi-step plans to accomplish complex tasks
    """
    
    def __init__(self):
        """Initialize the agentic RAG."""
        self.llm = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.1,
            max_tokens=4096
        )
        self.retriever = DocumentRetriever()
        self.tools = self._create_tools()
        self.agent = self._create_agent()
        self.metrics = {
            "total_queries": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "tool_calls": 0,
            "avg_tools_per_query": 0
        }
    
    def _create_tools(self) -> List:
        """Create and register tools for the agent."""
        
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
                documents = self.retriever.retrieve(query, k=5)
                
                if not documents:
                    return "No relevant policy information found. Please contact HR at hr@techcorp.com"
                
                return format_documents_for_prompt(documents)
            
            except Exception as e:
                logger.error(f"Error querying policy: {e}")
                return f"Error searching policy documents: {str(e)}"
        
        # Return all tools
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
            tool(get_month_info)
        ]
    
    def _create_agent(self):
        """Create the ReAct agent with tools."""
        
        system_prompt = """You are an intelligent HR assistant for TechCorp Inc. You help employees with HR-related queries and tasks.

YOUR CAPABILITIES:
1. **Information Retrieval**: Search company policies and provide accurate information
2. **Leave Management**: Check balances, apply leave, view history
3. **Calendar Information**: Check holidays, working days, and calendar details
4. **Email Notifications**: Send emails when required (automatically done for leave applications)

DECISION-MAKING PROCESS:
1. **Analyze the Request**:
   - Is it a question? → Use query_company_policy tool
   - Is it an action? → Use appropriate action tools
   - Is it ambiguous? → Ask clarifying questions

2. **Tool Selection Rules**:
   - query_company_policy: For policy questions, rules, procedures
   - check_leave_balance: When user asks about remaining leaves
   - apply_leave: When user wants to apply for leave
   - get_leave_history: When user asks about past leaves
   - get_holiday_calendar / get_upcoming_holidays: For holiday information
   - is_working_day / get_next_working_day: For checking specific dates
   - calculate_working_days_tool: To calculate days between dates
   - send_email: Only when explicitly requested (leave applications auto-send)

3. **Multi-Step Actions**:
   For complex requests like "apply leave for tomorrow":
   Step 1: Verify working day status if needed
   Step 2: Check leave balance
   Step 3: Apply leave if balance is sufficient
   Step 4: Confirm with user

GUIDELINES:
- Always explain what you're doing before using tools
- For leave applications, confirm all details are correct
- If information is missing, ask the user
- Be friendly and professional
- If unsure, ask clarifying questions
- Always verify critical information from policy documents

EXAMPLE INTERACTIONS:

Q: "How many casual leaves do I have?"
A: Let me check your leave balance.
[Uses check_leave_balance tool]

Q: "What are the holidays this month?"
A: I'll get the holiday calendar for you.
[Uses get_upcoming_holidays tool]

Q: "Apply sick leave for tomorrow"
A: I'll help you apply for sick leave. Let me first check if tomorrow is a working day and verify your leave balance.
[Uses is_working_day, check_leave_balance, then apply_leave]

Q: "What's the leave policy?"
A: Let me search the leave policy for you.
[Uses query_company_policy tool]

Remember: Be helpful, accurate, and always verify information from official policy documents."""
        
        # Create agent with memory
        memory = MemorySaver()
        
        agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_modifier=system_prompt,
            checkpointer=memory
        )
        
        return agent
    
    def query(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a query using the agentic RAG.
        
        Args:
            query: User's question or request
            session_id: Optional session identifier
            context: Optional context (e.g., employee_id)
            
        Returns:
            Dictionary containing answer, tools used, and metadata
        """
        try:
            self.metrics["total_queries"] += 1
            
            # Enhance query with context if provided
            if context and context.get("employee_id"):
                enhanced_query = f"[Employee ID: {context['employee_id']}] {query}"
            else:
                enhanced_query = query
            
            # Configure thread for conversation continuity
            config = {
                "configurable": {
                    "thread_id": session_id or "default"
                }
            }
            
            # Invoke agent
            response = self.agent.invoke(
                {"messages": [("user", enhanced_query)]},
                config=config
            )
            
            # Extract response and tools used
            messages = response["messages"]
            final_message = messages[-1]
            answer = final_message.content
            
            # Track tool usage
            tools_used = []
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tools_used.append(tool_call["name"])
                        self.metrics["tool_calls"] += 1
            
            # Update metrics
            if tools_used:
                self.metrics["avg_tools_per_query"] = (
                    (self.metrics["avg_tools_per_query"] * (self.metrics["total_queries"] - 1) + len(tools_used))
                    / self.metrics["total_queries"]
                )
            
            self.metrics["successful_responses"] += 1
            
            logger.info(
                f"Agentic RAG answered query: {query[:50]}... "
                f"(Tools used: {', '.join(tools_used) if tools_used else 'none'})"
            )
            
            return {
                "answer": answer,
                "tools_used": tools_used,
                "session_id": session_id or "default",
                "confidence": 0.9 if tools_used else 0.7,  # Higher confidence when tools are used
                "tool_calls_count": len(tools_used)
            }
        
        except Exception as e:
            logger.error(f"Error in agentic RAG: {e}")
            self.metrics["failed_responses"] += 1
            
            return {
                "answer": f"I encountered an error while processing your request. Please try again or contact HR at hr@techcorp.com. Error: {str(e)}",
                "tools_used": [],
                "session_id": session_id,
                "error": str(e)
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful_responses"] / self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0 else 0
            )
        }


# Convenience function for testing
def test_agentic_rag():
    """Test the agentic RAG with sample queries."""
    agent = AgenticRAG()
    
    test_queries = [
        "How many casual leaves do I get per year?",
        "Check my leave balance for employee EMP123",
        "Apply sick leave for EMP123 from 2024-12-01 to 2024-12-03 due to flu",
        "What are the holidays in December?",
        "Is 2024-12-25 a working day?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        response = agent.query(query, context={"employee_id": "EMP123"})
        
        print(f"\nAnswer: {response['answer']}")
        print(f"Tools Used: {response.get('tools_used', [])}")
        print(f"Confidence: {response.get('confidence', 0):.2f}")


if __name__ == "__main__":
    test_agentic_rag()
