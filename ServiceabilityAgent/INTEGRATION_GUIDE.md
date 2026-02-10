# 🔗 Serviceability Agent - Integration Guide

## Overview

This guide explains how to integrate the Serviceability Agent into the Super Agent orchestration system.

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Super Agent                            │
│              (Central Orchestrator)                      │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┼───────────┬──────────────┐
        │           │           │              │
        ▼           ▼           ▼              ▼
   Greeting     Product    Serviceability    FAQ
    Agent        Agent       Agent           Agent
                               │
                               ▼
                         GIS/Coverage
                            API
```

---

## Step-by-Step Integration

### Step 1: Verify Serviceability Agent Works Standalone

```bash
cd ServiceabilityAgent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with GOOGLE_API_KEY
python main.py
```

Test it:
```bash
curl http://localhost:8002/health
```

### Step 2: Import into Super Agent

Edit `SuperAgent/server/agent/agent.py`:

```python
# Add import at top
from serviceability_agent import get_agent as get_serviceability_agent

# In the _build_sub_agents() function
def _build_sub_agents() -> list[Agent]:
    """Return the list of active sub-agents based on config."""
    agents: list[Agent] = []
    if settings.agent.enable_sub_agents:
        agents.extend([
            greeting_agent,
            product_agent,
            faq_agent,
            get_serviceability_agent(),  # ADD THIS LINE
        ])
    return agents
```

### Step 3: Update Super Agent Routing

Edit `SuperAgent/server/agent/prompts.py`:

```python
ORCHESTRATOR_INSTRUCTION = f"""{settings.agent.system_message}

You are the central orchestrator for a B2B sales system. Your job is to route requests to specialist sub-agents or use tools.

**IMPORTANT**: Always delegate to sub-agents or use tools. Do not respond directly.

**Routing Rules:**
- Greetings, small-talk → Transfer to greeting_agent
- Address validation, coverage checks → Transfer to serviceability_agent  # ADD THIS
- Product questions (AFTER serviceability confirmed) → Transfer to product_agent
- FAQ, billing, policies, support → Transfer to faq_agent
- Service availability checks → Transfer to serviceability_agent  # ADD THIS
- Customer lookups → Use lookup_customer tool

**CRITICAL WORKFLOW FOR ADDRESS QUERIES:**
1. First route to serviceability_agent to check coverage
2. Only if serviceable, route to product_agent for recommendations
3. Never recommend products without checking serviceability first

The sub-agents will provide the actual responses to users. Your role is routing only.
"""
```

### Step 4: Install Serviceability Agent Dependencies in Super Agent

From SuperAgent directory:
```bash
cd SuperAgent/server
pip install -r ../../ServiceabilityAgent/requirements.txt
```

Or add to SuperAgent's requirements.txt:
```txt
# Add these if not present
google-adk>=1.20.0
pydantic>=2.5.0
```

### Step 5: Configure Environment Variables

In `SuperAgent/server/.env`, add:
```bash
# Serviceability Agent Config
USE_MOCK_DATA=true
CACHE_TTL_HOURS=24
```

### Step 6: Test Integration

Start Super Agent:
```bash
cd SuperAgent/server
python main.py
```

Test the integration:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_session",
    "message": "I need internet at 123 Market Street, Philadelphia, PA 19107"
  }'
```

Expected flow:
1. Super Agent receives message
2. Routes to Serviceability Agent
3. Serviceability Agent validates address
4. Returns available products
5. Super Agent can then route to Product Agent for details

---

## Alternative: Microservices Architecture

If you want to run Serviceability Agent as a separate service:

### Option A: Run Both Servers

Terminal 1 (Serviceability Agent):
```bash
cd ServiceabilityAgent
python main.py  # Runs on port 8002
```

Terminal 2 (Super Agent):
```bash
cd SuperAgent/server
python main.py  # Runs on port 8000
```

### Option B: HTTP Tool Integration

Instead of importing as sub-agent, call via HTTP:

In `SuperAgent/server/agent/tools/`:

```python
# Create serviceability_tool.py
import requests

def check_serviceability_remote(address: str) -> dict:
    """Call remote Serviceability Agent via HTTP"""
    response = requests.post(
        "http://localhost:8002/api/check",
        json={
            "user_id": "super_agent",
            "session_id": "shared_session",
            "message": f"Check serviceability for {address}"
        }
    )
    return response.json()
```

