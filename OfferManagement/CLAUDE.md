# Claude Code Instructions - Offer Management Agent

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

All Offer Management Agent documentation (price book, discount tiers, quote schema) is in AGENTS.md.

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Price book changes → [AGENTS.md - Product Price Book](AGENTS.md#product-price-book)
   - Discount changes → [AGENTS.md - Discount System](AGENTS.md#discount-system)
   - Quote schema → [AGENTS.md - Quote Output Schema](AGENTS.md#quote-output-schema)
   - Adding new discounts → [AGENTS.md - Adding New Discount Types](AGENTS.md#adding-new-discount-types)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

When working on Offer Management Agent:

1. **Read AGENTS.md** for complete documentation
2. **All pricing is deterministic** — temperature is 0.0, never hallucinate prices
3. **Price book** lives in `offer_management/tools/pricing_tools.py` (`PRODUCT_PRICE_BOOK`)
4. **Three discount layers** applied sequentially: Bundle → Term → BANT
5. **BANT score** comes from conversation context (set by DiscoveryAgent), passed to tools as `bant_score` parameter
6. **Quote JSON** must include `discount_breakdown` array for customer-visible savings
7. **Frontend** renders discounts via `QuoteCard.jsx` — update it if quote schema changes
8. **Test changes** with `pytest tests/ -v`

---

## Quick Reference

```
Tools: 2 (find_best_bundle_offer, generate_offer_quote)
Temperature: 0.0 (fully deterministic)
Invocation: When customer requests pricing, quote, or discounts
Price Book: offer_management/tools/pricing_tools.py
Discount Layers: Bundle (5-10%) → Term (0-10%) → BANT (0-8%)
```

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
**Frontend QuoteCard:** [/SuperAgent/client/src/components/QuoteCard.jsx](/SuperAgent/client/src/components/QuoteCard.jsx)
