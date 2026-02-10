# Serviceability Agent - Quick Start Guide

## Setup (5 minutes)

1. **Install dependencies**:
   ```bash
   cd ServiceabilityAgent
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

3. **Run the server**:
   ```bash
   python main.py
   ```

4. **Test it**:
   ```bash
   curl http://localhost:8002/health
   ```

## Example Requests

### Check Serviceable Address
```bash
curl -X POST http://localhost:8002/api/check \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "session_id": "test123",
    "message": "Check 123 Market Street, Philadelphia, PA 19107"
  }'
```

### Check Non-Serviceable Address
```bash
curl -X POST http://localhost:8002/api/check \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "session_id": "test123",
    "message": "Can you service 789 Remote Road, Nowhere, AK 99999?"
  }'
```

### Invalid Address Format
```bash
curl -X POST http://localhost:8002/api/check \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "session_id": "test123",
    "message": "Check somewhere in Philadelphia"
  }'
```

## Run Tests

```bash
pytest tests/ -v
```

## View API Docs

Open browser: http://localhost:8002/docs

## Mock Data

Development mode uses these serviceable ZIP codes:
- **19107** - Philadelphia downtown (Fiber)
- **19103** - Philadelphia center (Fiber)
- **18000** - Rural PA (Coax)
- **10001** - NYC (Fiber)
- **90001** - LA (Coax/DOCSIS)

All other ZIPs return "not serviceable"

## Integration as Sub-Agent

```python
from serviceability_agent import get_agent

# Add to your Super Agent
serviceability_sub_agent = get_agent()
```

For full documentation, see README.md
