# Offer Management Agent

**Type:** Deterministic Agent (Pricing & Quoting)
**Framework:** Google ADK 1.20.0
**Package:** `offer_management`
**Status:** ✅ Deployed in SuperAgent

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [Root CLAUDE.md](/CLAUDE.md)
   - [Root AGENTS.md](/AGENTS.md)
   - This file (OfferManagement/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Agent development → [Root AGENTS.md - Golden Rule](/AGENTS.md#the-golden-rule)
   - Pricing changes → This file (see Price Book & Discount Tiers)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Purpose

The Offer Management Agent is the **single source of truth for pricing**. It:

1. **Calculates** deterministic price quotes from the product price book
2. **Applies** three layers of discounts: Bundle → Term → BANT
3. **Generates** structured JSON quotes with itemized discount breakdowns
4. **Produces** offer IDs for downstream order placement

All pricing is **deterministic** (temperature=0.0) — no LLM hallucination on prices or discounts.

---

## Architecture

### Agent Classification

| Attribute | Value |
|-----------|-------|
| **Type** | Deterministic (zero-hallucination) |
| **Phase** | Offer/Quote (Phase 4 of sales cycle) |
| **Source of Truth** | `PRODUCT_PRICE_BOOK` in pricing_tools.py |
| **Temperature** | 0.0 (fully deterministic) |
| **Invocation** | When customer requests a price quote or discount info |

### Component Structure

```
OfferManagement/
├── offer_management/
│   ├── __init__.py              # Exports offer_management_agent
│   ├── agent.py                 # Agent instance + tool registration
│   ├── prompts.py               # Agent instruction template
│   ├── tools/
│   │   ├── __init__.py          # Exports pricing tools
│   │   └── pricing_tools.py     # Price book, discounts, quote generator
│   └── utils/
│       ├── __init__.py
│       ├── cache.py             # Offer caching
│       └── logger.py            # Structured logging
└── tests/
    └── (test files)
```

---

## Tools

The Offer Management Agent has **2 tools**, both operating on deterministic data:

### 1. `find_best_bundle_offer(items, term_months, bant_score)`

Evaluates all applicable discount rates for a set of products.

**Parameters:**
- `items`: List of `{"product_id": str, "quantity": int}`
- `term_months`: Contract duration — 12, 24, or 36 (default: 12)
- `bant_score`: Prospect's BANT qualification score 0–100 (default: 0)

**Returns:**
```json
{
  "found": true,
  "offer_id": "OFF-4D45CE5C8A",
  "term_months": 36,
  "bundle_discount_rate": 0.05,
  "term_discount_rate": 0.10,
  "bant_discount_rate": 0.08,
  "bant_discount_label": "Preferred Business Discount (Tier A)"
}
```

### 2. `generate_offer_quote(items, term_months, bant_score)`

Generates a full itemized quote with price points, layered discounts, and totals.

**Parameters:** Same as `find_best_bundle_offer`

**Returns:** Complete quote JSON (see Quote Output Schema below)

---

## Product Price Book

All prices are monthly recurring charges (MRC).

| Product ID | Product Name | Unit Price | Family |
|-----------|-------------|-----------|--------|
| FIB-1G | Business Fiber 1 Gbps | $249.00 | internet |
| FIB-5G | Business Fiber 5 Gbps | $599.00 | internet |
| FIB-10G | Business Fiber 10 Gbps | $999.00 | internet |
| COAX-200M | Business Internet 200 Mbps | $79.00 | internet |
| COAX-500M | Business Internet 500 Mbps | $149.00 | internet |
| COAX-1G | Business Internet 1 Gbps | $249.00 | internet |
| VOICE-BAS | Business Voice Basic | $29.00 | voice |
| VOICE-STD | Business Voice Standard | $24.00 | voice |
| VOICE-ENT | Business Voice Enterprise | $19.00 | voice |
| VOICE-UCAAS | Unified Communications (UCaaS) | $39.00 | voice |
| SDWAN-ESS | SD-WAN Essentials | $199.00 | sdwan |
| SDWAN-PRO | SD-WAN Professional | $399.00 | sdwan |
| SDWAN-ENT | SD-WAN Enterprise | $699.00 | sdwan |
| MOB-BAS | Business Mobile Basic | $35.00 | mobile |
| MOB-UNL | Business Mobile Unlimited | $55.00 | mobile |
| MOB-PREM | Business Mobile Premium | $75.00 | mobile |

---

## Discount System

Discounts are applied in **three sequential layers**. Each layer discounts the post-previous-layer price (not the original subtotal), which avoids over-discounting.

### Layer 1: Bundle Discounts

Triggered when the customer orders products from multiple product families:

| Bundle | Families Required | Discount Rate |
|--------|-------------------|---------------|
| Internet + Voice | internet, voice | **5%** |
| Internet + SD-WAN | internet, sdwan | **7%** |
| Triple Play | internet, voice, sdwan | **10%** |

### Layer 2: Term Commitment Discounts

Based on contract length:

| Term | Discount Rate |
|------|---------------|
| 12 months | 0% (base) |
| 24 months | **5%** |
| 36 months | **10%** |

### Layer 3: BANT Qualification Discounts

Based on the prospect's BANT score from DiscoveryAgent. Higher-qualified prospects earn better rates as a reward for engagement quality:

| BANT Score | Tier | Discount Rate | Customer-Facing Label |
|-----------|------|---------------|----------------------|
| ≥ 66.7 | A (Hot) | **8%** | Preferred Business Discount (Tier A) |
| ≥ 33.3 | B (Warm) | **4%** | Business Advantage Discount (Tier B) |
| < 33.3 | C (Cold) | 0% | No additional discount |

**How BANT score flows into pricing:**
1. DiscoveryAgent gathers BANT signals conversationally during discovery
2. `create_opportunity_from_bant` tool calculates the score (0–100) and stores it
3. When the customer requests a quote, the OfferManagement agent reads the BANT score from conversation context
4. The score is passed to `generate_offer_quote(bant_score=...)` for deterministic discount calculation

### Discount Application Order

```
Extended Price (unit × quantity)
  └─ × (1 - bundle_rate)  → after_bundle
       └─ × (1 - term_rate)   → after_term 
            └─ × (1 - bant_rate)   → final_price
```

**Example (FIB-5G + 5× VOICE-STD, 36 months, BANT=75):**
```
Subtotal:                $719.00
  Bundle (Internet+Voice 5%):   -$35.95
  Term (36-month 10%):          -$68.31
  BANT (Tier A 8%):             -$49.18
  ─────────────────────
  Total Discount:       $153.44
  Monthly Total:        $565.56
  Yearly Total:       $6,786.72
```

---

## Quote Output Schema

The `generate_offer_quote` tool returns this JSON structure:

```json
{
  "offer_id": "OFF-4D45CE5C8A",
  "term_months": 36,
  "items": [
    {
      "product_id": "FIB-5G",
      "product_name": "Business Fiber 5 Gbps",
      "quantity": 1,
      "price_points": {
        "unit_price": 599.0,
        "extended_price": 599.0
      },
      "discount": 126.69,
      "discount_detail": {
        "bundle_discount": 29.95,
        "term_discount": 56.91,
        "bant_discount": 39.83
      },
      "final_price": 472.31
    }
  ],
  "subtotal": 719.0,
  "discount_breakdown": [
    {
      "type": "bundle",
      "label": "Multi-Product Bundle Discount (Internet + Voice)",
      "rate": 0.05,
      "rate_display": "5%",
      "amount": 35.95
    },
    {
      "type": "term",
      "label": "36-Month Commitment Discount",
      "rate": 0.10,
      "rate_display": "10%",
      "amount": 68.31
    },
    {
      "type": "bant",
      "label": "Preferred Business Discount (Tier A)",
      "rate": 0.08,
      "rate_display": "8%",
      "amount": 49.18
    }
  ],
  "total_discount": 153.44,
  "total_price": 565.56,
  "monthly_total": 565.56,
  "yearly_total": 6786.72
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `offer_id` | Deterministic hash-based ID (stable for same inputs) |
| `discount_breakdown` | Array of customer-visible discount explanations |
| `discount_detail` | Per-item breakdown (bundle, term, BANT amounts) |
| `total_discount` | Sum of all discount types |
| `monthly_total` / `yearly_total` | Final amounts after all discounts |

---

## Customer-Facing Discount Presentation

The agent is instructed to present discounts transparently so the customer feels rewarded:

```
Here's your quote (OFF-4D45CE5C8A):

  Business Fiber 5 Gbps (×1): $472.31/mo
  Business Voice Standard (×5): $93.25/mo

  **Your Savings:**
  ✅ Multi-Product Bundle Discount (Internet + Voice): 5% → saves $35.95/mo
  ✅ 36-Month Commitment Discount: 10% → saves $68.31/mo
  ✅ Preferred Business Discount (Tier A): 8% → saves $49.18/mo
  ─────────────────────
  Total Savings: $153.44/mo

  Monthly Total: $565.56
  Yearly Total: $6,786.72
```

The frontend `QuoteCard` component renders this discount breakdown in a green "Your Savings" card for visual prominence.

---

## Integration with SuperAgent

### Routing Rule

**Priority:** #4 (Offer Management, Pricing, and Discounts)

**Trigger Examples:**
- "Give me a quote for these products"
- "Any discount if I take internet plus voice for 36 months?"
- "What's the total cost?"
- "Yes, proceed with pricing"

**Invocation:** After serviceability is confirmed and products are selected

### Agent Workflow

```
Step 1: Parse requested products, quantities, and term from user
Step 2: Check conversation context for BANT score
Step 3: Call find_best_bundle_offer(items, term_months, bant_score)
Step 4: Call generate_offer_quote(items, term_months, bant_score)
Step 5: Return JSON output with discount breakdown highlighted
```

### Data Flow

```
DiscoveryAgent           → BANT score in conversation context
ProductAgent             → Product IDs selected by customer
OfferManagementAgent     → Deterministic quote with discount breakdown
OrderAgent               → Accepts offer_id for order placement
```

---

## Caching

Offer results are cached by a composite key of `items + term_months + bant_score`. The same inputs always produce the same offer_id and pricing. Cache is in-memory and resets on server restart.

---

## Development

### Adding New Discount Types

1. Define the discount table in `pricing_tools.py` (like `BANT_DISCOUNTS`)
2. Create a `_get_*_discount_rate()` helper function
3. Wire into `find_best_bundle_offer()` and `generate_offer_quote()`
4. Add to the `discount_breakdown` array with `type`, `label`, `rate`, `amount`
5. Update the `QuoteCard.jsx` component if new display logic is needed
6. Update agent prompts in `prompts.py` to instruct the agent about the new discount
7. Update this documentation

### Adding New Products

1. Add entry to `PRODUCT_PRICE_BOOK` in `pricing_tools.py`
2. Set `product_id`, `product_name`, `unit_price`, and `family`
3. If new family, add bundle rules to `BUNDLE_DISCOUNTS` and `_get_bundle_discount_rate()`
4. Update ProductAgent catalog to match

### Running Tests

```bash
cd OfferManagement
pytest tests/ -v
```

---

## Common Issues

### Issue: BANT discount not applied

**Cause:** Agent didn't pass `bant_score` to the tools
**Fix:** Check that the OfferManagement agent instruction includes guidance to read BANT score from conversation context. Both tools default to `bant_score=0` if not provided.

### Issue: Discount amounts seem wrong

**Cause:** Discounts are layered sequentially, not additive
**Fix:** This is by design. Bundle discounts apply first on the full price, term discounts on the post-bundle price, BANT on the post-term price. This prevents over-discounting.

### Issue: Offer ID changes for same products

**Cause:** BANT score or term changed
**Fix:** Offer IDs are deterministic SHA-1 hashes of the full payload (items + term + discount rates). Any input change produces a new ID.

---

## Related Documentation

- **Root Architecture:** [/AGENTS.md](/AGENTS.md)
- **SuperAgent Integration:** [/SuperAgent/super_agent/sub_agents/AGENTS.md](/SuperAgent/super_agent/sub_agents/AGENTS.md)
- **BANT Scoring Source:** [/DiscoveryAgent/AGENTS.md](/DiscoveryAgent/AGENTS.md)
- **Product Catalog:** [/ProductAgent/AGENTS.md](/ProductAgent/AGENTS.md)
- **Frontend QuoteCard:** `SuperAgent/client/src/components/QuoteCard.jsx`
- **Test Scenarios:** [/Scenarios.md](/Scenarios.md)
