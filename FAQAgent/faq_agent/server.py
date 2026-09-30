"""A2A server for faq_agent: `uvicorn faq_agent.server:app --host 0.0.0.0 --port $PORT`."""

from sales_common.a2a_server import create_a2a_app

from .agent import root_agent

app = create_a2a_app(root_agent)
