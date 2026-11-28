# Proposal: Returning-Customer Resume

## Why

In session `nU901eqzQxrR7w03EBQEh_wi`, SuperCoffeeInc (registered earlier the same day) came back:
- Discovery found the company and asked "Are you calling about service for this location?". In the same turn, the gateway's automatic discovery → serviceability handoff re-ran the coverage check and dumped the infrastructure details before the customer could answer.
- The customer then asked for their earlier quote, and none existed. The earlier quote `OFF-8B2CCF2920` had been shown to the customer, but saving it failed during the database connection outage, and that failure was "non-fatal".
- The offer agent invented a reason ("quotes typically expire after 30 days").

The root causes:
- `check_customer_state` results never reach the session, so the gateway and other agents can't resume anything.
- Serviceability results live only in session state, so every new session re-checks.
- The handoff rule fires before a returning customer is acknowledged.

The same review found two more problems:
- **Suggestion chip:** the address reply template matched "…at your location", which was not a request for an address.
- **Langfuse:** agent services' spans mostly stopped reaching it after the 11-16 redeploy. Spans are flushed only when the HTTP response's final chunk is sent. Spans that end later, or exports cut off when Cloud Run throttles CPU, are lost, and failed exports are never logged.

## What Changes

- **Returning-customer context (new journey key `returning_customer_context`):**
  - When discovery identifies a CRM customer (`get_company_profile`, `check_customer_state`), it publishes a deterministic summary:
    - `status`: `active_service` | `in_progress` | `known`
    - the active quote, pending orders, fulfillments and active services
    - the last stored serviceability check
  - The most recent active quote is restored as `offer_context`.
  - A stored serviceability result for the account address, at most `SERVICEABILITY_REUSE_DAYS` (default 30) old, is restored as `serviceability_context` with `reused: true`.
- **Stored serviceability checks:**
  - migration `006_serviceability_checks.sql`
  - `serviceability_agent` records each `check_service_availability` result, keyed by customer and address
  - `sales_common.repositories.customer_state` reads the latest one
- **Gateway handoff:** the discovery → serviceability handoff is skipped in the turn a returning CRM customer is first identified (gateway key `returning_acknowledged_customer`), so discovery can acknowledge them and ask first. It applies normally on later turns.
- **Discovery prompt: acknowledge returning customers by status:**
  - **active service:** "Welcome back… your [service] is active… what else can we help with?"
  - **in progress:** present the saved quote, order or installation and offer to continue
  - **known:** "I found you in our system at [address]…"
  - Mention reused serviceability instead of re-checking.
- **Offer agent:**
  - `generate_offer_quote` returns `success: false, error: "quote_not_saved"` and does not publish `offer_context` when persistence fails
  - the prompt forbids presenting an unsaved quote and inventing reasons when no quote is found
  - it presents a restored `offer_context` quote
- **Suggestions:**
  - the address reply template matches only explicit address or ZIP requests
  - new reply template for "this location?" confirmations
  - new stage `returning_active` with chips for existing-service customers
- **Telemetry:**
  - `TelemetryFlushPlugin` flushes spans after each agent run, while the A2A stream is still open
  - failed exports and timed-out flushes are logged
  - the default `TELEMETRY_FLUSH_TIMEOUT_MS` rises from 2000 to 5000

## Capabilities

### Modified Capabilities

- `agent-services`: returning-customer acknowledgement and resume; unsaved quotes are not presented.
- `conversation-orchestration`: discovery → serviceability handoff for returning customers; suggestion reply templates and the `returning_active` stage.
- `sales-data-store`: the `serviceability_checks` table.
- `agent-observability`: span delivery after each agent run; logged export failures.

## Non-goals

- No resume of payment or installation steps beyond describing them: pending orders are acknowledged, and the customer chooses the next step.
- No change to quote expiry rules.
- No billed golden eval runs (by user decision).

## Impact

- **BASELINE.md sections:**
  - §4 Journey context: new key `returning_customer_context`, gateway-only `returning_acknowledged_customer`
  - §5 Gateway handoff rule
  - §6 Data: migration 006, env `SERVICEABILITY_REUSE_DAYS`
  - §10 Tracing: flush plugin, timeout default
- **Agents:** discovery (tools, prompt), serviceability (callback), offer (tool, prompt).
- **APIs/MCP:** none.
- **Data:** new table `serviceability_checks`, owned by `serviceability_agent`.
- **Scripts:** none.
- **Docs:** BASELINE, `db/README.md`, `.env.example`, `DiscoveryAgent/AGENTS.md`.
