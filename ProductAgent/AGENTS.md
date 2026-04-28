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

### ⚠️ Important: Two Separate Data Sources

ProductAgent has **two independent data paths** that never overlap:

| Data Source | Tools | What It Serves |
|-------------|-------|---------------|
| **`PRODUCT_CATALOG` dict** (hardcoded in `product_tools.py`) | `get_product_by_id`, `list_available_products`, `search_products_by_criteria`, `compare_products`, `suggest_alternatives`, `get_best_value_product` | Structured product details: speeds, features, technology, SLA tier, product IDs |
| **ChromaDB vector store** (RAG via `rag_tools.py`) | `search_product_knowledge` | Documentation-level questions: SLA specifics, installation process, codec details, use-case fit, technology deep-dives |

**Key nuance:** When a customer asks "Compare Fiber 1G vs 5G" or "Show me Fiber 5G details," the agent calls `compare_products` or `get_product_by_id` — these read exclusively from the hardcoded `PRODUCT_CATALOG` dictionary. **RAG is never involved in product lookups or comparisons.** RAG is only invoked when the LLM determines the question needs documentation-level depth that goes beyond the structured catalog (e.g., "What codec does Business Voice use?" or "Is fiber suitable for a medical practice?").

### Product Catalog Tools (product_tools.py) — Source: `PRODUCT_CATALOG` dict

| Tool | Signature | Purpose |
|------|-----------|---------|
| `list_available_products` | `() → List` | List all products in catalog |
| `get_product_by_id` | `(product_id) → Dict` | Get full product details |
| `search_products_by_criteria` | `(criteria) → List` | Search by speed, type, features |
| `get_product_categories` | `() → List` | List product categories |

### Comparison Tools (comparison_tools.py) — Source: `PRODUCT_CATALOG` dict

| Tool | Signature | Purpose |
|------|-----------|---------|
| `compare_products` | `(product_ids) → Dict` | Side-by-side feature comparison |
| `suggest_alternatives` | `(product_id) → List` | Recommend similar products |
| `get_best_value_product` | `(criteria) → Dict` | Find best-value match |

### RAG Tools (rag_tools.py) — Source: ChromaDB vector store

| Tool | Signature | Purpose |
|------|-----------|---------|
| `search_product_knowledge` | `(query) → str` | Semantic search over product docs |

### RAG Pipeline
```
User question → 384-dim vector (sentence-transformers) → ChromaDB cosine similarity
→ Top 3 chunks → [Source: filename — section] context → Agent composes answer
```

### Embedding Model Loading

The RAG pipeline uses `all-MiniLM-L6-v2` (87MB) from sentence-transformers. The model loading strategy adapts to the environment:

| Environment | Model Source | How |
|-------------|-------------|-----|
| **Docker (Cloud Run)** | Pre-copied local files | `COPY .hf_models/...` → `/app/.hf_models/all-MiniLM-L6-v2` |
| **Local dev (existing)** | HuggingFace cache | `~/.cache/huggingface/hub/` (already downloaded) |
| **Fresh clone** | Auto-download from HF Hub | First run of `ingest_knowledge.py` downloads ~87MB |

**Resolution logic** in `rag_manager.py`:
```python
_LOCAL_MODEL_PATH = Path(os.environ.get("EMBEDDING_MODEL_PATH", "/app/.hf_models/all-MiniLM-L6-v2"))
DEFAULT_EMBEDDING_MODEL = str(_LOCAL_MODEL_PATH) if _LOCAL_MODEL_PATH.is_dir() else "all-MiniLM-L6-v2"
```

- If `/app/.hf_models/all-MiniLM-L6-v2` exists (Docker) → loads directly from disk, no Python/PyTorch initialization overhead
- Otherwise → falls back to `"all-MiniLM-L6-v2"` which sentence-transformers resolves from HF cache or downloads

**Why not just download at Docker build time?**
Running `SentenceTransformer('all-MiniLM-L6-v2')` in Docker requires PyTorch initialization under QEMU emulation (ARM Mac → linux/amd64), which takes 10+ minutes. COPY'ing raw model files is instant.

**For Docker builders:** Run `make setup-hf-models` or manually:
```bash
mkdir -p .hf_models/sentence-transformers/all-MiniLM-L6-v2
cp -RLp ~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/*/* .hf_models/sentence-transformers/all-MiniLM-L6-v2/
```
The `.hf_models/` directory is gitignored (87MB) but included in Docker context.

---

## Conversation Behavior

### When Invoked
SuperAgent routes to ProductAgent for: "Show me products", "Compare Fiber 1G vs 5G", "SLA details", "What's the uptime guarantee?"

### Key Rule
ProductAgent returns **technical specs only** — never pricing. Pricing queries are routed to OfferManagementAgent.

---

## Integration with SuperAgent

Loaded via **importlib isolation** in `SuperAgent/super_agent/sub_agents/product/agent.py`. Agent name `product_agent` is hardcoded.
