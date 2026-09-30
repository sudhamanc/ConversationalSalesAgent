"""FastAPI app: REST API under ``/api/v1``, MCP at ``/mcp/`` and ``GET /healthz``.

Run with ``uvicorn serviceability_service.app:app --host 0.0.0.0 --port $PORT``.
"""

from __future__ import annotations

import contextlib
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from sales_common import db
from sales_common.logging import setup_logging

from . import __version__, core
from .mcp_server import mcp, streamable_http_app
from .models import (
    Address,
    AddressValidateRequest,
    AddressValidationResult,
    CoverageZonesResult,
    InfrastructureResult,
    NormalizedAddress,
    ServiceabilityResult,
    dump,
)

logger = logging.getLogger("serviceability.app")


def create_app() -> FastAPI:
    """Build the service app. Each call creates a fresh MCP session manager."""
    mcp_app = streamable_http_app()
    session_manager = mcp.session_manager  # the manager created for ``mcp_app``

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with session_manager.run():
            yield
        db.close_pool()

    app = FastAPI(
        title="Serviceability Service",
        description="US business address validation and network coverage (REST + MCP).",
        version=__version__,
        lifespan=lifespan,
    )

    @app.get("/healthz", tags=["ops"])
    def healthz() -> JSONResponse:
        healthy = db.ping()
        return JSONResponse(
            {"status": "ok" if healthy else "degraded", "service": "serviceability"},
            status_code=200 if healthy else 503,
        )

    @app.post("/api/v1/addresses/validate", response_model=AddressValidationResult,
              response_model_exclude_none=True, tags=["addresses"])
    def validate_address(body: AddressValidateRequest) -> dict:
        """Parse and validate a raw address (``valid: false`` with ``error`` when rejected)."""
        return dump(core.validate_and_parse_address(body.address))

    @app.post("/api/v1/addresses/normalize", response_model=NormalizedAddress, tags=["addresses"])
    def normalize(body: Address) -> dict:
        """Standard one-line address form."""
        return dump(core.normalize_address(body))

    @app.post("/api/v1/serviceability/check", response_model=ServiceabilityResult,
              response_model_exclude_none=True, tags=["serviceability"])
    def check(body: Address) -> dict:
        """Coverage decision, infrastructure details and SKU ids sold at the address."""
        return dump(core.check_service_availability(body))

    @app.get("/api/v1/infrastructure/{technology}", response_model=InfrastructureResult,
             tags=["serviceability"])
    def infrastructure(technology: str, zone: str = "all") -> dict:
        """Capabilities for FTTP/Fiber, HFC/Coax or DOCSIS 3.1/DOCSIS (empty list when unknown)."""
        return dump(core.get_infrastructure_by_technology(technology, zone))

    @app.get("/api/v1/coverage-zones", response_model=CoverageZonesResult, tags=["serviceability"])
    def coverage_zones() -> dict:
        """Service zones with at least one serviceable ZIP code."""
        return dump(core.get_coverage_zones())

    app.mount("/mcp", mcp_app)
    return app


setup_logging("serviceability-service")
app = create_app()
