# Integration tests (multi-process)

`test_local_stack.py` (pytest) starts PostgreSQL-backed tool services, all 10 A2A agent
services and the gateway as real processes with a scripted model
(`fake_llm/sitecustomize.py`, `GEMINI_MODEL=fake-sales`), then drives
a conversation over HTTP/SSE with assertions.

```bash
TEST_DATABASE_URL=postgresql://user:pw@127.0.0.1:5432/scratch_db venv/bin/python -m pytest tests/integration -q
``` Real A2A, real MCP, real
PostgreSQL; no Gemini calls.
