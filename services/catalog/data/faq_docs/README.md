# FAQ corpus (Connectivity Max)

Policy and support answers for the FAQ agent. Indexed into the catalog service's
`faq_knowledge` Chroma collection (`catalog_service/rag.py`, `FAQ_CORPUS`) and
searched with the `search_faq` MCP tool / `GET /api/v1/faq/search?q=`.

- One topic per file; `##` / `###` headings become chunks (keep each answer under one heading).
- These files are the only facts the FAQ agent may state. Keep them consistent with
  pricing (`OfferManagement`), scheduling (`ServiceFulfillmentAgent`), payment
  (`PaymentAgent`), expiry rules (`sales_common.db`) and the product docs.
- After editing, restart the catalog service (the index rebuilds when the collection is
  empty) or run `python services/catalog/scripts/ingest_knowledge.py`.
