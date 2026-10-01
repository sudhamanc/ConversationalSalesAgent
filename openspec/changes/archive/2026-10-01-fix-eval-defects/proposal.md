# Proposal: Fix Defects Found by the Golden Evals

## Why

The golden eval suite found seven defects; nine golden cases stay unreviewed until they are fixed:
- The FAQ agent has no knowledge source and invents policies (3.2, 3.3, 3.4).
- The product agent compares with competitors instead of declining (6.10).
- The order agent asks for a cancellation reason on an already-fulfilled order, and `cancel_order` would cancel any status (9.11).
- `get_payment_history` returns generated sample transactions (8.6).
- Agents do not know today's date, producing past payment plans and stale reschedule slots (8.5, 10.6).
- Discovery asks for a suite number instead of registering, so the serviceability handoff never runs (E2E-4).
- The router sends "We're <Company> at <address>" to serviceability (Scenarios 1.1).

## What Changes

- **FAQ RAG:**
  - A Connectivity Max FAQ corpus (`services/catalog/data/faq_docs/*.md`) is indexed as a second Chroma collection in the catalog service.
  - It is exposed as MCP tool `search_faq` and REST `GET /api/v1/faq/search?q=`.
  - `faq_agent` consumes it via `McpToolset` (filtered to `search_faq`), answers only from retrieved passages, and otherwise offers a specialist follow-up.
  - `faq` gains MCP dependency `CATALOG_MCP_URL=catalog` (services.conf, compose).
- **Product prompt:** an explicit competitor rule (decline, no competitor names or claims, offer own specs), with no tool calls for competitor-only questions.
- **Order:** `cancel_order` refuses fulfilled, activated, installed, completed and already-cancelled orders; the prompt calls `cancel_order` directly (reason optional, never asked first) and relays refusals.
- **Payment:** `get_payment_history` reads `payments` (joined to `orders` for customer), with date filters and limit; `setup_payment_plan` rejects past start dates.
- **Dates:**
  - Every agent's templated journey instruction carries `current_date` (set by `import_forwarded_context`).
  - Fulfillment `check_availability` rejects past start dates.
  - Payment and fulfillment prompts state that relative dates resolve from today.
- **Discovery prompt:** suite/unit is optional and never asked; register with `add_new_company` as soon as name, industry, street, city, state and ZIP are known.
- **Router prompt:** a company introduction (with or without an address) goes to discovery_agent; serviceability only for explicit availability/coverage questions or bare addresses after the customer is identified.
- **Found while running the full suite:**
  - catalog segfault from concurrent Apple-GPU (MPS) embedding → one shared CPU embedder with a lock
  - no model request timeout → `MODEL_REQUEST_TIMEOUT_MS`
  - the greeting prompt's example claimed market leadership → removed, with a rule against it
- **Goldens:** re-record and review the nine pending cases and re-run affected tiers.
- **Baseline:** remove the known-issues entries; document the FAQ RAG.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `product-catalog-service`: adds FAQ knowledge search.
- `agent-services`: adds grounded FAQ answers, competitor refusal, cancellation guard, real payment history, current-date awareness, prompt registration.
- `conversation-orchestration`: adds company-introduction routing.

BASELINE.md sections affected: 2 (faq MCP dependency), 3 (faq tool, catalog tools), 5 (router rule), 10 (known issues removed).

## Non-goals

- A separate knowledge service (the catalog service already owns RAG infrastructure).
- Editing FAQ content through an admin UI; the corpus is markdown in git.
- `mcp-remaining-domains`.

## Impact

- **Agents:** faq, product, order, payment, service_fulfillment, discovery prompts/tools; `sales_common.context` / `prompts`.
- **Services:** catalog gains a collection, an MCP tool and a REST endpoint (index rebuilt on start when the FAQ collection is empty).
- **Gateway:** router prompt only.
- **Data:** none (no schema change).
- **Scripts:** `services.conf`, `docker-compose.yml` (faq → catalog MCP URL).
- **Docs:** BASELINE.md, services/catalog/README.md, FAQAgent docs, evals goldens.
