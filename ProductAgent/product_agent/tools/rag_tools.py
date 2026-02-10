"""
RAG (Retrieval-Augmented Generation) tools for product documentation.

These tools query the ChromaDB vector database to retrieve relevant
product information from technical documentation.
"""

from typing import Dict, Any, Optional, List
from ..utils.logger import get_logger
from ..utils.cache import cache_result, get_cached_result
from ..utils.vector_db import get_vector_db

logger = get_logger(__name__)


def query_product_documentation(
    question: str,
    product_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query product documentation using RAG to answer questions.
    
    This tool uses semantic search over product manuals, spec sheets,
    and documentation to provide accurate answers to product questions.
    
    Args:
        question: User's question about products
        product_id: Optional product ID to filter results
        
    Returns:
        dict with 'answer', 'sources', 'confidence', and 'metadata'
        
    Examples:
        >>> query_product_documentation("What is the upload speed of Fiber 5G?", "FIB-5G")
        {'answer': 'Fiber 5G provides 5 Gbps symmetrical speeds...', 'sources': [...], ...}
        
        >>> query_product_documentation("What SLA uptime is guaranteed?")
        {'answer': 'Business fiber products include 99.9% uptime SLA...', ...}
    """
    logger.info(f"Querying documentation: {question} (product_id={product_id})")
    
    # Check cache first
    cache_key = f"rag:{product_id or 'all'}:{question[:50]}"
    cached = get_cached_result(cache_key)
    if cached:
        logger.debug("Returning cached RAG result")
        return cached
    
    vector_db = get_vector_db()
    
    if not vector_db.is_available():
        logger.warning("Vector DB not available, returning fallback")
        return {
            "answer": "I apologize, but I'm unable to access the product documentation at this moment. Please try again shortly or contact our sales team for detailed product information.",
            "sources": [],
            "confidence": 0.0,
            "metadata": {"error": "vector_db_unavailable"}
        }
    
    try:
        # Build metadata filter if product_id provided
        filter_metadata = {"product_id": product_id} if product_id else None
        
        # Query vector database
        results = vector_db.query(
            query_text=question,
            n_results=3,  # Top 3 most relevant documents
            filter_metadata=filter_metadata
        )
        
        # Extract results
        documents = results['documents'][0]
        distances = results['distances'][0]
        metadatas = results['metadatas'][0]
        
        if not documents:
            response = {
                "answer": f"I don't have specific documentation about {'that product' if product_id else 'that topic'}. Could you rephrase your question or ask about a different product?",
                "sources": [],
                "confidence": 0.0,
                "metadata": {"no_results": True}
            }
        else:
            # Calculate confidence (inverse of distance, normalized)
            confidence = 1.0 - (distances[0] if distances else 1.0)
            confidence = max(0.0, min(1.0, confidence))
            
            # Extract sources
            sources = [
                meta.get('source', 'Unknown') 
                for meta in metadatas
            ]
            
            # Combine top documents into context
            context = "\n\n".join(documents)
            
            # Create answer (in production, this would use LLM to synthesize)
            # For now, return the most relevant document content
            response = {
                "answer": documents[0] if documents else "No information found.",
                "sources": sources,
                "confidence": confidence,
                "metadata": {
                    "product_id": product_id,
                    "num_sources": len(documents)
                }
            }
        
        # Cache result
        cache_result(cache_key, response)
        
        logger.info(f"RAG query completed (confidence={response['confidence']:.2f})")
        return response
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        return {
            "answer": "An error occurred while searching the documentation. Please try again.",
            "sources": [],
            "confidence": 0.0,
            "metadata": {"error": str(e)}
        }


def search_technical_specs(product_name: str) -> Dict[str, Any]:
    """
    Search for technical specifications of a specific product.
    
    Args:
        product_name: Name of the product (e.g., "Fiber 5G", "Business Fiber 1 Gbps")
        
    Returns:
        dict with technical specifications
        
    Example:
        >>> search_technical_specs("Fiber 5G")
        {'product_id': 'FIB-5G', 'specs': {...}, 'found': True}
    """
    logger.info(f"Searching technical specs for: {product_name}")
    
    # Try cache first
    cache_key = f"specs:{product_name.lower()}"
    cached = get_cached_result(cache_key)
    if cached:
        return cached
    
    vector_db = get_vector_db()
    
    if not vector_db.is_available():
        return {
            "found": False,
            "error": "Vector database not available"
        }
    
    try:
        # Query for technical specifications
        query_text = f"technical specifications {product_name} speed bandwidth features"
        results = vector_db.query(query_text, n_results=2)
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        
        if not documents:
            response = {
                "found": False,
                "message": f"No technical specifications found for {product_name}"
            }
        else:
            response = {
                "found": True,
                "product_name": product_name,
                "specifications": documents[0],
                "source": metadatas[0].get('source', 'Unknown') if metadatas else 'Unknown',
                "metadata": metadatas[0] if metadatas else {}
            }
        
        cache_result(cache_key, response)
        return response
        
    except Exception as e:
        logger.error(f"Technical specs search failed: {e}")
        return {
            "found": False,
            "error": str(e)
        }


def get_product_features(product_id: str) -> Dict[str, Any]:
    """
    Get complete feature list for a product.
    
    Args:
        product_id: Product identifier (e.g., "FIB-5G")
        
    Returns:
        dict with features list and details
        
    Example:
        >>> get_product_features("FIB-5G")
        {'product_id': 'FIB-5G', 'features': [...], 'found': True}
    """
    logger.info(f"Getting features for product: {product_id}")
    
    cache_key = f"features:{product_id}"
    cached = get_cached_result(cache_key)
    if cached:
        return cached
    
    vector_db = get_vector_db()
    
    if not vector_db.is_available():
        return {
            "found": False,
            "error": "Vector database not available"
        }
    
    try:
        # Query for features
        query_text = f"features included {product_id} what is included benefits"
        results = vector_db.query(
            query_text,
            n_results=3,
            filter_metadata={"product_id": product_id}
        )
        
        documents = results['documents'][0]
        
        if not documents:
            response = {
                "found": False,
                "product_id": product_id,
                "message": f"No feature information found for {product_id}"
            }
        else:
            response = {
                "found": True,
                "product_id": product_id,
                "features": documents,
                "sources": [meta.get('source', 'Unknown') for meta in results['metadatas'][0]]
            }
        
        cache_result(cache_key, response)
        return response
        
    except Exception as e:
        logger.error(f"Feature retrieval failed: {e}")
        return {
            "found": False,
            "error": str(e)
        }


def get_sla_terms(product_id: str) -> Dict[str, Any]:
    """
    Get Service Level Agreement details for a product.
    
    Args:
        product_id: Product identifier
        
    Returns:
        dict with SLA terms including uptime, support, response time
        
    Example:
        >>> get_sla_terms("FIB-5G")
        {'uptime': '99.9%', 'support_level': 'Premium', ...}
    """
    logger.info(f"Getting SLA terms for: {product_id}")
    
    cache_key = f"sla:{product_id}"
    cached = get_cached_result(cache_key)
    if cached:
        return cached
    
    vector_db = get_vector_db()
    
    if not vector_db.is_available():
        return {
            "found": False,
            "error": "Vector database not available"
        }
    
    try:
        # Query for SLA information
        query_text = f"SLA service level agreement {product_id} uptime guarantee support response time"
        results = vector_db.query(
            query_text,
            n_results=2,
            filter_metadata={"product_id": product_id}
        )
        
        documents = results['documents'][0]
        
        if not documents:
            response = {
                "found": False,
                "product_id": product_id,
                "message": f"No SLA information found for {product_id}"
            }
        else:
            response = {
                "found": True,
                "product_id": product_id,
                "sla_details": documents[0],
                "source": results['metadatas'][0][0].get('source', 'Unknown') if results['metadatas'][0] else 'Unknown'
            }
        
        cache_result(cache_key, response)
        return response
        
    except Exception as e:
        logger.error(f"SLA retrieval failed: {e}")
        return {
            "found": False,
            "error": str(e)
        }
