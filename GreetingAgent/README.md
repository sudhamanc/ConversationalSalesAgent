# GreetingAgent

`greeting_agent` as a standalone A2A service (ADK 2.10, PostgreSQL-backed sessions and tasks). handles greetings and introductions (Connectivity Max phone-script greeting).
No tools. The orchestrator (SuperAgent gateway) routes user turns here; this agent cannot transfer.

## Run locally

```bash
uv pip install -e libs/sales_common -e GreetingAgent
GEMINI_MODEL=gemini-3-flash-preview GOOGLE_API_KEY=... \
DATABASE_URL=postgresql://csa:<password>@127.0.0.1:5432/csa \
PUBLIC_URL=http://127.0.0.1:8209 \
uvicorn greeting_agent.server:app --port 8209
```

- Agent card: `GET /.well-known/agent-card.json`
- Health: `GET /healthz`

Environment variables: see the README "Agent Service Guide" (environment variables).

## Docker

```bash
docker build -f GreetingAgent/Dockerfile -t greeting-agent .   # build context = repo root
```

## Tests

```bash
TEST_DATABASE_URL=postgresql://... pytest GreetingAgent/tests -q
```
