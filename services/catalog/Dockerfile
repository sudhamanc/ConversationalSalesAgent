# Catalog service (REST + MCP + product-knowledge RAG).
# Build context = repo root:  docker build -f services/catalog/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8080 \
    CHROMA_PATH=/app/data/embeddings \
    EMBEDDING_MODEL_PATH=/app/models/all-MiniLM-L6-v2 \
    HF_HOME=/app/.hf_cache

WORKDIR /app

# CPU-only PyTorch first so sentence-transformers does not pull CUDA wheels.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY libs/sales_common /app/libs/sales_common
RUN pip install /app/libs/sales_common

COPY services/catalog /app/services/catalog
RUN pip install /app/services/catalog

# Pre-stage the embedding model and build the (read-only) Chroma index into the image.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2').save('${EMBEDDING_MODEL_PATH}')" \
 && python /app/services/catalog/scripts/ingest_knowledge.py --chroma-path "${CHROMA_PATH}"

RUN useradd --create-home --uid 10001 app && chown -R app /app/data
USER app
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 RAG_BUILD_ON_START=false
WORKDIR /app/services/catalog
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn catalog_service.app:app --host 0.0.0.0 --port ${PORT}"]
