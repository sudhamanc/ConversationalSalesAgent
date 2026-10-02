# Discovery Agent

**Type:** Domain agent (Discovery phase), served as an A2A service
**Framework:** Google ADK 2.10 + `sales_common` (see [README: Agent Service Guide](../README.md#agent-service-guide))
**Package:** `discovery_agent`
**A2A app:** `discovery_agent.server:app` (port 8201 in local compose)

---

## Purpose

The Discovery Agent is the first business-context agent in the sales journey. It:

1. Extracts company and address details from conversation (intelligent inference)
2. Looks up existing accounts, or registers new companies/locations
3. Publishes `customer_context` for downstream agents
4. Gathers BANT signals conversationally and records a scored opportunity
5. Maps contact personas (email/phone collection)
6. Checks a returning customer's pipeline (`check_customer_state`)

---

## Configuration

| Attribute | Value |
|-----------|-------|
| Agent name | `discovery_agent` (hardcoded; the gateway routes by it) |
| Model | `GEMINI_MODEL` via `sales_common.config.model_name()` (no default) |
| Generation | `generate_config(temperature=0.0)` |
| `static_instruction` | `prompts.DISCOVERY_AGENT_INSTRUCTION` (long, cacheable, not templated) |
| `instruction` | `sales_common.prompts.JOURNEY_CONTEXT_INSTRUCTION` |
| Callbacks | `before_agent_callback=[import_forwarded_context]`, `after_tool_callback=[export_context_delta]` |
| Database | PostgreSQL via `sales_common.db` (`DATABASE_URL`); schema in `db/migrations/` |

Environment variables are listed in the service guide (§10): `GEMINI_MODEL`, `GOOGLE_API_KEY`, `DATABASE_URL`, `PUBLIC_URL`, optional `SERVICE_AUTH`, `LOG_LEVEL`.

## Layout

```text
DiscoveryAgent/
├── pyproject.toml              # discovery-agent, depends on sales-common
├── Dockerfile                  # build context = repo root
├── discovery_agent/
│   ├── __init__.py             # build_agent, root_agent
│   ├── agent.py                # build_agent(model=None) -> Agent; root_agent
│   ├── prompts.py              # DISCOVERY_AGENT_INSTRUCTION, DISCOVERY_SHORT_DESCRIPTION
│   ├── server.py               # app = create_a2a_app(root_agent)
│   └── tools/
│       ├── discovery_tools.py  # the 13 ADK tools (return dicts)
│       ├── db_tools.py         # PostgreSQL queries (accounts, contacts, spend, insights, actions)
│       └── qualification_tools.py  # BANT scoring + opportunities table
├── tests/                      # pytest (TEST_DATABASE_URL + ScriptLlm)
```

## Tables (PostgreSQL, quoted column names)

`accounts` (PK `"Company Name"`, `"Street"`, `"City"`, `"State"`, `zip_code`, `"Industry"`, `"Website"`, `customer_id`), `contacts`, `spend`, `opportunities`, `insights`, `actions`. Always double-quote capitalized columns in SQL. Agents never create tables at runtime.

## Tools (13)

| Tool | Tables | Writes `customer_context` |
|------|--------|---------------------------|
| `search_companies` | `accounts` (case-insensitive substring, compound name+address) | no |
| `get_company_profile` | `accounts` LEFT JOIN `spend` | yes, when the account has a `customer_id` |
| `get_contact_personas` | `contacts` | no |
| `get_customer_intent` | `insights`, `opportunities`, `actions` | no |
| `search_by_intent_signals` | `accounts` JOIN `insights` | no |
| `get_high_priority_opportunities` | `opportunities` | no |
| `add_new_company` | `accounts` INSERT (generates `CUST-YYYYMMDD-NNN`: today's UTC date, counter = max for today's prefix + 1 from 001, widens past 999; allocated under `pg_advisory_xact_lock`) | yes, on success |
| `update_company_info` | `accounts` UPDATE | no |
| `add_new_contact` / `update_contact_info` | `contacts` (`add_new_contact` requires an existing account, matched case-insensitively; else `{success: false, error}`) | no |
| `add_or_update_insights` | `insights` (update, else insert) | no |
| `create_opportunity_from_bant` | `opportunities` INSERT with BANT scores; an existing opportunity with the same company + name (case-insensitive) is not re-inserted (`success: false, duplicate: true`) | no |
| `check_customer_state` | cross-table, via `sales_common.repositories.customer_state` | no |

`customer_context` shape: `{customer_id, company_name, address: {street, address_line2, city, state, zip_code}}`. It is written to `tool_context.state`; `export_context_delta` adds it to the tool response as `_context_update` so the gateway merges it into the journey state.

Database errors (`psycopg.Error`) are returned as `{"success": false, "error": ...}`.

NULL or blank columns are rendered with the tool's default (`N/A`, `Unknown`, ...) through the
`_val(row, column, default)` helper; `dict.get(col, default)` would return `None` for a NULL
column. `customer_context.address` uses `""` for missing parts, never `N/A`.

## Known issues

- `opportunities` and `contacts` have no unique keys in the shared schema (the seed data
  already contains duplicate opportunities, so a unique index cannot be added without
  cleaning demo data). Duplicates are prevented in code: check + insert under a per-company
  advisory lock (contacts match on name or email, case-insensitive).
- `accounts."Company Name"` is the primary key (case-sensitive); lookups for contacts and
  opportunities match it case-insensitively.

## Hand-off

The agent never transfers. After registering or confirming an address it says it will check service availability. The gateway's `HandoffPolicyNode` runs the Discovery -> Serviceability hand-off deterministically when `customer_context.address.zip_code` is present and `serviceability_context` is absent.

## Tests

```bash
TEST_DATABASE_URL=postgresql://user:pw@127.0.0.1:5432/scratch_db \
  venv/bin/python -m pytest DiscoveryAgent/tests -q
```

Tool tests migrate + seed the scratch DB (`sales_common.migrate.run(seed=True)`) and skip without `TEST_DATABASE_URL`. The agent test uses `sales_common.testing.ScriptLlm` with `Runner` + `InMemorySessionService` (no API key).
