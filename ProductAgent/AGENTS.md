# Product Agent

**Type:** Info/RAG Agent (Configuration Phase)
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
   - ChromaDB/RAG setup → This file (see Tools section)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Purpose

The Product Agent retrieves technical product specifications using **RAG (Retrieval-Augmented Generation)** with ChromaDB. It provides accurate, zero-hallucination responses about business internet products by querying a vector database of product manuals and documentation.

**Key Responsibilities:**

1. **Product Lookup** - Query specs by name/ID
2. **Semantic Search** - Find products matching customer needs
3. **Product Comparison** - Side-by-side feature analysis
4. **Infrastructure Filtering** - Only recommend products compatible with available infrastructure
5. **Technical Documentation** - SLAs, features, hardware details

---

## Architecture

| Attribute | Value |
|-----------|-------|
| **Type** | Info/RAG |
| **Phase** | Configuration (Phase 2) |
| **Source of Truth** | Vector DB (ChromaDB) + Product Catalog |
| **Temperature** | 0.1 (low, for factual accuracy) |
| **Invocation** | After ServiceabilityAgent confirms infrastructure |

---

## Tools

11 specialized tools organized into 3 categories:

### RAG Tools (`rag_tools.py`)

1. `semantic_search_products(query: str)` - Natural language product search
2. `get_product_by_name(product_name: str)` - Exact name lookup
3. `query_product_documentation(product_id: str, question: str)` - Q&A on product docs

### Product Catalog Tools (`product_tools.py`)

4. `get_all_products()` - Full catalog
5. `get_products_by_category(category: str)` - Filter by Internet/Voice/Cloud
6. `get_product_specs(product_id: str)` - Technical specifications
7. `filter_by_infrastructure(products: list, infrastructure_type: str, max_speed: int)` - Infrastructure-aware filtering

### Comparison Tools (`comparison_tools.py`)

8. `compare_products(product_ids: list[str])` - Side-by-side comparison
9. `recommend_alternatives(product_id: str, reason: str)` - Suggest alternatives
10. `get_product_bundles()` - Available product bundles
11. `calculate_product_fit_score(product_id: str, requirements: dict)` - Match scoring

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

## Vector Database (ChromaDB)

**Storage:** `data/embeddings/` (git-ignored)
**Documents:** Product PDFs in `data/product_docs/`

**Indexed Fields:**
- Product name, description
- Technical specifications
- Features, SLAs
- Hardware requirements
- Use cases

**Embedding Model:** model2vec (local, no API calls)

---

## Integration Steps (Future)

1. Create wrapper in `SuperAgent/super_agent/sub_agents/product/`
2. Use importlib isolation pattern
3. Register in `super_agent/agent.py`
4. Add routing rule: "Tell me about [product]", "What internet plans?"

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
