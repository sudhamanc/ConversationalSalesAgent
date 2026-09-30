"""Pydantic models for catalog API and MCP tool results.

Public product models never carry price fields: pricing is disclosed only by
offer management. ``ProductRecord`` (internal, repository level) does.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AlternativeCriteria = Literal["faster", "similar", "different_tech"]


class ProductRecord(BaseModel):
    """Full database row, including internal commercial fields. Never returned."""

    product_id: str
    product_name: str
    category: str
    technology: str
    speeds: dict[str, str] = Field(default_factory=dict)
    description: str = ""
    features: list[str] = Field(default_factory=list)
    available: bool = True
    unit_price: Optional[float] = None
    family: Optional[str] = None
    sort_order: int = 0


class ProductSummary(BaseModel):
    product_id: str
    product_name: str
    category: str
    technology: str
    speeds: dict[str, str]


class Product(ProductSummary):
    description: str
    features: list[str]
    available: bool


class ProductDetail(Product):
    found: Literal[True] = True


class ProductList(BaseModel):
    products: list[ProductSummary]
    count: int
    category: Optional[str] = None


class SearchItem(BaseModel):
    product_id: str
    product_name: str
    category: str
    technology: str
    speeds: dict[str, str]
    description: str


class SearchCriteria(BaseModel):
    speed: Optional[str] = None
    speed_mbps: Optional[float] = None
    speed_operator: Optional[str] = None
    technology: Optional[str] = None


class SearchResult(BaseModel):
    products: list[SearchItem]
    count: int
    criteria: SearchCriteria


class CategoryList(BaseModel):
    categories: list[str]
    count: int


class ComparisonTable(BaseModel):
    product_name: list[str]
    technology: list[str]
    download_speed: list[str]
    upload_speed: list[str]
    uptime_sla: list[str]
    key_features: list[list[str]]


class Comparison(BaseModel):
    products: list[str]
    comparison_table: ComparisonTable


class CompareRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"product_ids": ["FIB-1G", "FIB-5G"]}})

    product_ids: list[str] = Field(..., min_length=2, max_length=5)


class CompareResult(BaseModel):
    comparison: Comparison
    products_compared: int
    not_found: list[str]
    fastest_product_id: Optional[str] = None
    recommendation: str


class Alternative(BaseModel):
    product_id: str
    product_name: str
    category: str
    technology: str
    speeds: dict[str, str]
    reason: str


class ProductRef(BaseModel):
    product_id: str
    product_name: str


class AlternativesResult(BaseModel):
    base_product: ProductRef
    alternatives: list[Alternative]
    count: int
    criteria: str


class BestValueResult(BaseModel):
    found: bool
    recommended: Optional[ProductSummary] = None
    category: Optional[str] = None
    reason: str


class KnowledgePassage(BaseModel):
    text: str
    doc_file: str
    section: str
    product_ids: list[str]
    product_family: Optional[str] = None
    distance: Optional[float] = None


class KnowledgeResult(BaseModel):
    available: bool
    query: str
    passages: list[KnowledgePassage] = Field(default_factory=list)
    count: int = 0
    message: Optional[str] = None


class ErrorBody(BaseModel):
    error: str
    detail: Any = None
