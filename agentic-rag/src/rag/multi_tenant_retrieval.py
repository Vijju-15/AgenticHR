"""Multi-tenant retrieval logic."""

from typing import List, Dict, Any, Optional
from loguru import logger

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document

from src.config import settings
from src.config.company_manager import company_manager


class MultiTenantRetriever:
    """Handles document retrieval for multiple companies."""
    
    def __init__(self):
        """Initialize the multi-tenant retriever."""
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        
        # Initialize Qdrant client - don't pass api_key if it's empty
        qdrant_kwargs = {
            "host": settings.qdrant_host,
            "port": settings.qdrant_port,
        }
        if settings.qdrant_api_key:
            qdrant_kwargs["api_key"] = settings.qdrant_api_key
        
        self.qdrant_client = QdrantClient(**qdrant_kwargs)
    
    def retrieve(
        self,
        query: str,
        company_id: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[Document]:
        """
        Retrieve relevant documents for a company.
        
        Args:
            query: The search query
            company_id: Company identifier
            k: Number of documents to retrieve
            filters: Optional metadata filters
            score_threshold: Minimum similarity score
            
        Returns:
            List of retrieved documents
        """
        try:
            # Get company
            company = company_manager.get_company(company_id)
            if not company:
                logger.warning(f"Company not found: {company_id}")
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                query, 
                convert_to_numpy=True
            ).tolist()
            
            # Build filters
            qdrant_filter = None
            if filters:
                qdrant_filter = self._build_filter(filters)
            
            # Search in company's collection
            # qdrant-client >= 1.7 removed .search(); use .query_points() instead
            search_response = self.qdrant_client.query_points(
                collection_name=company.collection_name,
                query=query_embedding,
                limit=k,
                query_filter=qdrant_filter,
                score_threshold=score_threshold if score_threshold > 0.0 else None,
            )
            search_results = search_response.points

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
            
            logger.info(
                f"Retrieved {len(documents)} documents for company {company_id}"
            )
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
