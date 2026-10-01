# Spec Delta: product-catalog-service

## ADDED Requirements

### Requirement: FAQ knowledge search

The catalog service SHALL index `data/faq_docs/*.md` into a separate Chroma collection `faq_knowledge` and expose `search_faq(query, top_k)` over MCP and `GET /api/v1/faq/search?q=` over REST. Results SHALL include passage text, topic, section and distance. They SHALL return `available: false` instead of raising when the index cannot be used.

#### Scenario: Policy question
- **WHEN** `search_faq("cancellation policy")` is called
- **THEN** the top passages come from the cancellation-policy FAQ document

#### Scenario: Index unavailable
- **WHEN** the embedding model or index cannot be loaded
- **THEN** `search_faq` returns `available: false` with a message
