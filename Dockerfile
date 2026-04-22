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

# GCS client for SQLite DB sync
RUN pip install --no-cache-dir google-cloud-storage

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
COPY requirements.txt .

# Copy built React app into the location FastAPI serves it from
COPY --from=frontend-builder /app/SuperAgent/client/dist ./SuperAgent/client/dist

RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app/SuperAgent/server
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
