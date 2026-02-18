"""
Vector database initialization and management for ChromaDB.

Handles document ingestion, embedding generation, and similarity search.
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None
    SentenceTransformer = None

from ..utils.logger import get_logger

logger = get_logger(__name__)


class VectorDBManager:
    """Manages ChromaDB vector database for product documentation"""
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize vector database manager.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
            embedding_model: Name of the sentence-transformers model
        """
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available. Install with: pip install chromadb sentence-transformers")
            self.client = None
            self.collection = None
            self.embedding_model = None
            return
        
        # Configuration from environment or defaults
        self.persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIRECTORY", 
            "./data/embeddings"
        )
        self.collection_name = collection_name or os.getenv(
            "CHROMA_COLLECTION_NAME", 
            "product_documents"
        )
        embedding_model_name = embedding_model or os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Create persist directory if it doesn't exist
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding model
            logger.info(f"Loading embedding model: {embedding_model_name}")
            self.embedding_model = SentenceTransformer(embedding_model_name)
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Product documentation and specifications"}
            )
            
            logger.info(f"Vector DB initialized: {self.collection_name} ({self.collection.count()} documents)")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None
            self.embedding_model = None
    
    def is_available(self) -> bool:
        """Check if vector database is available"""
        return self.client is not None and self.collection is not None
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        Add documents to the vector database.
        
        Args:
            documents: List of document texts
            metadatas: List of metadata dicts for each document
            ids: Optional list of document IDs (generated if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("Vector DB not available")
            return False
        
        try:
            # Generate IDs if not provided
            if ids is None:
                ids = [
                    hashlib.md5(doc.encode()).hexdigest()
                    for doc in documents
                ]
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(documents).tolist()
            
            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to vector DB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False
    
    def query(
        self,
        query_text: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the vector database for similar documents.
        
        Args:
            query_text: Query text
            n_results: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            Query results with documents, distances, and metadata
        """
        if not self.is_available():
            logger.warning("Vector DB not available, returning empty results")
            return {
                "documents": [[]],
                "distances": [[]],
                "metadatas": [[]],
                "ids": [[]]
            }
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query_text])[0].tolist()
            
            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata
            )
            
            logger.debug(f"Query returned {len(results['documents'][0])} results")
            return results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                "documents": [[]],
                "distances": [[]],
                "metadatas": [[]],
                "ids": [[]]
            }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        if not self.is_available():
            return {
                "available": False,
                "count": 0,
                "collection_name": self.collection_name
            }
        
        return {
            "available": True,
            "count": self.collection.count(),
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory
        }
    
    def reset_collection(self) -> bool:
        """Reset (clear) the collection"""
        if not self.is_available():
            return False
        
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Product documentation and specifications"}
            )
            logger.info(f"Collection {self.collection_name} reset")
            return True
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False


# Global vector DB instance
_vector_db = None


def get_vector_db() -> VectorDBManager:
    """Get or create global vector database instance"""
    global _vector_db
    if _vector_db is None:
        _vector_db = VectorDBManager()
    return _vector_db


def initialize_vector_db(
    persist_directory: Optional[str] = None,
    collection_name: Optional[str] = None,
    embedding_model: Optional[str] = None
) -> VectorDBManager:
    """Initialize vector database with custom configuration"""
    global _vector_db
    _vector_db = VectorDBManager(
        persist_directory=persist_directory,
        collection_name=collection_name,
        embedding_model=embedding_model
    )
    return _vector_db
