# Proposal: Remove SQLite references

## Why

The system has used PostgreSQL only since the A2A rewrite, and the GCS bucket that held the old database file was deleted on 2026-11-15. Several documents, comments, a spec, an unused migration script and an unlinked historical write-up still describe SQLite. Some present it as the current design (Scenarios.md CC.3, the "latest" architecture diagram generator). That misleads readers and assistants.

## What Changes

- Delete `scripts/export_sqlite_seed.py`, the one-time exporter whose output is already committed as `db/seed/001_sales_data.sql`.
- Delete `PaymentAgent/PAYMENT_SECURITY_ENHANCEMENTS.md`, an unlinked write-up of the old design; current behavior is in `PaymentAgent/AGENTS.md`.
- Rewrite every remaining mention so it describes the current PostgreSQL system. This covers Scenarios.md, AGENTS.md, agent READMEs and AGENTS.md files, db/README.md, GCP_DEPLOY.md, a DiscoveryAgent docstring, the architecture brief and diagram generator in `docs/`, and comment lines in `db/migrations/001_sales_schema.sql` and `db/seed/001_sales_data.sql` (comments only, no SQL change).
- Update the seed file's hash in `evals/golden/MANIFEST.json`. Only comment lines change; no data row does.
- `sales-data-store` spec: the two requirements no longer name the old database technology or file.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sales-data-store`: wording of "PostgreSQL system of record" and "Seed data" (no behavior change).

## BASELINE.md sections affected

None.

## Non-goals

- Editing archived OpenSpec changes (`openspec/changes/archive/`). They are the historical record.
- Editing the generic OpenSpec tooling examples under `.claude/`.
- Any schema or data change.

## Impact

- **Agents, APIs, MCP servers:** none. **Data:** none (comment-only edits in one migration and one seed file). **Scripts:** one unused script removed. **Docs:** updated as listed.
