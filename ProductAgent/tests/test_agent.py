"""
Integration tests for the Product Agent.
"""

import pytest
from product_agent import get_agent


class TestAgentIntegration:
    """Integration tests for the complete agent"""
    
    def test_agent_initialization(self):
        """Test that agent initializes correctly"""
        agent = get_agent()
        
        assert agent is not None
        assert agent.name == "product_agent" or agent.name.startswith("product")
        assert len(agent.tools) >= 11  # Should have at least 11 tools
    
    def test_agent_has_required_tools(self):
        """Test that agent has all required tools"""
        agent = get_agent()
        
        tool_names = [tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in agent.tools]
        
        # Should have RAG tools
        assert any('query' in str(name).lower() or 'documentation' in str(name).lower() for name in tool_names)
        
        # Should have product catalog tools
        assert any('list' in str(name).lower() or 'product' in str(name).lower() for name in tool_names)
        
        # Should have comparison tools
        assert any('compare' in str(name).lower() for name in tool_names)
    
    def test_agent_configuration(self):
        """Test agent configuration settings"""
        agent = get_agent()
        
        # Agent should have low temperature for factual responses
        config = agent.generate_content_config
        assert config.temperature == 0.1
        assert config.top_p == 0.2
        assert config.top_k == 20
    
    def test_agent_description(self):
        """Test agent has proper description"""
        agent = get_agent()
        
        assert agent.description is not None
        assert "Info/RAG" in agent.description or "RAG" in agent.description
        assert "product" in agent.description.lower()


class TestVectorDBIntegration:
    """Test vector database integration"""
    
    def test_vector_db_initialization(self):
        """Test vector DB can be initialized"""
        from product_agent.utils.vector_db import get_vector_db
        
        vector_db = get_vector_db()
        assert vector_db is not None
    
    def test_vector_db_stats(self):
        """Test getting vector DB statistics"""
        from product_agent.utils.vector_db import get_vector_db
        
        vector_db = get_vector_db()
        stats = vector_db.get_collection_stats()
        
        assert "available" in stats
        assert "count" in stats
        assert "collection_name" in stats


class TestCacheIntegration:
    """Test cache integration"""
    
    def test_cache_stats(self):
        """Test cache statistics"""
        from product_agent.utils.cache import get_cache_stats, clear_cache
        
        # Clear cache first
        clear_cache()
        
        stats = get_cache_stats()
        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
    
    def test_cache_cleanup(self):
        """Test cache cleanup"""
        from product_agent.utils.cache import cleanup_cache, clear_cache
        
        # Should not raise any errors
        clear_cache()
        cleanup_cache()


class TestLogging:
    """Test logging functionality"""
    
    def test_logger_creation(self):
        """Test logger can be created"""
        from product_agent.utils.logger import get_logger
        
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
