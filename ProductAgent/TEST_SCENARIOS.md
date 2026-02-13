# 🧪 Test Scenarios - Product Agent

Test scenarios for the Product Agent based on [Scenarios.md](../Scenarios.md) section 5.

---

## Test Scenarios from Scenarios.md

### Positive Cases

#### 5.1 - Specific Product Query
**Input:** "What is the speed of Fiber 5G?"
**Expected:** Returns accurate specs from product manuals
**Status:** ✅ Implemented

**Test:**
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_5_1",
    "message": "What is the speed of Fiber 5G?"
  }'
```

#### 5.2 - Comparison Query
**Input:** "Compare Fiber 1G vs Fiber 5G"
**Expected:** Returns side-by-side comparison table
**Status:** ✅ Implemented

**Test:**
```bash
curl -X POST http://localhost:8003/compare \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_5_2",
    "product_ids": ["FIB-1G", "FIB-5G"]
  }'
```

#### 5.3 - Feature Inquiry
**Input:** "Does Fiber 5G include a static IP?"
**Expected:** Returns feature details from documentation
**Status:** ✅ Implemented

**Test:**
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_5_3",
    "message": "Does Fiber 5G include a static IP?"
  }'
```

#### 5.4 - SLA Inquiry
**Input:** "What's the uptime guarantee?"
**Expected:** Returns SLA terms from product manual
**Status:** ✅ Implemented

**Test:**
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_5_4",
    "message": "What is the uptime guarantee for business fiber?"
  }'
```

#### 5.5 - Hardware Specs
**Input:** "What router is included?"
**Expected:** Returns hardware documentation
**Status:** ✅ Implemented

**Test:**
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_5_5",
    "message": "What router is included with Fiber 5G?"
  }'
```

---

### Negative Cases

#### 5.6 - Non-Existent Product
**Input:** "Tell me about Fiber 100G"
**Expected:** "We don't currently offer that product"
**Status:** ✅ Implemented

**Test:**
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_5_6",
    "message": "Tell me about Fiber 100G"
  }'
```

#### 5.7 - Vague Query
**Input:** "Tell me about internet"
**Expected:** Asks for specifics or lists available products
**Status:** ✅ Implemented

**Test:**
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_5_7",
    "message": "Tell me about internet"
  }'
```

#### 5.8 - ChromaDB Unavailable
**Input:** Any product query when ChromaDB fails
**Expected:** Falls back to basic product info from cache
**Status:** ✅ Implemented (automatic fallback)

**Test:**
```python
# Manually test by stopping ChromaDB or removing embeddings directory
# Agent should automatically fall back to product catalog tools
```

#### 5.9 - Competitor Product Query
**Input:** "How does your Fiber compare to AT&T?"
**Expected:** Guardrails: declines to discuss competitors
**Status:** ✅ Implemented in prompts

**Test:**
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_5_9",
    "message": "How does your Fiber 5G compare to AT&T fiber?"
  }'
```

#### 5.10 - Out-of-Date Document
**Input:** Query about potentially outdated info
**Expected:** Returns best available info, notes last update date
**Status:** ✅ Implemented (metadata includes source)

---

## Additional Test Scenarios

### Product Catalog Tests

#### TC-1: List All Products
```bash
curl http://localhost:8003/products
```
**Expected:** Returns all 6 products

#### TC-2: Filter by Category
```bash
curl "http://localhost:8003/products?category=Fiber%20Internet"
```
**Expected:** Returns only fiber products (3 products)

#### TC-3: Get Specific Product
```bash
curl http://localhost:8003/products/FIB-5G
```
**Expected:** Returns complete Fiber 5G details

#### TC-4: Invalid Product ID
```bash
curl http://localhost:8003/products/INVALID-ID
```
**Expected:** 404 Not Found

---

### Comparison Tests

#### TC-5: Compare 3 Products
```bash
curl -X POST http://localhost:8003/compare \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_compare_3",
    "product_ids": ["FIB-1G", "FIB-5G", "FIB-10G"]
  }'
```
**Expected:** Side-by-side comparison of 3 fiber products

#### TC-6: Too Few Products
```bash
curl -X POST http://localhost:8003/compare \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_compare_few",
    "product_ids": ["FIB-1G"]
  }'
```
**Expected:** Error message (need at least 2 products)

#### TC-7: Too Many Products
```bash
curl -X POST http://localhost:8003/compare \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_compare_many",
    "product_ids": ["FIB-1G", "FIB-5G", "FIB-10G", "COAX-200M", "COAX-500M", "COAX-1G"]
  }'
```
**Expected:** Error message (max 5 products)

---

### RAG Tests (Requires ChromaDB)

#### TC-8: Semantic Search
```python
from product_agent.tools.rag_tools import query_product_documentation

result = query_product_documentation(
    "What kind of network speeds can I get?",
    product_id=None
)
```
**Expected:** Returns relevant speed information from docs

#### TC-9: Product-Specific RAG
```python
result = query_product_documentation(
    "installation timeline",
    product_id="FIB-1G"
)
```
**Expected:** Returns Fiber 1G installation info

#### TC-10: No Results
```python
result = query_product_documentation(
    "quantum entanglement speeds",
    product_id="FIB-1G"
)
```
**Expected:** No relevant results message

---

### Cache Tests

#### TC-11: Cache Hit
```python
from product_agent.tools.product_tools import get_product_by_id
from product_agent.utils.cache import get_cache_stats, clear_cache

