## ADDED Requirements

### Requirement: Embedding model readable in the image

The catalog container image SHALL pre-stage the embedding model at `EMBEDDING_MODEL_PATH`, with every file readable by the non-root runtime user. Knowledge and FAQ search SHALL then be available in the container without network access.

#### Scenario: FAQ search on Cloud Run
- **WHEN** the deployed catalog service receives `search_faq("What is your cancellation policy?")`
- **THEN** it returns `available: true` with passages from the FAQ corpus
