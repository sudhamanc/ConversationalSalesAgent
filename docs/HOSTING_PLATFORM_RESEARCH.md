# Hosting Platform Research for Testing

## Application Profile

| Aspect | Details |
|--------|---------|
| Backend | Python 3.12+ / FastAPI (WebSocket via Socket.io) |
| Frontend | React 19 / Tailwind CSS |
| Agent Framework | Google ADK ~1.20.0 with Gemini 2.5-flash |
| Databases | PostgreSQL (prod), SQLite (dev), ChromaDB (RAG) |
| Cloud Dependencies | GCP Vertex AI, Secret Manager, Cloud Logging, Cloud Trace |
| Observability | OpenTelemetry with GCP exporters |

## Hosting Options

### 1. Google Cloud Run (Recommended)

**Why it fits:**
- Native integration with all existing GCP dependencies (Vertex AI, Secret Manager, Cloud Logging, Cloud Trace).
- WebSocket support for the Socket.io real-time chat interface.
- Scales to zero when idle — minimal cost during testing.
- IAM and service account integration works without extra credential management.
- Smooth promotion path from testing to Vertex AI Reasoning Engine production deployment.

**Cost:** Free tier includes 2M requests/month, 360K vCPU-seconds, 180K GiB-seconds.

**Setup overview:**
1. Containerize the FastAPI backend (Dockerfile at project root).
2. Deploy to Cloud Run with environment variables from `.env.dev`.
3. Serve React frontend via Cloud Storage + CDN, or bundle into the same container.
4. Grant the Cloud Run service account access to Vertex AI, Secret Manager, etc.

### 2. Vertex AI Reasoning Engines (Already Configured)

The `bootstrap_agent/deploy/` directory already targets this platform. Suitable for testing the agent orchestration layer in a production-like environment.

### 3. Railway / Render

**Pros:**
- Fast setup for demos and staging environments.
- Container-based, supports FastAPI + React easily.

**Cons:**
- Requires exporting GCP service account credentials as environment variables.
- Cross-cloud latency for Vertex AI and Gemini API calls.
- No native integration with GCP monitoring/logging stack.

**Cost:** Railway ~$5/month hobby plan; Render free tier 750 hours/month.

### 4. Fly.io

**Pros:**
- Strong WebSocket support, important for the real-time chat interface.
- Global edge deployment for low-latency demos.
- Free tier: 3 shared VMs, 3GB storage.

**Cons:**
- Same GCP credential management overhead as Railway/Render.

### 5. VPS (DigitalOcean / Hetzner / Linode)

**Pros:**
- Full control, run all services (PostgreSQL, ChromaDB, FastAPI, React) on one machine.
- Good for integration testing of the full stack.

**Cons:**
- Manual infrastructure management (no auto-scaling, no managed services).
- Must handle TLS, reverse proxy, process management.

**Cost:** $5-10/month for a basic VM.

## Decision Matrix

| Criteria | Cloud Run | Vertex AI RE | Railway/Render | Fly.io | VPS |
|----------|-----------|-------------|----------------|--------|-----|
| GCP integration | Native | Native | Manual | Manual | Manual |
| WebSocket support | Yes | N/A | Yes | Yes | Yes |
| Scale to zero | Yes | No | Varies | Yes | No |
| Setup complexity | Low | Low (existing) | Low | Medium | High |
| Cost (testing) | Free tier | Pay-per-use | Free-$5/mo | Free tier | $5-10/mo |
| Demo suitability | High | Medium | High | High | Medium |

## Recommendation

**Google Cloud Run** is the best fit for testing because:
1. Zero friction with existing GCP service dependencies.
2. Free tier covers typical testing workloads.
3. WebSocket support for the real-time chat interface.
4. OpenTelemetry, Cloud Logging, and Secret Manager work out of the box.
5. Natural stepping stone to Vertex AI production deployment.

For quick external demos where simplicity matters more than full observability, Railway or Render are viable alternatives.
