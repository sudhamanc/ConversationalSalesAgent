# 🔗 Product Agent Integration Guide

Guide for integrating the Product Agent into the Super Agent orchestration system.

---

## Overview

The Product Agent is a specialized sub-agent designed to be orchestrated by the Super Agent. It provides product information, specifications, and comparisons through a consistent ADK-based interface.

---

## Integration Architecture

```
┌─────────────────────┐
│   SUPER AGENT       │
│   (Orchestrator)    │
└──────────┬──────────┘
           │
           │ delegates
           ▼
┌─────────────────────┐
│   PRODUCT AGENT     │
│   (Info/RAG)        │
│                     │
│   Tools:            │
│   • RAG queries     │
│   • Product catalog │
│   • Comparisons     │
└──────────┬──────────┘
           │
           ▼
    ┌─────────────┐
    │  ChromaDB   │
    │  (Vector DB)│
    └─────────────┘
```

---

## Integration Methods

### Method 1: Direct Agent Integration (Recommended)

Import and use the agent directly in your orchestration code:

```python
from product_agent import get_agent

# Get the configured Product Agent
product_agent = get_agent()

# Use in Super Agent's sub-agent list
super_agent_config = {
    "sub_agents": {
        "product": product_agent,
        # ... other agents
    }
}
```

### Method 2: API-Based Integration

Run Product Agent as a standalone service and call via HTTP:

```python
import requests

# Product Agent running on port 8003
PRODUCT_AGENT_URL = "http://localhost:8003"

def query_product_agent(user_id: str, session_id: str, message: str):
    response = requests.post(
        f"{PRODUCT_AGENT_URL}/query",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": message
        }
    )
    return response.json()
```

---

## Agent-to-Agent (A2A) Protocol

### Communication Pattern

```python
# Super Agent determines user needs product info
if intent == "product_inquiry":
    # Delegate to Product Agent
    result = product_agent.process(
        user_input=user_message,
        context={
            "customer_id": customer_id,
            "previous_interactions": history
        }
    )
    
    # Product Agent returns structured response
    # Super Agent synthesizes and returns to user
    return synthesize_response(result)
```

### Context Passing

Product Agent expects minimal context:
```python
context = {
    "user_id": str,           # Required
    "session_id": str,        # Required
    "customer_location": str, # Optional - for serviceability context
    "previous_products": []   # Optional - for recommendation context
}
```

---

## Routing Logic

### When to Route to Product Agent

Super Agent should route to Product Agent when user queries include:

1. **Product specifications**: speeds, technology, pricing
2. **Product features**: what's included, SLA terms, hardware
3. **Product comparisons**: "compare X vs Y"
4. **Product recommendations**: "best product for...", "cheapest option"
5. **Technical questions**: "does it include static IPs?", "what's the uptime?"

### Example Routing

```python
def route_query(user_message: str):
    # Simple keyword-based routing
    product_keywords = [
        "speed", "gbps", "mbps", "fiber", "product",
        "price", "cost", "feature", "sla", "compare",
        "uptime", "bandwidth", "specification", "spec"
    ]
    
    if any(keyword in user_message.lower() for keyword in product_keywords):
        return "product_agent"
    
    # ... other routing logic
```

---

## Response Handling

### Product Agent Response Format

```python
{
    "response": str,      # Natural language response
    "agent": str,         # "product-agent"
    "session_id": str,    # Session identifier
}
```

### Super Agent Processing

```python
def process_product_agent_response(response):
    # Extract the response text
    answer = response["response"]
    
    # Optionally enhance with additional context
    enhanced = f"{answer}\n\nWould you like me to check if this product is available at your location?"
    
    # Return to user
    return enhanced
```

---

## Vector Database Setup

### Option 1: Shared Vector DB

If Super Agent manages ChromaDB, pass the instance to Product Agent:

```python
from product_agent.utils.vector_db import initialize_vector_db

# Initialize with custom configuration
vector_db = initialize_vector_db(
    persist_directory="./shared_embeddings",
    collection_name="product_documents"
)
```

### Option 2: Standalone Vector DB

Product Agent manages its own ChromaDB instance:

```env
# .env configuration
CHROMA_PERSIST_DIRECTORY=./ProductAgent/data/embeddings
CHROMA_COLLECTION_NAME=product_documents
```

### Document Ingestion

```python
from product_agent.utils.vector_db import get_vector_db
import os

def ingest_product_documents():
    vector_db = get_vector_db()
    
    # Example: Ingest from data/product_docs/
    docs_dir = "./data/product_docs"
    
    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            with open(os.path.join(docs_dir, filename), "r") as f:
                content = f.read()
                
            # Add to vector DB
            vector_db.add_documents(
                documents=[content],
                metadatas=[{
                    "source": filename,
                    "product_id": extract_product_id(filename)
                }]
            )
    
    print(f"Ingested documents: {vector_db.collection.count()}")
```

---

## Session Management

### Using ADK Session Service

