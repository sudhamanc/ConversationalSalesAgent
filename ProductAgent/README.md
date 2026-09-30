# Product Agent

ADK 2.x agent served over A2A that answers product questions: specs, comparisons, alternatives and documentation. It never gives pricing.
Its tools come from the catalog service (`services/catalog`) over MCP.

```bash
pip install -e libs/sales_common -e ProductAgent          # from the repo root
export GEMINI_MODEL=gemini-3-flash-preview GOOGLE_API_KEY=... \
       DATABASE_URL=postgresql://... PUBLIC_URL=http://localhost:8003 \
       CATALOG_MCP_URL=http://localhost:8101/mcp/
uvicorn product_agent.server:app --host 0.0.0.0 --port 8003
```

- Docker: `docker build -f ProductAgent/Dockerfile .` (build context is the repo root).
- Details: [AGENTS.md](AGENTS.md).
- Catalog API and tools: [services/catalog/README.md](../services/catalog/README.md).
