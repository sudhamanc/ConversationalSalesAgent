# FAQAgent

`faq_agent` as a standalone A2A service (ADK 2.10, PostgreSQL-backed sessions and tasks). answers common questions about products, contracts, SLAs, installation, support and policies as a phone script.
No tools. The orchestrator (SuperAgent gateway) routes user turns here; this agent cannot transfer.

## Run locally

```bash
uv pip install -e libs/sales_common -e FAQAgent
GEMINI_MODEL=gemini-3-flash-preview GOOGLE_API_KEY=... \
DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa \
PUBLIC_URL=http://127.0.0.1:8210 \
uvicorn faq_agent.server:app --port 8210
```

- Agent card: `GET /.well-known/agent-card.json`
- Health: `GET /healthz`

Environment variables: see `docs/agent-service-guide.md` section 10.

## Docker

```bash
docker build -f FAQAgent/Dockerfile -t faq-agent .   # build context = repo root
```

## Tests

```bash
TEST_DATABASE_URL=postgresql://... pytest FAQAgent/tests -q
```
