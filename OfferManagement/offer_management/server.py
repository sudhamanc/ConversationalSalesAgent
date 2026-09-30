"""A2A server for offer_management_agent: `uvicorn offer_management.server:app --host 0.0.0.0 --port $PORT`."""

from sales_common.a2a_server import create_a2a_app

from .agent import root_agent

app = create_a2a_app(root_agent)
