# 📦 Product Agent

[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-1.20.0-blue.svg)](https://github.com/google/adk)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.4.0-orange.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> An Info/RAG AI agent for product specifications and documentation retrieval in B2B telecommunications sales.

---

## 📋 Overview

The **Product Agent** is a specialized AI agent built on Google's Agent Development Kit (ADK) that retrieves technical product information using RAG (Retrieval-Augmented Generation). It queries a ChromaDB vector database containing product manuals, specification sheets, and documentation to provide accurate, zero-hallucination responses about business internet products.

### Key Features

- ✅ **RAG-Powered**: Semantic search over product documentation using ChromaDB
- 📚 **Comprehensive Info**: Technical specs, features, SLAs, hardware details
- 🔄 **Product Comparison**: Side-by-side comparison of multiple products
- 💡 **Smart Recommendations**: Suggests alternatives based on customer needs
- 🚀 **24-Hour Caching**: Reduces redundant queries with intelligent caching
- 🔒 **Zero Hallucination**: All data from vector DB or product catalog
- 🛠️ **Tool-Based**: 11 specialized tools for different query types

---

## 🏗️ Architecture

### Agent Type Classification

| Attribute | Value |
|-----------|-------|
| **Type** | Info/RAG (Information Retrieval) |
| **Purpose** | Product specification & documentation retrieval |
| **Framework** | Google ADK (Agent Development Kit) |
| **Source of Truth** | Vector DB (ChromaDB) + Product Catalog |
| **Temperature** | 0.1 (low, for factual accuracy) |
| **Cluster** | Configuration Agents |

### Component Structure

```
ProductAgent/
├── main.py                          # FastAPI server + ADK Runner
├── product_agent/
│   ├── __init__.py                  # Package exports
│   ├── agent.py                     # Main agent configuration
│   ├── prompts.py                   # Agent instructions
│   ├── models/
│   │   └── schemas.py               # Pydantic data models
│   ├── tools/
│   │   ├── rag_tools.py             # RAG/Vector DB tools
│   │   ├── product_tools.py         # Product catalog tools
│   │   └── comparison_tools.py      # Product comparison tools
│   └── utils/
│       ├── logger.py                # Structured logging
│       ├── cache.py                 # 24-hour TTL cache
│       └── vector_db.py             # ChromaDB manager
├── tests/
│   ├── test_tools.py                # Unit tests
│   ├── test_agent.py                # Integration tests
│   └── test_rag.py                  # RAG tests
└── data/
    ├── product_docs/                # Sample product PDFs
    └── embeddings/                  # ChromaDB storage (gitignored)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- Google Gemini API key ([Get one free](https://aistudio.google.com/apikey))
- (Optional) ChromaDB for RAG functionality

### Installation

1. **Navigate to the ProductAgent directory**:
   ```bash
   cd ProductAgent
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

5. **Run the server**:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8003`

---

## 📚 API Documentation

### Endpoints

#### `POST /query`
Query product information using natural language.

**Request:**
```json
{
  "user_id": "user123",
  "session_id": "session456",
  "message": "What are the speeds for Fiber 5G?"
}
```

**Response:**
```json
{
  "response": "The Business Fiber 5 Gbps provides symmetrical speeds of 5 Gbps...",
  "agent": "product-agent",
  "session_id": "session456"
}
```

#### `POST /compare`
Compare multiple products side-by-side.

**Request:**
```json
{
  "user_id": "user123",
  "session_id": "session456",
  "product_ids": ["FIB-1G", "FIB-5G", "FIB-10G"]
}
```

#### `GET /products`
List all available products or filter by category.

**Query Parameters:**
- `category` (optional): Filter by category (e.g., "Fiber Internet")

#### `GET /products/{product_id}`
Get detailed information about a specific product.

**Example:**
```bash
curl http://localhost:8003/products/FIB-5G
```

#### `GET /health`
Health check endpoint with vector DB status.

#### `GET /stats`
Get agent statistics (cache, vector DB stats).

---

## 🛠️ Tools Overview

### RAG Tools (Primary Data Source)
1. **query_product_documentation** - Semantic search over product docs
2. **search_technical_specs** - Find technical specifications
3. **get_product_features** - Retrieve feature lists
4. **get_sla_terms** - Get SLA details

### Product Catalog Tools (Structured Data)
5. **list_available_products** - Browse product catalog
6. **get_product_by_id** - Get specific product details
7. **search_products_by_criteria** - Filter by speed, tech, price
8. **get_product_categories** - List product categories

### Comparison Tools
9. **compare_products** - Side-by-side comparison
10. **suggest_alternatives** - Find similar/alternative products
11. **get_best_value_product** - Recommend best value

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `GEMINI_MODEL` | Model to use | `gemini-2.0-flash` |
| `AGENT_NAME` | Agent identifier | `product_agent` |
| `PORT` | Server port | `8003` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CHROMA_PERSIST_DIRECTORY` | ChromaDB storage | `./data/embeddings` |
| `CHROMA_COLLECTION_NAME` | Collection name | `product_documents` |
| `EMBEDDING_MODEL` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `CACHE_TTL_HOURS` | Cache TTL in hours | `24` |
| `CACHE_MAX_SIZE` | Max cache entries | `1000` |

---

## 📊 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Suites
```bash
# Unit tests for tools
pytest tests/test_tools.py -v

# Integration tests
pytest tests/test_agent.py -v

# RAG tests (requires ChromaDB)
pytest tests/test_rag.py -v
```

### Test Coverage
```bash
pytest tests/ --cov=product_agent --cov-report=html
open htmlcov/index.html
```

---

## 🗄️ Vector Database Setup

### Initialize ChromaDB

The vector database is automatically initialized on first run. To populate it with product documents:

1. **Add product documents** to `data/product_docs/`
2. **Run the ingestion script** (create one using the example below)

**Example Document Ingestion:**
```python
from product_agent.utils.vector_db import get_vector_db

vector_db = get_vector_db()

# Add documents
documents = [
    "Business Fiber 5 Gbps provides symmetrical 5 Gbps speeds...",
    "The service includes 99.9% uptime SLA with priority support..."
]
metadatas = [
    {"product_id": "FIB-5G", "source": "fiber_5g_spec.pdf", "section": "specs"},
    {"product_id": "FIB-5G", "source": "fiber_5g_spec.pdf", "section": "sla"}
]

vector_db.add_documents(documents, metadatas)
```

---

## 🎯 Use Cases

### Scenario 1: Product Specification Query
```
User: "What is the upload speed of Fiber 5G?"
Agent: [Uses search_technical_specs + query_product_documentation]
Response: "The Business Fiber 5 Gbps provides 5 Gbps symmetrical upload speeds..."
```

### Scenario 2: Product Comparison
```
User: "Compare Fiber 1G and Fiber 5G"
Agent: [Uses compare_products]
Response: [Side-by-side comparison table with speeds, prices, features]
```

### Scenario 3: Feature Inquiry
```
User: "Does Fiber 5G include static IPs?"
Agent: [Uses get_product_features]
Response: "Yes, Business Fiber 5G includes 5 static IP addresses at no additional cost..."
```

### Scenario 4: Alternative Suggestions
```
User: "Is there a cheaper fiber option?"
Agent: [Uses suggest_alternatives with criteria="cheaper"]
Response: "Yes, Business Fiber 1 Gbps is available at $249/month..."
```

---

## 🔗 Integration with Super Agent

The Product Agent is designed to be integrated as a sub-agent in the Super Agent orchestration system. See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for details.

**Integration Pattern:**
```python
from product_agent import get_agent

product_sub_agent = get_agent()
# Register with Super Agent
```

---

## 📈 Performance

- **Average Query Response**: < 500ms (with cache)
- **Cache Hit Rate**: ~70% (typical usage)
- **Vector DB Query**: < 200ms (ChromaDB)
- **Concurrent Requests**: Supports 100+ concurrent sessions

---

## 🐛 Troubleshooting

### ChromaDB Not Available
If ChromaDB is not installed or fails to initialize:
- Agent automatically falls back to product catalog tools
- Basic product info still available
- Install ChromaDB: `pip install chromadb sentence-transformers`

### Cache Issues
```bash
# Clear cache via API
curl -X POST http://localhost:8003/cache/clear

# Or in Python
from product_agent.utils.cache import clear_cache
clear_cache()
```

### Vector DB Issues
```bash
# Check vector DB stats
curl http://localhost:8003/stats

# Reset collection (warning: deletes all data)
from product_agent.utils.vector_db import get_vector_db
get_vector_db().reset_collection()
```

---

## 🤝 Contributing

This agent follows the same patterns as ServiceabilityAgent for consistency across the project.

---

## 📄 License

MIT License - See LICENSE file for details

---

## 📞 Support

For questions or issues:
- Check [QUICKSTART.md](QUICKSTART.md) for quick start guide
- Review [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for integration details
- See [Scenarios.md](../Scenarios.md) for test scenarios

---

**Built for B2B Agentic Sales Orchestration System**
**Drexel University - Senior Design Project (Winter/Spring 2026)**
