"""Multi-tenant document ingestion pipeline."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
import tempfile
import shutil

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid

from src.config import settings
from src.config.company_manager import company_manager


class MultiTenantIngestion:
    """Handles document ingestion for multiple companies."""
    
    def __init__(self):
        """Initialize the multi-tenant ingestion pipeline."""
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        
        # Initialize Qdrant client - don't pass api_key if it's empty
        qdrant_kwargs = {
            "host": settings.qdrant_host,
            "port": settings.qdrant_port,
        }
        if settings.qdrant_api_key:
            qdrant_kwargs["api_key"] = settings.qdrant_api_key
        
        self.qdrant_client = QdrantClient(**qdrant_kwargs)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _ensure_collection(self, collection_name: str):
        """Ensure collection exists for a company."""
        collections = self.qdrant_client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if collection_name not in collection_names:
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {collection_name}")
    
    def ingest_from_upload(
        self,
        company_id: str,
        file_path: Path,
        file_name: str,
        doc_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest a single uploaded document for a company.
        
        Args:
            company_id: Company identifier
            file_path: Path to uploaded file
            file_name: Original filename
            doc_type: Document type (leave_policy, faq, etc.)
            
        Returns:
            Dictionary with ingestion results
        """
        try:
            # Get or create company
            company = company_manager.get_company(company_id)
            if not company:
                company = company_manager.create_company(
                    company_name=company_id,
                    company_id=company_id
                )
            
            # Ensure collection exists
            self._ensure_collection(company.collection_name)
            
            # Load document based on file type
            file_extension = file_path.suffix.lower()
            
            if file_extension == '.pdf':
                loader = PyPDFLoader(str(file_path))
            elif file_extension in ['.docx', '.doc']:
                loader = Docx2txtLoader(str(file_path))
            elif file_extension in ['.txt', '.md']:
                loader = TextLoader(str(file_path))
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported file type: {file_extension}"
                }
            
            # Load document
            documents = loader.load()
            
            # Add metadata
            for doc in documents:
                doc.metadata.update({
                    "company_id": company_id,
                    "filename": file_name,
                    "document_type": doc_type or "general",
                    "uploaded_at": str(Path(file_path).stat().st_mtime)
                })
            
            # Chunk documents
            chunks = self.text_splitter.split_documents(documents)
            
            # Generate embeddings
            texts = [chunk.page_content for chunk in chunks]
            embeddings = self.embedding_model.encode(
                texts,
                show_progress_bar=True,
                convert_to_numpy=True
            ).tolist()
            
            # Store in Qdrant
            points = []
            for chunk, embedding in zip(chunks, embeddings):
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "text": chunk.page_content,
                        "metadata": chunk.metadata
                    }
                )
                points.append(point)
            
            self.qdrant_client.upsert(
                collection_name=company.collection_name,
                points=points
            )
            
            logger.info(
                f"Ingested {len(chunks)} chunks from {file_name} "
                f"for company {company_id}"
            )
            
            return {
                "status": "success",
                "company_id": company_id,
                "collection_name": company.collection_name,
                "filename": file_name,
                "chunks_created": len(chunks),
                "chunks_stored": len(points)
            }
        
        except Exception as e:
            logger.error(f"Error ingesting document: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def ingest_multiple_files(
        self,
        company_id: str,
        files: List[tuple]  # List of (file_path, file_name, doc_type)
    ) -> Dict[str, Any]:
        """
        Ingest multiple files for a company.
        
        Args:
            company_id: Company identifier
            files: List of tuples (file_path, file_name, doc_type)
            
        Returns:
            Dictionary with ingestion results
        """
        results = []
        total_chunks = 0
        
        for file_path, file_name, doc_type in files:
            result = self.ingest_from_upload(
                company_id=company_id,
                file_path=file_path,
                file_name=file_name,
                doc_type=doc_type
            )
            results.append(result)
            if result["status"] == "success":
                total_chunks += result["chunks_stored"]
        
        return {
            "status": "success",
            "company_id": company_id,
            "files_processed": len(files),
            "total_chunks": total_chunks,
            "results": results
        }
    
    def clear_company_collection(self, company_id: str) -> bool:
        """Clear all documents for a company."""
        try:
            company = company_manager.get_company(company_id)
            if company:
                self.qdrant_client.delete_collection(company.collection_name)
                self._ensure_collection(company.collection_name)
                logger.info(f"Cleared collection for company: {company_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False
    
    def get_company_stats(self, company_id: str) -> Dict[str, Any]:
        """Get statistics for a company's knowledge base."""
        try:
            company = company_manager.get_company(company_id)
            if not company:
                return {"status": "error", "message": "Company not found"}
            
            collection_info = self.qdrant_client.get_collection(
                company.collection_name
            )
            
            return {
                "status": "success",
                "company_id": company_id,
                "company_name": company.company_name,
                "collection_name": company.collection_name,
                "total_vectors": collection_info.vectors_count,
                "created_at": company.created_at
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"status": "error", "message": str(e)}


# Global instance
multi_tenant_ingestion = MultiTenantIngestion()
