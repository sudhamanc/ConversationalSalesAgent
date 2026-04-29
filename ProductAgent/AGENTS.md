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

### Complete RAG Pipeline — Step by Step

#### What Exists on Disk

```
ProductAgent/
├── data/
│   ├── product_docs/              ← SOURCE: 5 markdown knowledge files (858 lines)
│   │   ├── fiber_internet.md      (156 lines — SLAs, install process, use cases)
│   │   ├── coax_internet.md       (134 lines)
│   │   ├── voice_services.md      (195 lines)
│   │   ├── sd_wan.md              (174 lines)
│   │   └── mobile_services.md     (173 lines)
│   └── embeddings/                ← OUTPUT: ChromaDB vector store (3.2 MB, gitignored)
│       ├── chroma.sqlite3         (vector index + metadata)
│       └── 1465b650-.../          (binary HNSW vector data)
│
.hf_models/                        ← PROJECT ROOT (gitignored, 87 MB)
└── sentence-transformers/
    └── all-MiniLM-L6-v2/
        ├── model.safetensors      (neural network weights — 87 MB)
        ├── tokenizer.json         (WordPiece tokenizer)
        ├── vocab.txt              (30,522 tokens)
        └── config.json            (model architecture definition)
```

#### Local Development Flow

**Step 1: Model Download (one-time, automatic)**

When you first run the ingestion script, `SentenceTransformer('all-MiniLM-L6-v2')` checks `~/.cache/huggingface/hub/`. If not cached, it downloads 87 MB from HuggingFace Hub. This happens once ever per machine.

**Step 2: Run Ingestion Script (one-time, or when product docs change)**

```bash
python ProductAgent/scripts/ingest_knowledge.py
```

What happens inside `ingest_knowledge.py`:
1. Reads all `.md` files from `ProductAgent/data/product_docs/`
2. Splits each file into chunks by `##`/`###` headings (~1800 chars max per chunk)
3. Loads `SentenceTransformer('all-MiniLM-L6-v2')` from HF cache
4. Encodes each text chunk → 384-dimension float vector
5. Upserts vectors + text + metadata into ChromaDB at `ProductAgent/data/embeddings/`
6. Idempotent — re-running only refreshes changed content (stable doc IDs)

**Step 3: Runtime (every RAG query)**

When a user asks a documentation-level question:
1. ProductAgent LLM decides to call `search_product_knowledge(query)`
2. `rag_manager.py` initializes lazily (first call only):
   - Opens ChromaDB persistent client from `ProductAgent/data/embeddings/`
   - Loads `SentenceTransformer` from `~/.cache/huggingface/hub/`
3. Encodes the user's query string → 384-dim vector
4. ChromaDB cosine similarity search → returns top 3 matching chunks
5. Formatted text returned to the LLM as grounded context for its answer

**Model path resolution (local):**
```python
_LOCAL_MODEL_PATH = "/app/.hf_models/all-MiniLM-L6-v2"  # doesn't exist locally
# Falls back to: DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2" → resolves from HF cache
```

#### Docker / Cloud Run Flow

**Build Time (Dockerfile):**

```dockerfile
# Step 1: Product docs + pre-built embeddings copied together
COPY ProductAgent/ ./ProductAgent/
# ↳ includes data/product_docs/ AND data/embeddings/ (pre-built locally!)

# Step 2: Model files copied directly — no Python/PyTorch execution needed
COPY .hf_models/sentence-transformers/all-MiniLM-L6-v2 /app/.hf_models/all-MiniLM-L6-v2
```

**No ingestion script runs at build time.** The embeddings were already generated on your local machine and COPY'd into the image.

**Runtime (every RAG query):**

1. User asks a question → ProductAgent calls `search_product_knowledge(query)`
2. `rag_manager.py` initializes lazily (first call only):
   - Opens ChromaDB from `/app/ProductAgent/data/embeddings/` (COPY'd at build)
   - Checks: `/app/.hf_models/all-MiniLM-L6-v2` exists? **YES** → loads from disk
3. Encodes query → 384-dim vector
4. ChromaDB similarity search → top 3 chunks → returned as context

**Model path resolution (Docker):**
```python
_LOCAL_MODEL_PATH = "/app/.hf_models/all-MiniLM-L6-v2"  # EXISTS in container
# Uses: DEFAULT_EMBEDDING_MODEL = "/app/.hf_models/all-MiniLM-L6-v2" → loads from disk
```

#### Local vs Docker Comparison

| Step | Local Dev | Docker/Cloud Run |
|------|-----------|-----------------|
| **Model source** | `~/.cache/huggingface/hub/` (auto-downloaded once) | `/app/.hf_models/all-MiniLM-L6-v2` (COPY'd at build) |
| **Embeddings created by** | `python scripts/ingest_knowledge.py` (you run manually) | Never — COPY'd from your local `ProductAgent/data/embeddings/` |
| **Embeddings location** | `ProductAgent/data/embeddings/` | `/app/ProductAgent/data/embeddings/` |
| **When model loads** | First `search_product_knowledge` call | First `search_product_knowledge` call |
| **Network needed?** | Only first-ever model download | Never |
| **Ingestion time** | ~5 seconds | N/A (pre-built) |

#### Why COPY Instead of RUN?

Running `SentenceTransformer('all-MiniLM-L6-v2')` during `docker build` requires PyTorch initialization. On ARM Macs building linux/amd64 images via QEMU emulation, this takes **10+ minutes** (CPU emulation overhead). COPY'ing the raw model files is instant (0.1s).

---

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
