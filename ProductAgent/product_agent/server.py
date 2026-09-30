"""A2A service entry point: ``uvicorn product_agent.server:app --host 0.0.0.0 --port $PORT``."""

from sales_common.a2a_server import create_a2a_app

from .agent import root_agent

# Catalog data comes from the catalog service; this agent's tools do not touch the DB
# (DATABASE_URL is still required for ADK sessions and A2A tasks).
app = create_a2a_app(root_agent, uses_database=False)
