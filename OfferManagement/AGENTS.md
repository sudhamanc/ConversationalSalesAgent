# Offer Management Agent

**Type:** Deterministic Agent (Pricing & Quoting)
**Framework:** Google ADK 2.10 (A2A service)
**Package:** `offer_management` (project `offer-management-agent`)
**A2A name:** `offer_management_agent` (hardcoded) · local port 8204
**Contract:** [docs/agent-service-guide.md](../docs/agent-service-guide.md)

---

## Purpose

The Offer Management Agent performs **deterministic pricing calculation, discount application, and quote generation**. It computes exact prices from a hardcoded price book — no LLM involvement in pricing math.

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `offer_management_agent` (hardcoded) |
| **Model** | `GEMINI_MODEL` via `sales_common.config.model_name()` — no default |
| **Instructions** | `static_instruction` = `OFFER_MANAGEMENT_AGENT_INSTRUCTION`; `instruction` = `JOURNEY_CONTEXT_INSTRUCTION` |
| **Callbacks** | `before_agent_callback=[import_forwarded_context]`, `after_tool_callback=[export_context_delta]` |
| **Temperature** | 0.0 (deterministic) · max 2048 output tokens (`generate_config`) |
| **Database** | PostgreSQL (`DATABASE_URL`) → `quotes` table via `sales_common.db` |

### Component Structure

```
OfferManagement/
├── pyproject.toml                  # offer-management-agent, depends on sales-common
├── Dockerfile                      # build context = repo root
├── offer_management/
│   ├── __init__.py                 # exports build_agent, root_agent
│   ├── agent.py                    # build_agent(model=None) -> Agent
│   ├── prompts.py                  # static domain prompt
│   ├── server.py                   # app = create_a2a_app(root_agent)
│   ├── tools/pricing_tools.py      # pricing engine + quote tools
│   └── utils/
│       ├── cache.py                # in-memory result cache (1h TTL)
│       └── quote_db.py             # quotes persistence (sales_common.db)
└── tests/                          # tool tests (Postgres) + ScriptLlm agent test
```

Persistence is PostgreSQL only (see `db/README.md`); the legacy SQLite file was removed.

### Database Tables (Offer domain)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `quotes` | Persisted price quotes | offer_id (PK), customer_id, items_json, term_months, bant_score, subtotal, total_discount, total_price, status, expires_at |

Schema lives in `db/migrations/001_sales_schema.sql`; the agent never creates tables.

---

## Tools (4 functions)

| Tool | Signature | Tables | Purpose |
|------|-----------|--------|---------|
| `find_best_bundle_offer` | `(items, term_months, bant_score) → Dict` | — | Discount rates + deterministic offer id |
| `generate_offer_quote` | `(items, term_months, bant_score, customer_id, company_name, customer_email) → Dict` | `quotes` UPSERT, `notifications` INSERT | Itemized quote; persists it; enqueues `quote_confirmation` |
| `get_existing_quotes` | `(company_name, customer_id) → Dict` | `quotes` SELECT | Active quotes for a returning customer |
| `get_quote_details` | `(offer_id) → Dict` | `quotes` SELECT | Full quote by id |

### Pricing Engine

Price book (`PRODUCT_PRICE_BOOK`): 16 SKUs across internet, voice, SD-WAN and mobile families.

Discount layers (applied sequentially per item):
1. **Bundle:** internet+voice 5%, internet+SD-WAN 7%, internet+voice+SD-WAN 10%
2. **Term:** 12 mo 0%, 24 mo 5%, 36 mo 10%
3. **BANT:** score ≥ 66.7 → 8% (Tier A), ≥ 33.3 → 4% (Tier B), else 0%

### Journey context and outputs

- `generate_offer_quote` reads `customer_context` (customer_id, company_name) from state when the model omits them.
- It writes `offer_context` = `{offer_id, customer_id, company_name, items, term_months, total_price, monthly_total, total_discount}`; `export_context_delta` returns it to the gateway as `_context_update.offer_context`.
- Response fields used by the UI (`QuoteCard.jsx`): `offer_id`, `items[]` (product_id, product_name, quantity, price_points, discount, discount_detail, final_price), `subtotal`, `discount_breakdown[]`, `total_discount`, `total_price`, `monthly_total`, `yearly_total`, `term_months`, and `notification_sent` (`{type, recipient, quote_id, notification_id, status}`) when a confirmation was enqueued. The response also carries `bant_score`, which `save_quote` persists to `quotes.bant_score`.

### Cross-service integration

- **Notifications:** the quote upsert and `notifications.enqueue("quote_confirmation", ...)` run in one transaction (outbox). The communication service delivers it. `args` carry offer_id, company/customer, items, totals, term, discount breakdown and expiry.
- **Quote status:** the order service marks a quote `ordered` with `sales_common.repositories.quotes.mark_ordered`.
- Lifecycle: `active` → `ordered` → `expired` (30-day `expires_at`; expired by `sales_common.maintenance`).

---

## Running

```bash
uv pip install -e libs/sales_common -e OfferManagement
GEMINI_MODEL=... DATABASE_URL=postgresql://... PUBLIC_URL=http://localhost:8204 \
  uvicorn offer_management.server:app --host 0.0.0.0 --port 8204
TEST_DATABASE_URL=postgresql://.../scratch pytest OfferManagement/tests -q
```

## Known issues

Fixed: the cache stores only customer-independent pricing; offer ids are per customer; every call persists its own quote, publishes `offer_context` and enqueues its own confirmation.


Fixed: `generate_offer_quote` returns `bant_score` and it is persisted to `quotes.bant_score`; the prompt only names registered tools (quotes are saved automatically by `generate_offer_quote`; lookup via `get_existing_quotes` / `get_quote_details`), enforced by `test_prompt_references_only_registered_tools`.
