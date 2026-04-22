"""
RAG tool for ProductAgent — exposes search_product_knowledge as an ADK-compatible function.

The ChromaDB singleton is lazily initialized on the first function call, so
importing this module never triggers model download or DB connection.
"""

from __future__ import annotations

from ..utils.logger import get_logger

logger = get_logger(__name__)


def search_product_knowledge(query: str) -> str:
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
               Be specific — include product names or IDs when known.

    Returns:
        Relevant excerpts from the product knowledge base, or a message
        indicating no relevant information was found.
    """
    if not query or not query.strip():
        return "Please provide a specific question to search the product knowledge base."

    try:
        try:
            from ..utils.rag_manager import get_rag_manager
        except ImportError:
            # Fallback for when the module is loaded via importlib without a
            # proper package context (e.g., loaded dynamically by SuperAgent).
            import importlib.util as _ilu
            import os as _os
            _here = _os.path.dirname(_os.path.abspath(__file__))
            _spec = _ilu.spec_from_file_location(
                "product_agent.utils.rag_manager",
                _os.path.join(_here, "..", "utils", "rag_manager.py"),
            )
            _mod = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            get_rag_manager = _mod.get_rag_manager

        rag = get_rag_manager()

        if rag.document_count() == 0:
            logger.warning("rag_empty_collection")
            return (
                "The product knowledge base has not been populated yet. "
                "Please run the ingestion script: "
                "python ProductAgent/scripts/ingest_knowledge.py"
            )

        context = rag.get_context(query_text=query.strip(), n_results=3)

        if not context:
            return (
                "No specific documentation found for that question. "
                "I can still answer using the structured product catalog — "
                "try asking me to list or compare products directly."
            )

        logger.info("rag_query_success query=%s", query[:80])
        return context

    except ImportError as exc:
        logger.error("rag_import_error: %s", exc)
        return (
            "RAG dependencies are not installed. "
            "Run: pip install chromadb>=0.5.0 sentence-transformers>=2.7.0"
        )
    except Exception as exc:
        logger.error("rag_query_error: %s", exc)
        return f"An error occurred searching the product knowledge base: {exc}"
