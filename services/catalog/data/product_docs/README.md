# Product Knowledge Documents

Source documents for the catalog service's knowledge search (`search_product_knowledge`,
`GET /api/v1/knowledge/search`). This README is not indexed.

- One markdown file per product family. Chunks split on `##` / `###` headings.
- Each chunk carries `doc_file`, `section`, `product_family` and `product_ids` metadata.
  File-to-product mapping: `DOC_METADATA` in `catalog_service/rag.py`; update it when adding a file.
- Structured product data (ids, speeds, features) lives in PostgreSQL (`products` table), not here.
- After editing, rebuild the index: `python services/catalog/scripts/ingest_knowledge.py`.
  The Docker image rebuilds it at build time.
- Keep content technical. No pricing: prices come only from offer management.
