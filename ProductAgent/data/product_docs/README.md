# Product Data Notes

This directory may contain legacy sample product documentation files from earlier experiments.

## Current Source of Truth

ProductAgent now uses deterministic in-repo catalog tools, not vector search.

- Catalog data is maintained in `ProductAgent/product_agent/tools/product_tools.py`
- Comparison logic is maintained in `ProductAgent/product_agent/tools/comparison_tools.py`
- Pricing, discounts, and quote totals are handled by `OfferManagementAgent`

## How to Update Product Information

1. Update product entries in `product_tools.py` (ids, names, speeds, features, availability)
2. Keep ProductAgent technical-only (no pricing outputs)
3. Run ProductAgent tests:

```bash
GEMINI_MODEL=gemini-3-flash-preview /Users/sudhamanc/Desktop/Github/ConversationalSalesAgent/.venv/bin/python -m pytest ProductAgent/tests/test_tools.py ProductAgent/tests/test_agent.py -q
```

## Notes

- If this folder is not used by runtime code, it can be kept for archival docs or removed later.
- Keep this folder aligned with current catalog-first ProductAgent behavior.
