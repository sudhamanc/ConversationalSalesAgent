"""
Tests for RAG functionality (when ChromaDB is available).
"""

import pytest
from product_agent.utils.vector_db import get_vector_db
from product_agent.tools.rag_tools import (
    query_product_documentation,
    search_technical_specs,
    get_product_features,
    get_sla_terms,
)


class TestRAGTools:
    """Tests for RAG tools (requires ChromaDB)"""
    
    def test_query_product_documentation(self):
        """Test querying product documentation"""
        result = query_product_documentation(
            question="What is the speed of Fiber 5G?",
            product_id="FIB-5G"
        )
        
        assert 'answer' in result
        assert 'sources' in result
        assert 'confidence' in result
        assert 'metadata' in result
    
    def test_query_product_documentation_no_product_id(self):
        """Test RAG query without specific product ID"""
        result = query_product_documentation(
            question="What SLA uptime is guaranteed?"
        )
        
        assert 'answer' in result
        assert 'sources' in result
        assert 'confidence' in result
    
    def test_search_technical_specs(self):
        """Test searching for technical specifications"""
        result = search_technical_specs("Fiber 5G")
        
        assert 'found' in result
        # If vector DB not available, it may return False
        if result['found']:
            assert 'product_name' in result
            assert 'specifications' in result
    
    def test_get_product_features(self):
        """Test getting product features"""
        result = get_product_features("FIB-5G")
        
        assert 'found' in result
        assert 'product_id' in result
    
    def test_get_sla_terms(self):
        """Test getting SLA terms"""
        result = get_sla_terms("FIB-5G")
        
        assert 'found' in result
        assert 'product_id' in result


class TestVectorDBManager:
    """Tests for VectorDBManager"""
    
    def test_vector_db_available(self):
        """Test checking if vector DB is available"""
        vector_db = get_vector_db()
        
        # Should return True or False without errors
        is_available = vector_db.is_available()
        assert isinstance(is_available, bool)
    
    def test_get_collection_stats(self):
        """Test getting collection statistics"""
        vector_db = get_vector_db()
        stats = vector_db.get_collection_stats()
        
        assert 'available' in stats
        assert 'count' in stats
        assert 'collection_name' in stats
        
        if stats['available']:
            assert stats['collection_name'] == "product_documents"
    
    @pytest.mark.skipif(
        not get_vector_db().is_available(),
        reason="ChromaDB not available"
    )
    def test_add_documents(self):
        """Test adding documents to vector DB"""
        vector_db = get_vector_db()
        
        # Add test documents
        documents = [
            "Test product specification for testing purposes",
            "Another test document with product information"
        ]
        metadatas = [
            {"product_id": "TEST-1", "source": "test_spec.pdf"},
            {"product_id": "TEST-2", "source": "test_spec2.pdf"}
        ]
        
        success = vector_db.add_documents(documents, metadatas)
        assert success is True
    
    @pytest.mark.skipif(
        not get_vector_db().is_available(),
        reason="ChromaDB not available"
    )
    def test_query_documents(self):
        """Test querying documents from vector DB"""
        vector_db = get_vector_db()
        
        # Query for any product information
        results = vector_db.query("product specifications", n_results=5)
        
        assert 'documents' in results
        assert 'distances' in results
        assert 'metadatas' in results
        assert 'ids' in results


class TestRAGCaching:
    """Test RAG query caching"""
    
    def test_rag_query_caching(self):
        """Test that RAG queries are cached"""
        from product_agent.utils.cache import get_cache_stats, clear_cache
        
        # Clear cache
        clear_cache()
        
        # First query - should miss cache
        query_product_documentation("What is Fiber 5G?", "FIB-5G")
        stats1 = get_cache_stats()
        
        # Second identical query - should hit cache
        query_product_documentation("What is Fiber 5G?", "FIB-5G")
        stats2 = get_cache_stats()
        
        # Cache hits should increase
        assert stats2['hits'] > stats1['hits']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
