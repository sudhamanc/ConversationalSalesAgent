# Stage 1: Build React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/SuperAgent/client
COPY SuperAgent/client/package*.json ./
RUN npm ci
COPY SuperAgent/client/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Standalone essentials — Dockerfile works even without requirements.txt
# (pip skips already-installed packages, so no build-time cost for duplicates)
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --trusted-host download.pytorch.org \
    --trusted-host download-r2.pytorch.org \
    google-cloud-storage \
    fastapi \
    "uvicorn[standard]" \
    google-genai \
    google-adk \
    python-dotenv \
    pydantic \
    pandas \
    chromadb \
    sentence-transformers \
    diskcache \
    requests

# Install from requirements.txt (layer cached separately from source code)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --trusted-host download.pytorch.org \
    --trusted-host download-r2.pytorch.org \
    -r requirements.txt

# Copy all agent directories (sub-agents resolve paths relative to workspace root)
COPY SuperAgent/ ./SuperAgent/
COPY DiscoveryAgent/ ./DiscoveryAgent/
COPY ServiceabilityAgent/ ./ServiceabilityAgent/
COPY ProductAgent/ ./ProductAgent/
COPY OfferManagement/ ./OfferManagement/
COPY PaymentAgent/ ./PaymentAgent/
COPY OrderAgent/ ./OrderAgent/
COPY ServiceFulfillmentAgent/ ./ServiceFulfillmentAgent/
COPY CustomerCommunicationAgent/ ./CustomerCommunicationAgent/

# Copy built React app into the location FastAPI serves it from
COPY --from=frontend-builder /app/SuperAgent/client/dist ./SuperAgent/client/dist

# Ensure unified DB data directory exists (entrypoint downloads DB here from GCS)
RUN mkdir -p /app/SuperAgent/data

# Ingest product knowledge into ChromaDB at build time (baked into image)
RUN python ProductAgent/scripts/ingest_knowledge.py

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app/SuperAgent/server
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
