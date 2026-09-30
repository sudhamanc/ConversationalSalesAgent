"""Catalog service: REST API under ``/api/v1`` and MCP server at ``/mcp/``.

Run with ``uvicorn catalog_service.app:app --host 0.0.0.0 --port $PORT``.
"""

from __future__ import annotations

import contextlib
import threading
from typing import Annotated, Any, Optional

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from sales_common import db
from sales_common.config import env_bool
from sales_common.logging import setup_logging

from . import __version__, core, rag
from .core import InvalidInputError, ProductNotFoundError
from .mcp_server import build_mcp
from .models import (
    AlternativeCriteria,
    AlternativesResult,
    BestValueResult,
    CategoryList,
    CompareRequest,
    CompareResult,
    KnowledgeResult,
    ProductDetail,
    ProductList,
    SearchResult,
)

SERVICE_NAME = "catalog-service"


def _router() -> APIRouter:
    api = APIRouter(prefix="/api/v1", tags=["catalog"])

    @api.get("/products", response_model=ProductList)
    def list_products(category: Optional[str] = None) -> Any:
        """List available products, optionally filtered by category (aliases accepted)."""
        return core.list_available_products(category).model_dump()

    @api.get("/products/search", response_model=SearchResult)
    def search_products(
        speed: Annotated[Optional[str], Query(max_length=64)] = None,
        technology: Annotated[Optional[str], Query(max_length=64)] = None,
    ) -> Any:
        """Search by download speed (numeric; ``1 Gbps``, ``>= 500 Mbps``, ``under 1 Gbps``) and technology."""
        return core.search_products_by_criteria(speed, technology).model_dump()

    @api.get("/products/best-value", response_model=BestValueResult)
    def best_value(
        category: Optional[str] = None,
        max_budget: Annotated[
            Optional[float],
            Query(
                ge=0,
                deprecated=True,
                description="Accepted for compatibility and not applied: pricing is not disclosed "
                "by the catalog; budget fit is handled by offer management.",
            ),
        ] = None,
    ) -> Any:
        """Highest-throughput product, optionally within a category."""
        return core.get_best_value_product(category).model_dump()

    @api.get("/categories", response_model=CategoryList)
    def categories() -> Any:
        return core.get_product_categories().model_dump()

    @api.post("/products/compare", response_model=CompareResult)
    def compare(body: CompareRequest) -> Any:
        """Compare 2-5 products; names the fastest (numeric speed comparison)."""
        return core.compare_products(body.product_ids).model_dump()

    @api.get("/products/{product_id}", response_model=ProductDetail)
    def get_product(product_id: str) -> Any:
        """Product details by id (case-insensitive). Never includes price fields."""
        return core.get_product_by_id(product_id).model_dump()

    @api.get("/products/{product_id}/alternatives", response_model=AlternativesResult)
    def alternatives(product_id: str, criteria: Optional[AlternativeCriteria] = None) -> Any:
        return core.suggest_alternatives(product_id, criteria).model_dump()

    @api.get("/knowledge/search", response_model=KnowledgeResult)
    def knowledge_search(
        q: Annotated[str, Query(min_length=1, max_length=500)],
        top_k: Annotated[int, Query(ge=1, le=core.MAX_TOP_K)] = core.DEFAULT_TOP_K,
    ) -> Any:
        """Top-k passages from the product documents (``available: false`` if the index is down)."""
        return core.search_product_knowledge(q, top_k).model_dump()

    return api


def create_app(*, rag_warmup: Optional[bool] = None) -> FastAPI:
    """Build the FastAPI app. Each call creates its own MCP server instance."""
    mcp = build_mcp()
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        host="0.0.0.0",  # disables localhost-only Host checks (HTTP 421 on Cloud Run)
    )
    warmup = env_bool("RAG_BUILD_ON_START", True) if rag_warmup is None else rag_warmup

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        setup_logging(SERVICE_NAME)
        if warmup:
            threading.Thread(target=rag.warm_up, name="rag-warmup", daemon=True).start()
        async with mcp.session_manager.run():
            yield
        db.close_pool()

    app = FastAPI(
        title="Product Catalog Service",
        version=__version__,
        description="Product catalog and knowledge search (REST + MCP). Pricing is not disclosed.",
        lifespan=lifespan,
    )

    @app.exception_handler(ProductNotFoundError)
    async def _not_found(_request: Request, exc: ProductNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": "not_found", "detail": str(exc)})

    @app.exception_handler(InvalidInputError)
    async def _invalid(_request: Request, exc: InvalidInputError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_input", "detail": jsonable_encoder(exc.errors())},
        )

    @app.get("/healthz", tags=["ops"])
    def healthz() -> JSONResponse:
        healthy = db.ping()
        return JSONResponse(
            {"status": "ok" if healthy else "degraded", "service": SERVICE_NAME, "knowledge": rag.status()},
            status_code=200 if healthy else 503,
        )

    app.include_router(_router())
    app.mount("/mcp", mcp_app)
    app.state.mcp = mcp
    return app


app = create_app()
