"""Plain REST routes of the customer communication service (no model involved).

``POST /dispatch`` delivers the due pending notifications inside the request and
returns the counts (spec: agent-services, notification dispatch endpoint). On
Cloud Run the service only has CPU while it serves a request, so the background
loop alone does not deliver anything once the instance is idle; the gateway calls
this route whenever a turn queued a notification. ``FOR UPDATE SKIP LOCKED`` in
:func:`dispatcher.dispatch_pending` keeps it safe next to the loop.
"""

from __future__ import annotations

import asyncio
import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import dispatcher

logger = logging.getLogger("customer_communication_agent.rest")


async def dispatch(_request: Request) -> JSONResponse:
    try:
        counts = await asyncio.to_thread(dispatcher.dispatch_pending)
    except Exception as exc:  # database unavailable etc.; rows stay pending
        logger.warning("On-demand dispatch failed: %s", type(exc).__name__)
        return JSONResponse({"success": False, "error": "dispatch failed"}, status_code=503)
    return JSONResponse({"success": True, **counts})


ROUTES = [Route("/dispatch", dispatch, methods=["POST"])]
