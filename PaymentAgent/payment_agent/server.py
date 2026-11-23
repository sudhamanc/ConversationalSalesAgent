"""A2A server for payment_agent: `uvicorn payment_agent.server:app --host 0.0.0.0 --port $PORT`.

Besides the A2A endpoint it serves ``POST /payment-methods`` (``rest.py``), the
model-free endpoint behind the chat's secure payment form.
"""

from sales_common.a2a_server import create_a2a_app

from .agent import root_agent
from .rest import ROUTES

app = create_a2a_app(root_agent, extra_routes=ROUTES)
