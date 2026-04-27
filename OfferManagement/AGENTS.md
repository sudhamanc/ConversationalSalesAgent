# Offer Management Agent

**Type:** Deterministic Agent (Pricing & Quoting)
**Framework:** Google ADK 1.20.0+
**Package:** `offer_management`
**Status:** ✅ Deployed in SuperAgent

---

## Purpose

The Offer Management Agent performs **deterministic pricing calculation, discount application, and quote generation**. It computes exact prices from a hardcoded price book — no LLM involvement in pricing math.

---

## Architecture

### Agent Configuration

| Attribute | Value |
|-----------|-------|
| **Agent Name** | `offer_management_agent` (hardcoded) |
| **Model** | `os.getenv("GEMINI_MODEL")` — no default |
| **Temperature** | 0.0 (deterministic) |
| **Max Tokens** | 2048 |
| **Database** | Unified `sales_agent.db` → `quotes` table |
| **Fallback DB** | `OfferManagement/data/quotes.db` |

### Component Structure

```
OfferManagement/
├── offer_management/
│   ├── __init__.py
│   ├── agent.py                    # Agent definition
│   ├── prompts.py                  # System instructions
│   ├── tools/
│   │   └── pricing_tools.py        # Pricing engine + quote generation
│   └── utils/
│       ├── cache.py                # Quote caching
│       └── quote_db.py             # SQLite persistence for quotes
└── tests/
```

### Database Tables (1 table — Offer Domain)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `quotes` | Persisted price quotes | offer_id (PK), customer_id, items_json, term_months, bant_score, subtotal, total_discount, total_price, status, expires_at |

---

## Tools (4 Functions)

| Tool | Signature | Tables | Purpose |
|------|-----------|--------|---------|
| `find_best_bundle_offer` | `(items, term_months, bant_score) → Dict` | None (in-memory) | Calculate optimal pricing without persisting |
| `generate_offer_quote` | `(items, term_months, bant_score, customer_id, company_name, customer_email) → Dict` | `quotes` INSERT | Generate and persist a formal quote |
| `get_existing_quotes` | `(company_name, customer_id) → Dict` | `quotes` SELECT | Retrieve active quotes for a customer |
| `get_quote_details` | `(offer_id) → Dict` | `quotes` SELECT | Get full quote by ID |

### Pricing Engine

**Price Book:** 16 SKUs across Internet, SD-WAN, Security, TV, Phone categories.

**Discount Layers (applied sequentially):**
1. **Term Discounts:** 12mo (0%), 24mo (5%), 36mo (10%)
2. **Bundle Discounts:** 2 items (5%), 3 items (8%), 4+ items (12%)
3. **BANT Discounts:** Score ≥70 (3%), ≥50 (2%), <50 (0%)

**Quote Lifecycle:**
- Status: `active` → `ordered` (when OrderAgent creates order) → `expired` (TTL: 30 days)
- Each quote gets a unique `offer_id` (hash-based)

### Cross-Agent Integration
- Auto-sends `QUOTE_CONFIRMATION` notification via `sys.modules` to CustomerCommunicationAgent
- OrderAgent calls `mark_quote_ordered(offer_id)` to transition quote status

---

## Conversation Behavior

### When Invoked
SuperAgent routes to OfferManagementAgent for: "Give me pricing", "How much for Fiber 5G?", "Any discounts?", "Generate a quote"

### Response Pattern
Returns structured pricing:
> "Quote #ABC123: Fiber Internet 5G ($X/mo) + SD-WAN ($Y/mo) — Bundle discount 8%, Term discount 5% — **Total: $Z/mo**"

---

## Integration with SuperAgent

Loaded via **importlib isolation** in `SuperAgent/super_agent/sub_agents/offer_management/agent.py`. Agent name `offer_management_agent` is hardcoded.
