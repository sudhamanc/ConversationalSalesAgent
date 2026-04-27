# Product Agent

**Type:** Product Catalog Agent (Configuration Phase)
**Framework:** Google ADK 1.20.0+
**Package:** `product_agent`
**Status:** ✅ Deployed in SuperAgent

---

## Purpose

The Product Agent provides **deterministic product catalog lookup, technical comparison, and RAG-powered knowledge search**. It answers questions about product specifications, SLAs, features, and compatibility without any pricing information (pricing is handled by OfferManagementAgent).

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `product_agent` (hardcoded) |
| **Model** | `os.getenv("GEMINI_MODEL")` — no default |
| **Temperature** | 0.0 (deterministic) |
| **Top P** | 0.2 |
| **Top K** | 20 |
| **Max Tokens** | 2048 |
| **Safety** | `BLOCK_LOW_AND_ABOVE` for all categories |
| **Database** | None (in-memory catalog + ChromaDB for RAG) |

### Component Structure

```
ProductAgent/
├── product_agent/
│   ├── __init__.py
│   ├── agent.py                    # Agent definition
│   ├── prompts.py                  # System instructions
│   ├── tools/
│   │   ├── product_tools.py        # Catalog CRUD
│   │   ├── comparison_tools.py     # Product comparison
│   │   └── rag_tools.py            # ChromaDB vector search
│   └── config.py
├── data/
│   ├── products/                   # Product JSON catalog
│   ├── knowledge/                  # RAG source documents
│   └── embeddings/                 # ChromaDB (gitignored)
├── scripts/
│   └── ingest_knowledge.py         # Vector store ingestion
└── tests/
```

---

## Tools (8 Functions)

### Product Catalog Tools (product_tools.py)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `list_available_products` | `() → List` | List all products in catalog |
| `get_product_by_id` | `(product_id) → Dict` | Get full product details |
| `search_products_by_criteria` | `(criteria) → List` | Search by speed, type, features |
| `get_product_categories` | `() → List` | List product categories |

### Comparison Tools (comparison_tools.py)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `compare_products` | `(product_ids) → Dict` | Side-by-side feature comparison |
| `suggest_alternatives` | `(product_id) → List` | Recommend similar products |
| `get_best_value_product` | `(criteria) → Dict` | Find best-value match |

### RAG Tools (rag_tools.py)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `search_product_knowledge` | `(query) → str` | Semantic search over product docs |

### RAG Pipeline
```
User question → 384-dim vector (sentence-transformers) → ChromaDB cosine similarity
→ Top 3 chunks → [Source: filename — section] context → Agent composes answer
```

---

## Conversation Behavior

### When Invoked
SuperAgent routes to ProductAgent for: "Show me products", "Compare Fiber 1G vs 5G", "SLA details", "What's the uptime guarantee?"

### Key Rule
ProductAgent returns **technical specs only** — never pricing. Pricing queries are routed to OfferManagementAgent.

---

## Integration with SuperAgent

Loaded via **importlib isolation** in `SuperAgent/super_agent/sub_agents/product/agent.py`. Agent name `product_agent` is hardcoded.
