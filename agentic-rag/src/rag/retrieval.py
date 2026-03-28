"""Retrieval logic for the RAG system."""

from typing import List, Dict, Any, Optional
from loguru import logger

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document

from src.config import settings


class DocumentRetriever:
    """Handles document retrieval from vector store."""
    
    def __init__(self):
        """Initialize the retriever."""
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        
        # Initialize Qdrant client - don't pass api_key if it's empty
        qdrant_kwargs = {
            "host": settings.qdrant_host,
            "port": settings.qdrant_port,
        }
        if settings.qdrant_api_key:
            qdrant_kwargs["api_key"] = settings.qdrant_api_key
        
        self.qdrant_client = QdrantClient(**qdrant_kwargs)
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a query."""
        embedding = self.embedding_model.encode(query, convert_to_numpy=True)
        return embedding.tolist()
    
    def retrieve(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[Document]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: The search query
            k: Number of documents to retrieve
            filters: Optional metadata filters
            score_threshold: Minimum similarity score
            
        Returns:
            List of retrieved documents
        """
        # Generate query embedding
        query_embedding = self.generate_query_embedding(query)
        
        # Build filters if provided
        qdrant_filter = None
        if filters:
            qdrant_filter = self._build_filter(filters)
        
        # Search in Qdrant
        try:
            search_results = self.qdrant_client.search(
                collection_name=settings.qdrant_collection_name,
                query_vector=query_embedding,
                limit=k,
                query_filter=qdrant_filter,
                score_threshold=score_threshold
            )
            
            # Convert to Document objects
            documents = []
            for result in search_results:
                doc = Document(
                    page_content=result.payload["text"],
                    metadata={
                        **result.payload.get("metadata", {}),
                        "score": result.score
                    }
                )
                documents.append(doc)
            
            logger.info(f"Retrieved {len(documents)} documents for query: {query[:50]}...")
            return documents
            
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []
    
    def _build_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build Qdrant filter from dictionary."""
        conditions = []
        
        for key, value in filters.items():
            condition = FieldCondition(
                key=f"metadata.{key}",
                match=MatchValue(value=value)
            )
            conditions.append(condition)
        
        return Filter(must=conditions) if conditions else None
    
    def retrieve_by_document_type(
        self,
        query: str,
        document_type: str,
        k: int = 5
    ) -> List[Document]:
        """Retrieve documents filtered by document type."""
        return self.retrieve(
            query=query,
            k=k,
            filters={"document_type": document_type}
        )
    
    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        semantic_weight: float = 0.7
    ) -> List[Document]:
        """
        Perform hybrid search combining semantic and keyword matching.
        
        Note: This is a simplified version. For production, consider using
        proper hybrid search with BM25 + vector search.
        """
        # For now, we'll just use semantic search
        # In a full implementation, you would combine BM25 and vector search
        return self.retrieve(query=query, k=k)
    
    def rewrite_query(self, original_query: str) -> List[str]:
        """
        Generate alternative query formulations.
        
        Note: This requires an LLM call. For now, returning original query.
        In production, use Claude to generate alternative queries.
        """
        # Placeholder - in production, use Claude to generate alternatives
        return [original_query]
    
    def multi_query_retrieve(
        self,
        query: str,
        k: int = 5,
        num_queries: int = 3
    ) -> List[Document]:
        """
        Retrieve using multiple query formulations and combine results.
        
        Note: Simplified implementation.
        """
        queries = self.rewrite_query(query)
        
        all_docs = []
        seen_content = set()
        
        for q in queries[:num_queries]:
            docs = self.retrieve(q, k=k)
            for doc in docs:
                if doc.page_content not in seen_content:
                    all_docs.append(doc)
                    seen_content.add(doc.page_content)
        
        # Sort by score and return top k
        all_docs.sort(key=lambda x: x.metadata.get("score", 0), reverse=True)
        return all_docs[:k]


class ContextualRetriever(DocumentRetriever):
    """Enhanced retriever with contextual capabilities."""
    
    def retrieve_with_context(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        k: int = 5
    ) -> List[Document]:
        """
        Retrieve documents considering conversation history.
        
        Args:
            query: Current query
            conversation_history: Previous conversation turns
            k: Number of documents to retrieve
            
        Returns:
            List of relevant documents
        """
        # Combine query with recent context
        if conversation_history:
            # Get last 2 exchanges for context
            recent_context = conversation_history[-4:]  # 2 user + 2 assistant
            context_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in recent_context
            ])
            enhanced_query = f"Context:\n{context_text}\n\nCurrent query: {query}"
        else:
            enhanced_query = query
        
        return self.retrieve(enhanced_query, k=k)
    
    def get_policy_documents(self, k: int = 10) -> List[Document]:
        """Get all policy documents for reference."""
        # Retrieve policy documents
        return self.retrieve(
            query="company policies leave work hours code of conduct",
            k=k,
            filters={"document_type": "leave_policy"}
        )


def format_documents_for_prompt(documents: List[Document]) -> str:
    """Format retrieved documents for inclusion in LLM prompt."""
    if not documents:
        return "No relevant documents found."
    
    formatted = []
    for i, doc in enumerate(documents, 1):
        source = doc.metadata.get("filename", "Unknown")
        score = doc.metadata.get("score", 0)
        formatted.append(
            f"[Document {i}] (Source: {source}, Relevance: {score:.2f})\n{doc.page_content}\n"
        )
    
    return "\n---\n".join(formatted)
