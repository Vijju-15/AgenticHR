"""Conversational RAG - Baseline implementation without tools."""

from typing import Dict, Any, List, Optional
from loguru import logger
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.config import settings
from src.rag.retrieval import DocumentRetriever, format_documents_for_prompt


class ConversationalRAG:
    """
    Baseline RAG system without tool calling capabilities.
    
    This agent can only answer questions from the knowledge base
    and cannot perform actions like applying leave or sending emails.
    """
    
    def __init__(self):
        """Initialize the conversational RAG."""
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.1,
            max_tokens=2048,
        )
        self.retriever = DocumentRetriever()
        self.conversation_history: List[Dict[str, str]] = []
        self.metrics = {
            "total_queries": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "avg_retrieval_docs": 0
        }
    
    def query(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Answer a query using RAG.
        
        Args:
            query: User's question
            session_id: Optional session identifier
            context: Optional context (e.g., employee_id)
            
        Returns:
            Dictionary containing answer, sources, and metadata
        """
        try:
            self.metrics["total_queries"] += 1
            
            # Retrieve relevant documents
            documents = self.retriever.retrieve(query, k=5)
            
            if not documents:
                logger.warning(f"No documents retrieved for query: {query}")
                return {
                    "answer": "I couldn't find relevant information in the knowledge base to answer your question. Please contact HR directly at hr@techcorp.com or +1-555-0123.",
                    "sources": [],
                    "session_id": session_id,
                    "confidence": 0.0
                }
            
            # Update metrics
            self.metrics["avg_retrieval_docs"] = (
                (self.metrics["avg_retrieval_docs"] * (self.metrics["total_queries"] - 1) + len(documents))
                / self.metrics["total_queries"]
            )
            
            # Format context from retrieved documents
            context_text = format_documents_for_prompt(documents)
            
            # Build system prompt
            system_prompt = """You are an HR assistant for TechCorp Inc. Your role is to help employees with HR-related questions using the company's policy documents.

IMPORTANT LIMITATIONS:
- You can ONLY provide information from the knowledge base
- You CANNOT perform actions like applying leave, sending emails, or making changes
- If someone asks you to perform an action, politely explain that they need to use the HR portal or contact HR directly
- Always be helpful, friendly, and professional

GUIDELINES:
1. Answer questions accurately using ONLY the provided context
2. If the context doesn't contain the answer, say so clearly
3. For action requests, guide users to the appropriate channel (HR portal, email, or phone)
4. Be concise but complete in your answers
5. If information is unclear or missing, acknowledge it

Remember: You are an information assistant, not an action executor."""
            
            # Build user prompt with context
            user_prompt = f"""Based on the following company policy documents, please answer the user's question.

CONTEXT:
{context_text}

QUESTION: {query}

Please provide a helpful answer based on the context above. If the context doesn't contain enough information to answer the question, clearly state that and suggest contacting HR directly."""
            
            # Generate response
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Handle different response formats (Gemini returns list, Claude returns string)
            if isinstance(response.content, list):
                # Gemini format: [{'type': 'text', 'text': '...'}]
                answer = response.content[0]['text'] if response.content else ""
            else:
                # Claude format: plain string
                answer = response.content
            
            # Store in conversation history
            self.conversation_history.append({
                "role": "user",
                "content": query
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": answer
            })
            
            # Extract sources
            sources = [
                {
                    "filename": doc.metadata.get("filename", "Unknown"),
                    "document_type": doc.metadata.get("document_type", "general"),
                    "score": doc.metadata.get("score", 0.0),
                    "excerpt": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                }
                for doc in documents
            ]
            
            self.metrics["successful_responses"] += 1
            
            logger.info(f"Conversational RAG answered query: {query[:50]}...")
            
            return {
                "answer": answer,
                "sources": sources,
                "session_id": session_id,
                "confidence": self._calculate_confidence(documents),
                "retrieved_docs_count": len(documents)
            }
        
        except Exception as e:
            logger.error(f"Error in conversational RAG: {e}")
            self.metrics["failed_responses"] += 1
            
            return {
                "answer": f"I encountered an error while processing your question. Please try again or contact HR at hr@techcorp.com",
                "sources": [],
                "session_id": session_id,
                "error": str(e)
            }
    
    def _calculate_confidence(self, documents: List) -> float:
        """
        Calculate confidence score based on retrieval results.
        
        Args:
            documents: Retrieved documents
            
        Returns:
            Confidence score between 0 and 1
        """
        if not documents:
            return 0.0
        
        # Average of top document scores
        scores = [doc.metadata.get("score", 0) for doc in documents]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Normalize to 0-1 range (assuming similarity scores are already 0-1)
        return min(1.0, max(0.0, avg_score))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful_responses"] / self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0 else 0
            )
        }
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")


# Create global instance
conversational_rag = ConversationalRAG()
