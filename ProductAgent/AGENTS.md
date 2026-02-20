# Product Agent

**Type:** Product Catalog Agent (Configuration Phase)
**Framework:** Google ADK 1.20.0
**Package:** `product_agent`
**Status:** ✅ Deployed in SuperAgent

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [Root CLAUDE.md](/CLAUDE.md)
   - [Root AGENTS.md](/AGENTS.md)
   - This file (ProductAgent/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Agent development → [Root AGENTS.md - Golden Rule](/AGENTS.md#the-golden-rule)
   - Product catalog changes → `product_agent/tools/product_tools.py`

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Purpose

The Product Agent retrieves technical product specifications from a deterministic in-repo product catalog. It provides accurate, zero-hallucination responses about business telecom products using catalog and comparison tools.

**Key Responsibilities:**

1. **Product Lookup** - Query specs by name/ID
2. **Criteria Search** - Find products matching customer needs
3. **Product Comparison** - Side-by-side feature analysis
4. **Infrastructure Filtering** - Only recommend products compatible with available infrastructure
5. **Technical Guidance** - Speeds, features, technology compatibility

---

## Architecture

| Attribute | Value |
|-----------|-------|
| **Type** | Catalog/Comparison |
| **Phase** | Configuration (Phase 2) |
| **Source of Truth** | Product catalog + deterministic comparison logic |
| **Temperature** | 0.0 (deterministic for factual accuracy) |
| **Invocation** | After ServiceabilityAgent confirms infrastructure |

---

## Tools

7 specialized tools organized into 2 categories:

### Product Catalog Tools (`product_tools.py`)

1. `list_available_products(category: str | None)` - Full catalog or category filtered
2. `get_product_by_id(product_id: str)` - Product details by ID
3. `search_products_by_criteria(...)` - Criteria-based filtering
4. `get_product_categories()` - Available categories

### Comparison Tools (`comparison_tools.py`)

5. `compare_products(product_ids: list[str])` - Side-by-side technical comparison
6. `suggest_alternatives(product_id: str, criteria: str)` - Suggest alternatives
7. `get_best_value_product(max_budget: int | None)` - Deterministic value recommendation

---

## Infrastructure-Aware Filtering

When ServiceabilityAgent provides infrastructure context, ProductAgent automatically filters:

**Infrastructure Context Format:**
```
[INFRASTRUCTURE AVAILABILITY]
Location: 123 Main St, Philadelphia, PA 19103
Network Type: Fiber
Speed Capability: 10 Gbps (max download), 10 Gbps (max upload)
Connection Type: Symmetrical
Service Class: Business
```

**Filtering Rules:**

- **Fiber infrastructure** → Only FTTP/Fiber products
- **Coax infrastructure** → Only HFC/Cable products
- **Max speed limit** → Exclude products exceeding infrastructure capacity
- **Symmetrical requirement** → Only products with symmetric upload/download

---

## Integration Steps (Future)

1. Keep wrapper in `SuperAgent/super_agent/sub_agents/product/` aligned with ProductAgent imports
2. Maintain deterministic catalog/comparison tool behavior
3. Keep routing in `super_agent/prompts.py` for technical product questions
4. Route all commercial/pricing asks to OfferManagementAgent

---

## Development

```bash
cd ProductAgent
pip install -e .
python main.py  # FastAPI server
# OR
adk web
```

**Related Documentation:** [/AGENTS.md](/AGENTS.md)
