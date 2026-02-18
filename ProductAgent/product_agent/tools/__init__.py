"""
Tools package initialization.
"""

from .rag_tools import (
    query_product_documentation,
    search_technical_specs,
    get_product_features,
    get_sla_terms,
)

from .product_tools import (
    list_available_products,
    get_product_by_id,
    search_products_by_criteria,
    get_product_categories,
)

from .comparison_tools import (
    compare_products,
    suggest_alternatives,
    get_best_value_product,
)

__all__ = [
    # RAG tools
    "query_product_documentation",
    "search_technical_specs",
    "get_product_features",
    "get_sla_terms",
    # Product tools
    "list_available_products",
    "get_product_by_id",
    "search_products_by_criteria",
    "get_product_categories",
    # Comparison tools
    "compare_products",
    "suggest_alternatives",
    "get_best_value_product",
]