clear_cache()
get_product_by_id("FIB-5G")  # First call - miss
get_product_by_id("FIB-5G")  # Second call - hit
stats = get_cache_stats()
```
**Expected:** Cache hits > 0

#### TC-12: Cache Expiration
```python
# Would need to mock time or wait 24 hours
# Cache entries expire after TTL
```

---

### Error Handling Tests

#### TC-13: Malformed Request
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{invalid json}'
```
**Expected:** 422 Validation Error

#### TC-14: Missing Required Fields
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user"
  }'
```
**Expected:** 422 Validation Error (missing session_id, message)

---

### Performance Tests

#### TC-15: Concurrent Requests
```bash
# Run 100 concurrent requests
for i in {1..100}; do
  curl -X POST http://localhost:8003/query \
    -H "Content-Type: application/json" \
    -d "{
      \"user_id\": \"user_$i\",
      \"session_id\": \"session_$i\",
      \"message\": \"What is Fiber 5G?\"
    }" &
done
wait
```
**Expected:** All requests complete successfully

#### TC-16: Large Message
```bash
# Send very long message (test token limits)
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"test_user\",
    \"session_id\": \"test_large\",
    \"message\": \"$(python -c 'print("What is " * 1000)')\"
  }"
```
**Expected:** Handles gracefully (truncate or error)

---

## Infrastructure-Aware Filtering Tests (Added: Feb 2026)

### TC-17: Fiber Infrastructure with Speed Limit
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_infra_fiber_5g",
    "message": "[INFRASTRUCTURE AVAILABILITY]\nLocation: 123 Main St, Philadelphia, PA 19103\nNetwork Type: Fiber\nSpeed Capability: 5000 Mbps (max download), 5000 Mbps (max upload)\nConnection Type: Symmetrical\nService Class: Business\n\nCustomer Question: What internet plans are available for a 30-employee office?"
  }'
```
**Expected:** Recommends only Fiber products up to 5 Gbps (1G, 5G) with symmetrical speeds. Excludes 10G Fiber and all Coax products.

### TC-18: Coax Infrastructure with Asymmetrical Speeds
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_infra_coax",
    "message": "[INFRASTRUCTURE AVAILABILITY]\nLocation: 456 Oak Ave, Philadelphia, PA 19104\nNetwork Type: Coax/HFC\nSpeed Capability: 500 Mbps (max download), 50 Mbps (max upload)\nConnection Type: Asymmetrical\nService Class: Business\n\nCustomer Question: Show me available business internet options"
  }'
```
**Expected:** Recommends only Coax/Cable products up to 500 Mbps (200M, 500M). Excludes all Fiber products and 1G Coax (if exceeds speed).

### TC-19: Product Comparison with Infrastructure Context
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_infra_compare",
    "message": "[INFRASTRUCTURE AVAILABILITY]\nNetwork Type: Fiber\nSpeed Capability: 10000 Mbps (max download), 10000 Mbps (max upload)\nConnection Type: Symmetrical\n\nCompare all available fiber plans"
  }'
```
**Expected:** Compares Fiber 1G, 5G, and 10G. Does not include Coax products in comparison.

### TC-20: Query Without Infrastructure Context (Baseline)
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_no_infra",
    "message": "What are your best business internet options?"
  }'
```
**Expected:** Recommends all products across Fiber and Coax without filtering. Should present full catalog.

### TC-21: Infrastructure Context with Speed Exceeding All Products
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_infra_high_speed",
    "message": "[INFRASTRUCTURE AVAILABILITY]\nNetwork Type: Fiber\nSpeed Capability: 100000 Mbps (max download), 100000 Mbps (max upload)\nConnection Type: Symmetrical\n\nWhat are my options?"
  }'
```
**Expected:** Recommends all Fiber products (1G, 5G, 10G) since infrastructure supports higher speeds.

### TC-22: Infrastructure Context with Low Speed Limit
```bash
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_infra_low_speed",
    "message": "[INFRASTRUCTURE AVAILABILITY]\nNetwork Type: Fiber\nSpeed Capability: 1000 Mbps (max download), 1000 Mbps (max upload)\nConnection Type: Symmetrical\n\nWhat business fiber plans are available?"
  }'
```
**Expected:** Recommends only Fiber 1G product. Excludes 5G and 10G due to speed constraints.

---

## Automated Test Suite

Run all tests:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=product_agent --cov-report=html
```

Run specific scenario:
```bash
pytest tests/test_tools.py::TestProductTools::test_get_product_by_id_success -v
```

---

## Manual Testing Checklist

- [ ] All 10 scenario tests (5.1-5.10) pass
- [ ] Product catalog endpoints work
- [ ] Comparison functionality works
- [ ] RAG queries return relevant results
- [ ] Cache improves performance
- [ ] Error handling works correctly
- [ ] API documentation accessible
- [ ] Health check returns correct status
- [ ] Statistics endpoint works
- [ ] Concurrent requests handled
- [ ] Infrastructure-aware filtering works (TC-17 to TC-22)
- [ ] Fiber infrastructure filters correctly
- [ ] Coax infrastructure filters correctly
- [ ] Speed limits are respected
- [ ] Symmetrical requirements handled properly

---

**Last Updated**: February 13, 2026  
**Test Coverage**: 80%+
