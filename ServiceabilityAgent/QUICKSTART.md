# Serviceability Agent - Quick Start

> The legacy standalone FastAPI server (`main.py`, `/api/check`) and in-process
> tools were removed in the ADK 2.x rewrite. The agent is now an A2A service that
> calls the serviceability service over MCP.

1. Apply the database schema and seed (once):
   ```bash
   DATABASE_URL=postgresql://... python -m sales_common.migrate --seed
   ```
2. Start the serviceability service (REST + MCP):
   ```bash
   pip install -e libs/sales_common -e services/serviceability
   DATABASE_URL=postgresql://... uvicorn serviceability_service.app:app --port 8102
   curl -s -X POST localhost:8102/api/v1/serviceability/check -H 'Content-Type: application/json' \
     -d '{"street":"123 Main St","city":"Philadelphia","state":"PA","zip_code":"19103"}'
   ```
3. Start the agent:
   ```bash
   pip install -e ServiceabilityAgent
   export GEMINI_MODEL=gemini-3-flash-preview GOOGLE_API_KEY=... DATABASE_URL=postgresql://... \
          PUBLIC_URL=http://localhost:8002 SERVICEABILITY_MCP_URL=http://localhost:8102/mcp/
   cd ServiceabilityAgent && uvicorn serviceability_agent.server:app --port 8002
   curl -s localhost:8002/.well-known/agent-card.json
   ```

Test addresses (seeded coverage): `19107` Philadelphia (FTTP, 10 Gbps), `19103`
Philadelphia (FTTP, 5 Gbps), `18000` rural PA (HFC, 500 Mbps), `99501` Anchorage
(not serviceable), any ZIP not in `coverage_zones` (not serviceable).

See [README.md](README.md) and [AGENTS.md](AGENTS.md).
