# Product Agent

**Type:** Product catalog agent (configuration phase)
**Framework:** Google ADK 2.10, served over A2A (`sales_common.a2a_server`)
**Package:** `product_agent`. **Agent name:** `product_agent` (hardcoded; the gateway routes by it)
**Build guide:** [docs/agent-service-guide.md](../docs/agent-service-guide.md)

---

## Purpose

Answers product questions: specifications, features, SLAs, comparisons, alternatives and technical fit. It never gives pricing; offer management owns prices.

The agent contains **no catalog data and no tool implementations**. Its tools come from the **catalog service** (`services/catalog`) over MCP (streamable HTTP) through ADK `McpToolset`. The same service also serves a REST API for other systems. See [services/catalog/README.md](../services/catalog/README.md).

```text
gateway ──A2A──▶ product_agent ──MCP (CATALOG_MCP_URL)──▶ catalog service ──▶ PostgreSQL `products`
                                                                        └─▶ ChromaDB product docs
```

## Layout

```text
ProductAgent/
├── pyproject.toml     # "product-agent"; depends on sales-common only
├── Dockerfile         # build context = repo root; no PyTorch
├── product_agent/
│   ├── __init__.py    # build_agent, root_agent
│   ├── agent.py       # build_agent(model=None, *, catalog_mcp_url=None) -> Agent
│   ├── prompts.py     # PRODUCT_AGENT_INSTRUCTION (static_instruction), PRODUCT_SHORT_DESCRIPTION
│   └── server.py      # app = create_a2a_app(root_agent, uses_database=False)
└── tests/
```

## Agent configuration

| Attribute | Value |
|---|---|
| `tools` | `[mcp_toolset(CATALOG_MCP_URL, tool_filter=CATALOG_TOOLS)]` |
| `static_instruction` | `PRODUCT_AGENT_INSTRUCTION` (domain prompt, no transfer instructions) |
| `instruction` | `sales_common.prompts.JOURNEY_CONTEXT_INSTRUCTION` |
| `before_agent_callback` | `import_forwarded_context` |
| `after_tool_callback` | `export_context_delta` |
| Generation | temperature 0.0, top_p 0.2, top_k 20, max 2048 tokens, safety from `SAFETY_*` |

## Tools (served by the catalog MCP server)

| Tool | Arguments | Purpose |
|---|---|---|
| `list_available_products` | `category?` | List products, optionally by category (aliases such as `fiber` or `sdwan` work) |
| `get_product_by_id` | `product_id` | Full specs (case-insensitive id); `found: false` when unknown |
| `search_products_by_criteria` | `speed?`, `technology?` | Numeric download-speed filter (`1 Gbps`, `>= 500 Mbps`, `under 1 Gbps`) and technology |
| `get_product_categories` | none | Category names |
| `compare_products` | `product_ids` (2..5) | Comparison table and `fastest_product_id` (numeric) |
| `suggest_alternatives` | `product_id`, `criteria?` (`faster`, `similar`, `different_tech`) | Up to 5 alternatives with reasons |
| `get_best_value_product` | `category?` | Highest-throughput product; no budget parameter |
| `search_product_knowledge` | `query`, `top_k?` | Passages from product docs (`doc_file`, `section`, `product_ids`); `available: false` when the index is down |

- Every result is a JSON object (MCP `structuredContent`).
- No result contains `price` or `unit_price`.
- Tool names are unchanged from the in-process version, so the prompt still refers to them by name.

## Environment

| Variable | Required | Notes |
|---|---|---|
| `CATALOG_MCP_URL` | yes | e.g. `http://catalog:8101/mcp/` (trailing slash); Cloud Run: `https://catalog-...run.app/mcp/` |
| `GEMINI_MODEL`, `GOOGLE_API_KEY` | yes | no model default |
| `DATABASE_URL` | yes | ADK sessions and A2A tasks only |
| `PUBLIC_URL` | yes | agent card URL |
| `SERVICE_AUTH` | no | `gcp_id_token` on Cloud Run: MCP calls carry an ID token for the catalog service |
| `MCP_TIMEOUT_SECONDS`, `MCP_TOOL_CACHE_SECONDS` | no | defaults 15 / 300 |

## Run and test

```bash
uvicorn product_agent.server:app --host 0.0.0.0 --port 8003     # from ProductAgent/, after pip install
pytest ProductAgent/tests -q                                      # set TEST_DATABASE_URL to include the server import test
```

Tests (no API key, no catalog service needed):

- Construction: the toolset URL comes from `CATALOG_MCP_URL`; the tool filter lists the 8 names; callbacks and generation config are set.
- The prompt contains no transfer mechanics.
- End to end: `ScriptLlm` calls `get_product_by_id` through `McpToolset` against a stub MCP server.

## Rules

- Do not add local tools or catalog data here. Change `services/catalog` instead.
- Keep the output formats in `prompts.py`; the UI shows them as they are.
- Pricing questions: the agent says pricing comes from the offer specialist. The gateway routes the next turn; the agent cannot transfer.

## History

- Up to v1 the catalog was a Python dict in `product_tools.py` and RAG ran in-process with ChromaDB and PyTorch.
- Legacy defects fixed in the service:
  - case-sensitive ids
  - lexical speed comparison (`"5 Gbps" > "10 Gbps"`)
  - ignored `max_price` / `max_budget` parameters
- The old FastAPI `main.py` (`/query`, `/products`, cache endpoints) is gone. The A2A `server.py` and the catalog REST API replace it.
