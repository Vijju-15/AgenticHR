"""Document ingestion pipeline for the RAG system."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    DirectoryLoader
)
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid

from src.config import settings


class DocumentIngestion:
    """Handles document loading, processing, and storage."""
    
    def __init__(self):
        """Initialize the document ingestion pipeline."""
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.qdrant_client = self._initialize_qdrant()
        self.text_splitter = self._get_text_splitter()
        
    def _initialize_qdrant(self) -> QdrantClient:
        """Initialize Qdrant vector store."""
        try:
            # Initialize Qdrant client - don't pass api_key if it's empty
            qdrant_kwargs = {
                "host": settings.qdrant_host,
                "port": settings.qdrant_port,
            }
            if settings.qdrant_api_key:
                qdrant_kwargs["api_key"] = settings.qdrant_api_key
            
            client = QdrantClient(**qdrant_kwargs)
            
            # Create collection if it doesn't exist
            collections = client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if settings.qdrant_collection_name not in collection_names:
                client.create_collection(
                    collection_name=settings.qdrant_collection_name,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {settings.qdrant_collection_name}")
            
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise
    
    def _get_text_splitter(self, doc_type: str = "default") -> RecursiveCharacterTextSplitter:
        """Get appropriate text splitter based on document type."""
        splitter_configs = {
            "policy_documents": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            "faqs": {
                "chunk_size": 500,
                "chunk_overlap": 50,
            },
            "procedures": {
                "chunk_size": 800,
                "chunk_overlap": 150,
            },
            "default": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
            }
        }
        
        config = splitter_configs.get(doc_type, splitter_configs["default"])
        
        return RecursiveCharacterTextSplitter(
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def load_documents(self, directory_path: Optional[Path] = None) -> List[Document]:
        """Load documents from a directory."""
        if directory_path is None:
            directory_path = settings.knowledge_base_path
        
        if not directory_path.exists():
            logger.warning(f"Directory not found: {directory_path}")
            return []
        
        documents = []
        
        # Load different file types
        loaders = {
            "*.pdf": PyPDFLoader,
            "*.docx": Docx2txtLoader,
            "*.txt": TextLoader,
            "*.md": TextLoader,  # Added support for Markdown files
        }
        
        for pattern, loader_class in loaders.items():
            try:
                loader = DirectoryLoader(
                    str(directory_path),
                    glob=pattern,
                    loader_cls=loader_class,
                    show_progress=True
                )
                docs = loader.load()
                documents.extend(docs)
                logger.info(f"Loaded {len(docs)} documents matching {pattern}")
            except Exception as e:
                logger.error(f"Error loading {pattern} files: {e}")
        
        return documents
    
    def enrich_metadata(self, document: Document) -> Document:
        """Add metadata to documents for better filtering and retrieval."""
        # Extract document type from content or filename
        source = document.metadata.get("source", "")
        filename = Path(source).name.lower()
        
        # Classify document type
        if "leave" in filename or "leave policy" in document.page_content.lower()[:500]:
            doc_type = "leave_policy"
        elif "faq" in filename:
            doc_type = "faq"
        elif "holiday" in filename or "calendar" in filename:
            doc_type = "holiday_calendar"
        elif "code of conduct" in filename or "conduct" in filename:
            doc_type = "code_of_conduct"
        elif "work hours" in filename or "working hours" in filename:
            doc_type = "work_hours"
        else:
            doc_type = "general"
        
        document.metadata.update({
            "document_type": doc_type,
            "filename": filename,
            "char_count": len(document.page_content)
        })
        
        return document
    
    def chunk_documents(
        self, 
        documents: List[Document], 
        doc_type: str = "default"
    ) -> List[Document]:
        """Split documents into chunks."""
        splitter = self._get_text_splitter(doc_type)
        chunks = splitter.split_documents(documents)
        
        # Add chunk-specific metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
        
        logger.info(f"Split {len(documents)} documents into {len(chunks)} chunks")
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def store_documents(self, documents: List[Document]) -> int:
        """Store documents in Qdrant vector store."""
        if not documents:
            logger.warning("No documents to store")
            return 0
        
        # Prepare points for Qdrant
        texts = [doc.page_content for doc in documents]
        embeddings = self.generate_embeddings(texts)
        
        points = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "text": doc.page_content,
                    "metadata": doc.metadata
                }
            )
            points.append(point)
        
        # Upload to Qdrant in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.qdrant_client.upsert(
                collection_name=settings.qdrant_collection_name,
                points=batch
            )
            logger.info(f"Uploaded batch {i // batch_size + 1}/{(len(points) - 1) // batch_size + 1}")
        
        logger.info(f"Successfully stored {len(documents)} documents")
        return len(documents)
    
    def ingest(self, directory_path: Optional[Path] = None) -> Dict[str, Any]:
        """Complete ingestion pipeline."""
        logger.info("Starting document ingestion pipeline")
        
        # Load documents
        documents = self.load_documents(directory_path)
        if not documents:
            return {
                "status": "error",
                "message": "No documents found",
                "documents_processed": 0
            }
        
        # Enrich metadata
        documents = [self.enrich_metadata(doc) for doc in documents]
        
        # Chunk documents
        chunks = self.chunk_documents(documents)
        
        # Store in vector database
        count = self.store_documents(chunks)
        
        logger.info(f"Ingestion complete: {count} chunks stored")
        
        return {
            "status": "success",
            "documents_loaded": len(documents),
            "chunks_created": len(chunks),
            "chunks_stored": count
        }
    
    def clear_collection(self):
        """Clear all documents from the collection."""
        try:
            self.qdrant_client.delete_collection(settings.qdrant_collection_name)
            self._initialize_qdrant()
            logger.info(f"Cleared collection: {settings.qdrant_collection_name}")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            raise


def run_ingestion():
    """Run the ingestion pipeline as a standalone script."""
    ingestion = DocumentIngestion()
    result = ingestion.ingest()
    print(f"\nIngestion Results:")
    print(f"Status: {result['status']}")
    print(f"Documents loaded: {result.get('documents_loaded', 0)}")
    print(f"Chunks created: {result.get('chunks_created', 0)}")
    print(f"Chunks stored: {result.get('chunks_stored', 0)}")


if __name__ == "__main__":
    run_ingestion()