---

## Testing End-to-End Scenarios

### Scenario 1: Address Lookup - New Prospect

**User Message**: "I need internet for my office at 123 Market Street, Philadelphia, PA 19107"

**Expected Flow**:
1. Super Agent → Prospect Agent (extracts address)
2. Super Agent → Serviceability Agent (checks coverage)
3. Serviceability Agent → Returns: serviceable=true, products=[Fiber 1G, 5G, 10G]
4. Super Agent → Product Agent (recommends specific tier)
5. Super Agent → Synthesizes response to user

**Test Command**:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "session_id": "test1",
    "message": "I need internet for my office at 123 Market Street, Philadelphia, PA 19107"
  }'
```

### Scenario 2: Non-Serviceable Address

**User Message**: "Can you service 789 Remote Road, Nowhere, AK 99999?"

**Expected Response**: Serviceability Agent returns not serviceable, offers alternatives

---

## Configuration Options

### Development Mode (Mock Data)
```bash
USE_MOCK_DATA=true
```
- No external API calls
- Fast response times
- Predictable test data

### Production Mode (Real GIS API)
```bash
USE_MOCK_DATA=false
GIS_API_URL=https://your-gis-api.com
GIS_API_KEY=your-api-key
```
- Real coverage data
- Production-ready
- Requires API credentials

---

## Monitoring Integration

### Health Checks

```bash
# Super Agent health
curl http://localhost:8000/health

# Serviceability Agent health (if standalone)
curl http://localhost:8002/health
```

### Cache Statistics

```bash
# Check cache performance
curl http://localhost:8002/cache/stats
```

### Logging

Both agents use structured logging. Grep for serviceability events:

```bash
# View serviceability-related logs
tail -f logs/super_agent.log | grep -i serviceability
```

---

## Troubleshooting

### Issue: Sub-agent not found

**Symptoms**: Super Agent can't find serviceability_agent module

**Solution**:
```bash
# Make sure ServiceabilityAgent is in Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/ConversationalSalesAgent"
```

### Issue: Import errors

**Symptoms**: `ModuleNotFoundError: No module named 'serviceability_agent'`

**Solution**:
```bash
cd ConversationalSalesAgent
pip install -e ServiceabilityAgent/
```

### Issue: Routing not working

**Symptoms**: Super Agent doesn't route to Serviceability Agent

**Solution**: Check orchestrator prompts contain routing rules for address/serviceability queries

### Issue: Different responses in integration vs standalone

**Symptoms**: Agent behaves differently when integrated

**Solution**: Ensure environment variables are consistent between standalone and integrated modes

---

## Performance Considerations

### Caching

- Cache TTL: 24 hours default
- Shared cache between calls
- Thread-safe implementation
- Stats available via `/cache/stats`

### Response Times

| Mode | Avg Response Time |
|------|-------------------|
| Cached | <100ms |
| Uncached (mock) | 100-200ms |
| Uncached (real API) | 300-600ms |

### Optimization Tips

1. **Enable caching**: Reduces repeated API calls
2. **Use mock data in dev**: Faster development cycle
3. **Batch address checks**: If checking multiple addresses
4. **Monitor cache hit rate**: Target >60%

---

## Security Considerations

### API Keys

- Store in `.env` files
- Never commit to git
- Use different keys for dev/prod

### Rate Limiting

If calling real GIS API:
```python
# In gis_tools.py, add rate limiting
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=100, period=60)  # 100 calls per minute
def _call_real_gis_api(address):
    ...
```

### Data Privacy

- Addresses are business locations (not PII)
- No customer data logged
- Review logging settings for production

---

## Next Steps After Integration

1. ✅ Test all 6 scenarios from Scenarios.md
2. ✅ Monitor cache hit rates
3. ✅ Measure end-to-end latency
4. ✅ Load test with concurrent requests
5. ✅ Replace mock GIS with production API
6. ✅ Set up monitoring/alerting
7. ✅ Deploy to staging environment

---

## Support

For integration issues:
1. Check logs in both agents
2. Verify environment variables
3. Test serviceability agent standalone first
4. Review Super Agent routing logic
5. Check [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)

---

**Integration complete! The Serviceability Agent is ready to be part of your B2B sales orchestration system.** 🚀
