# Tasks: Remove SQLite references

## 1. Code and data files

- [x] 1.1 Delete `scripts/export_sqlite_seed.py` and `PaymentAgent/PAYMENT_SECURITY_ENHANCEMENTS.md`; reword the DiscoveryAgent docstring and the comment lines in `db/migrations/001_sales_schema.sql` and `db/seed/001_sales_data.sql`; update the seed hash in `evals/golden/MANIFEST.json`. Verify: `git diff` shows comment-only changes in the SQL files; `pytest evals -q` and `pytest DiscoveryAgent/tests -q` pass.

## 2. Docs

- [x] 2.1 Rewrite the mentions in Scenarios.md, AGENTS.md, the CustomerCommunication/Offer/Order agent docs, db/README.md, GCP_DEPLOY.md and `docs/` (brief + diagram generator). Verify: `git grep -nIi sqlite -- . ':!openspec/changes/archive' ':!.claude'` returns nothing except this change's own files.

## 3. Close

- [x] 3.1 `openspec validate remove-sqlite-references`; `pytest tests/test_baseline_doc.py -q`; commit, archive, push.
