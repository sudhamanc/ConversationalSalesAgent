"""A2A server for customer_communication_agent.

Run: ``uvicorn customer_communication_agent.server:app --host 0.0.0.0 --port $PORT``.
The notification outbox dispatcher runs in the server lifespan (every
``NOTIFY_POLL_SECONDS``) and on demand in ``POST /dispatch`` (``rest.py``), which
the gateway calls when a turn queued a notification.
"""

from sales_common.a2a_server import create_a2a_app

from .agent import root_agent
from .dispatcher import dispatcher_lifespan
from .rest import ROUTES

app = create_a2a_app(root_agent, extra_lifespan=dispatcher_lifespan, extra_routes=ROUTES)