Product Agent uses `InMemorySessionService` by default. For persistent sessions:

```python
from google.adk.sessions import Session
from product_agent import get_agent

# Create session
session = Session(
    user_id="user123",
    session_id="session_456",
    state={"customer_info": {...}}
)

# Query with session context
result = runner.run(
    user_id=session.user_id,
    session_id=session.session_id,
    message="What's the speed of Fiber 5G?"
)
```

---

## Error Handling

### Graceful Degradation

Product Agent implements fallback mechanisms:

1. **ChromaDB unavailable** → Falls back to product catalog tools
2. **Tool failure** → Returns error message with alternative action
3. **No results found** → Suggests alternatives or human handoff

### Super Agent Error Handling

```python
try:
    result = product_agent.query(user_message)
except Exception as e:
    logger.error(f"Product Agent error: {e}")
    
    # Fallback response
    return {
        "response": "I'm having trouble accessing product information right now. Let me connect you with a sales representative.",
        "action": "escalate_to_human"
    }
```

---

## Testing Integration

### Integration Test Example

```python
def test_super_agent_product_agent_integration():
    # Initialize agents
    super_agent = initialize_super_agent()
    product_agent = get_agent()
    
    # Register product agent
    super_agent.register_sub_agent("product", product_agent)
    
    # Test query
    result = super_agent.process(
        user_id="test_user",
        message="What's the speed of Fiber 5G?"
    )
    
    # Verify routing worked
    assert "5 Gbps" in result["response"]
    assert result["sub_agent_used"] == "product"
```

---

## Performance Considerations

### Caching Strategy

- **Query cache**: 24-hour TTL for RAG queries
- **Product catalog**: In-memory, no TTL
- **Vector embeddings**: Persistent in ChromaDB

### Concurrent Requests

Product Agent supports concurrent requests:
- Each session is independent
- Vector DB queries are thread-safe
- Cache is thread-safe using OrderedDict

### Recommended Limits

| Metric | Recommended Value |
|--------|-------------------|
| Concurrent sessions | 100+ |
| Queries per session | Unlimited |
| Vector DB queries | < 10/second |
| Cache size | 1000 entries |

---

## Monitoring & Observability

### Health Checks

```python
# Check Product Agent health
response = requests.get("http://localhost:8003/health")

if response.json()["status"] != "ok":
    # Alert or fallback
    handle_agent_unavailable()
```

### Metrics to Track

1. **Response time**: Average query processing time
2. **Cache hit rate**: Percentage of cached responses
3. **Vector DB performance**: Query latency
4. **Tool usage**: Which tools are called most frequently

### Logging

Product Agent logs to stdout with structured format:
```
2026-02-10 10:30:45 - product_agent.tools.rag_tools - INFO - Querying documentation: What is Fiber 5G?
2026-02-10 10:30:46 - product_agent.tools.rag_tools - INFO - RAG query completed (confidence=0.95)
```

---

## Configuration Management

### Environment Variables for Integration

```env
# Product Agent
AGENT_NAME=product_agent
PORT=8003
GEMINI_API_KEY=your_key

# Vector DB
CHROMA_PERSIST_DIRECTORY=./data/embeddings
CHROMA_COLLECTION_NAME=product_documents

# Cache
CACHE_TTL_HOURS=24
CACHE_MAX_SIZE=1000

# Logging
LOG_LEVEL=INFO
```

---

## Deployment Considerations

### Standalone Deployment

```bash
# Run as separate service
cd ProductAgent
python main.py
```

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY ProductAgent/ /app/

RUN pip install -r requirements.txt

EXPOSE 8003
CMD ["python", "main.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: Service
metadata:
  name: product-agent
spec:
  selector:
    app: product-agent
  ports:
    - port: 8003
      targetPort: 8003
```

---

## Security Considerations

1. **API Key Management**: Never commit API keys to repository
2. **CORS Configuration**: Restrict origins in production
3. **Rate Limiting**: Implement rate limiting for public endpoints
4. **Input Validation**: All user inputs are validated via Pydantic models

---

## Troubleshooting Integration Issues

### Issue: Agent not responding
```python
# Check if agent is initialized
from product_agent import get_agent
agent = get_agent()
assert agent is not None
```

### Issue: Vector DB not available
```python
# Check vector DB status
from product_agent.utils.vector_db import get_vector_db
db = get_vector_db()
print(db.get_collection_stats())
```

### Issue: Cache not working
```python
# Check cache stats
from product_agent.utils.cache import get_cache_stats
print(get_cache_stats())
```

---

## Example: Complete Integration

See [ServiceabilityAgent/INTEGRATION_GUIDE.md](../ServiceabilityAgent/INTEGRATION_GUIDE.md) for a complete integration example that can be adapted for Product Agent.

---

**Next Steps:**
- Review [README.md](README.md) for full documentation
- Check [../Scenarios.md](../Scenarios.md) for test scenarios
- See Super Agent documentation for orchestration details
