"""
Integration tests for the Serviceability Agent.
"""

import pytest
from serviceability_agent import get_agent


class TestAgentIntegration:
    """Integration tests for the complete agent"""
    
    def test_agent_initialization(self):
        """Test that agent initializes correctly"""
        agent = get_agent()
        
        assert agent is not None
        assert agent.name == "serviceability_agent" or agent.name.startswith("serviceability")
        assert len(agent.tools) >= 4  # Should have at least 4 tools
    
    def test_agent_has_required_tools(self):
        """Test that agent has all required tools"""
        agent = get_agent()
        
        tool_names = [tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in agent.tools]
        
        # Should have address validation tools
        assert any('validate' in str(name).lower() for name in tool_names)
        
        # Should have serviceability check tool
        assert any('availability' in str(name).lower() or 'service' in str(name).lower() for name in tool_names)
    
    def test_agent_configuration(self):
        """Test agent configuration settings"""
        agent = get_agent()
        
        # Agent should be deterministic (temperature = 0)
        config = agent.generate_content_config
        assert config.temperature == 0.0
        assert config.top_p == 0.1
        assert config.top_k == 10
    
    def test_agent_description(self):
        """Test agent has proper description"""
        agent = get_agent()
        
        assert agent.description is not None
        assert "PRE-SALE" in agent.description
        assert "address" in agent.description.lower()


class TestCacheIntegration:
    """Test cache integration"""
    
    def test_cache_stats(self):
        """Test cache statistics"""
        from serviceability_agent.utils.cache import get_cache_stats, clear_cache
        
        # Clear cache first
        clear_cache()
        
        stats = get_cache_stats()
        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
    
    def test_cache_cleanup(self):
        """Test cache cleanup"""
        from serviceability_agent.utils.cache import cleanup_cache, clear_cache
        
        # Should not raise any errors
        clear_cache()
        cleanup_cache()


class TestLogging:
    """Test logging functionality"""
    
    def test_logger_creation(self):
        """Test logger can be created"""
        from serviceability_agent.utils.logger import get_logger
        
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
