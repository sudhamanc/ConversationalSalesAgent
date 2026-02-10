# 🚀 Product Agent Quick Start Guide

Get the Product Agent up and running in 5 minutes!

---

## Prerequisites

- Python 3.12+
- Google Gemini API key
- Terminal/Command Prompt

---

## Installation Steps

### 1. Navigate to Directory
```bash
cd ProductAgent
```

### 2. Create Virtual Environment
```bash
python -m venv .venv

# Activate (Mac/Linux)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API key
nano .env  # or use your preferred editor
```

**Required in `.env`:**
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### 5. Run the Server
```bash
python main.py
```

You should see:
```
🚀 Product Agent Starting Up
✅ Vector DB initialized: 0 documents
✅ Agent: product-agent
✅ Model: gemini-2.0-flash
```

Server will be running at: `http://localhost:8003`

---

## Quick Test

### Test 1: Health Check
```bash
curl http://localhost:8003/health
```

Expected response:
```json
{
  "status": "ok",
  "agent": "product-agent",
  "model": "gemini-2.0-flash",
  "vector_db": {
    "available": false,
    "documents": 0
  }
}
```

### Test 2: List Products
```bash
curl http://localhost:8003/products
```

### Test 3: Get Specific Product
```bash
curl http://localhost:8003/products/FIB-5G
```

### Test 4: Query via API
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_session_001",
    "message": "What are the speeds for Fiber 5G?"
  }'
```

---

## API Documentation

Visit the interactive API docs:
- Swagger UI: `http://localhost:8003/docs`
- ReDoc: `http://localhost:8003/redoc`

---

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'google.adk'`
**Solution:**
```bash
pip install google-adk google-genai
```

### Issue: `GEMINI_API_KEY not set`
**Solution:**
Make sure you've created `.env` file with your API key:
```env
GEMINI_API_KEY=your_key_here
```

### Issue: ChromaDB warnings
**Note:** ChromaDB is optional. The agent will work without it using the product catalog fallback. To fully enable RAG:
```bash
pip install chromadb sentence-transformers
```

---

## Next Steps

✅ **Test the API endpoints** using curl or Postman  
✅ **Run the test suite**: `pytest tests/ -v`  
✅ **Review the README**: See [README.md](README.md) for full documentation  
✅ **Set up Vector DB**: See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md#vector-database-setup)  
✅ **Integrate with Super Agent**: See integration guide  

---

## Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/query` | POST | Natural language query |
| `/compare` | POST | Compare products |
| `/products` | GET | List all products |
| `/products/{id}` | GET | Get specific product |
| `/stats` | GET | Agent statistics |

---

**Need Help?** Check [README.md](README.md) for detailed documentation!
