try:
    from .agent import root_agent
    __all__ = ["root_agent"]
except (ModuleNotFoundError, ImportError):
    # Handle missing dependencies (vertexai, google-adk) for testing
    __all__ = []


def get_agent():
    """Return the root agent for ADK to load"""
    return root_agent
