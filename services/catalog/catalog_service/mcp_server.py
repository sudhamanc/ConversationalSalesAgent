"""MCP server exposing the catalog as the 8 product-agent tools plus search_faq (FAQ agent).

Tools are thin wrappers over :mod:`catalog_service.core`; every result is a
JSON object (``structuredContent``). Input errors and unknown products are
returned as data (``success: false`` / ``found: false``) so the model can
react, mirroring the legacy in-process tools.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import anyio
from mcp.server.mcpserver import MCPServer

from . import core
from .core import InvalidInputError, ProductNotFoundError

TOOL_NAMES = (
    "list_available_products",
    "get_product_by_id",
    "search_products_by_criteria",
    "get_product_categories",
    "compare_products",
    "suggest_alternatives",
    "get_best_value_product",
    "search_product_knowledge",
    "search_faq",
)
#: Tools the product agent uses (everything except the FAQ agent's search_faq).
PRODUCT_TOOL_NAMES = TOOL_NAMES[:-1]


async def _call(fn: Callable[..., Any], *args: Any) -> dict[str, Any]:
    result = await anyio.to_thread.run_sync(fn, *args)
    return result.model_dump(exclude_none=False)


def build_mcp() -> MCPServer:
    """Create a fresh MCP server (a session manager can only run once per instance)."""
    mcp = MCPServer(
        name="catalog",
        instructions=(
            "Product catalog for a B2B telecom provider: technical specifications, "
            "comparisons and product documentation. Pricing is never disclosed here."
        ),
    )

    @mcp.tool()
    async def list_available_products(category: Optional[str] = None) -> dict[str, Any]:
        """List all available products or filter by category.

        Args:
            category: Optional category filter, e.g. "Fiber Internet", "Coax Internet",
                "Voice", "SD-WAN", "Business Mobile". Aliases such as "fiber", "voice",
                "sdwan" or "mobile" are accepted.

        Returns:
            dict with ``products`` (id, name, category, technology, speeds), ``count``
            and the canonical ``category`` when filtered.
        """
        return await _call(core.list_available_products, category)

    @mcp.tool()
    async def get_product_by_id(product_id: str) -> dict[str, Any]:
        """Get complete product information by product ID (case-insensitive).

        Args:
            product_id: Product identifier, e.g. "FIB-5G".

        Returns:
            dict with the product's specifications and ``found: true``, or
            ``found: false`` with a message when the product does not exist.
            Pricing is not included (offer management provides prices).
        """
        try:
            return await _call(core.get_product_by_id, product_id)
        except ProductNotFoundError as exc:
            return {"found": False, "product_id": product_id, "message": str(exc)}
        except InvalidInputError as exc:
            return {"found": False, "product_id": product_id, "message": str(exc)}

    @mcp.tool()
    async def search_products_by_criteria(
        speed: Optional[str] = None, technology: Optional[str] = None
    ) -> dict[str, Any]:
        """Search products by download speed and/or technology.

        Args:
            speed: Download speed filter compared numerically, e.g. "1 Gbps" (exact),
                ">= 500 Mbps", "at least 1 Gbps", "under 500 Mbps".
            technology: Technology type, e.g. "FTTP", "HFC", "DOCSIS 3.1" (case-insensitive).

        Returns:
            dict with matching ``products``, ``count`` and the parsed ``criteria``.
        """
        try:
            return await _call(core.search_products_by_criteria, speed, technology)
        except InvalidInputError as exc:
            return {"success": False, "error": str(exc), "products": [], "count": 0}

    @mcp.tool()
    async def get_product_categories() -> dict[str, Any]:
        """Get the list of all product categories.

        Returns:
            dict with ``categories`` and ``count``.
        """
        return await _call(core.get_product_categories)

    @mcp.tool()
    async def compare_products(product_ids: list[str]) -> dict[str, Any]:
        """Compare 2-5 products side-by-side.

        Generates a comparison table of key technical differences (technology,
        speeds, uptime SLA, key features) and names the fastest product,
        comparing speeds numerically.

        Args:
            product_ids: List of 2-5 product IDs to compare, e.g. ["FIB-1G", "FIB-5G"].

        Returns:
            dict with ``comparison``, ``products_compared``, ``not_found``,
            ``fastest_product_id`` and ``recommendation``.
        """
        try:
            return await _call(core.compare_products, product_ids)
        except (InvalidInputError, ProductNotFoundError) as exc:
            return {"success": False, "error": str(exc), "products_compared": 0}

    @mcp.tool()
    async def suggest_alternatives(product_id: str, criteria: Optional[str] = None) -> dict[str, Any]:
        """Suggest alternative products based on a given product.

        Args:
            product_id: Base product ID to find alternatives for.
            criteria: Optional: "faster" (higher download speed), "similar" (same
                technology) or "different_tech" (same product family, different
                technology). Omit for products in the same category.

        Returns:
            dict with ``base_product``, up to 5 ``alternatives`` (each with a
            ``reason``), ``count`` and ``criteria``.
        """
        try:
            return await _call(core.suggest_alternatives, product_id, criteria)
        except (InvalidInputError, ProductNotFoundError) as exc:
            return {"success": False, "error": str(exc), "alternatives": [], "count": 0}

    @mcp.tool()
    async def get_best_value_product(category: Optional[str] = None) -> dict[str, Any]:
        """Get a technical best-fit recommendation (highest throughput) without pricing.

        Args:
            category: Optional category to rank within, e.g. "Fiber Internet" or "SD-WAN".

        Returns:
            dict with ``found``, ``recommended`` product and ``reason``.
            Budget-based recommendations are handled by offer management.
        """
        return await _call(core.get_best_value_product, category)

    @mcp.tool()
    async def search_product_knowledge(query: str, top_k: int = core.DEFAULT_TOP_K) -> dict[str, Any]:
        """Search the product knowledge base for detailed information about product
        specifications, SLAs, installation requirements, use cases, technical
        deep-dives, and frequently asked customer questions.

        Use this tool when:
        - A customer asks about uptime SLA or reliability commitments for a product
        - A customer asks about installation process, lead time, or hardware requirements
        - A customer asks whether a product is suitable for a specific industry or use case
        - A customer asks a technical question that goes beyond the structured catalog
          (e.g., "What codec does Business Voice use?", "Does SD-WAN support ZTNA?")
        - A customer asks a comparison question about technology differences
          (e.g., "What is the difference between fiber and coax?")
        - Follow-up Q&A after a catalog tool has already returned a product result

        Do NOT use this tool for:
        - Listing or filtering products by category, speed, or availability
          (use list_available_products, search_products_by_criteria instead)
        - Comparing multiple products side by side by spec columns
          (use compare_products instead)

        Args:
            query: The customer's question or search phrase, in natural language.
                Be specific; include product names or IDs when known.
            top_k: Number of passages to return (1-10, default 4).

        Returns:
            dict with ``available``, ``passages`` (text, doc_file, section,
            product_ids) and ``count``. ``available: false`` means the knowledge
            base is not reachable; answer from the catalog tools instead.
        """
        try:
            return await _call(core.search_product_knowledge, query, top_k)
        except InvalidInputError as exc:
            return {"available": True, "success": False, "error": str(exc), "passages": [], "count": 0}

    @mcp.tool()
    async def search_faq(query: str, top_k: int = core.DEFAULT_TOP_K) -> dict[str, Any]:
        """Search Connectivity Max's FAQ and policy documents: contract terms, renewals,
        quote validity, installation process and windows, support hours and channels,
        SLA and service credits, payment methods and payment plans, cancellation,
        early termination and order changes.

        These passages are the only approved source for policy answers. Answer only
        with facts they contain; if no passage answers the question, say a specialist
        will follow up.

        Args:
            query: The customer's question in natural language.
            top_k: Number of passages to return (1-10, default 4).

        Returns:
            dict with ``available``, ``passages`` (text, topic, section, doc_file,
            distance) and ``count``. ``available: false`` means the FAQ index is not
            reachable.
        """
        try:
            return await _call(core.search_faq, query, top_k)
        except InvalidInputError as exc:
            return {"available": True, "success": False, "error": str(exc), "passages": [], "count": 0}

    return mcp
