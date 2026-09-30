# Gateway image: FastAPI SSE chat + sales_journey workflow + built React UI.
# Build context = repository root:
#   docker build -f SuperAgent/Dockerfile -t csa-gateway .
# The same image runs migrations (docker compose db-init, Cloud Run job csa-db-init):
#   python -m sales_common.migrate --seed        (DB_DIR=/app/db)

# --- Stage 1: React client -----------------------------------------------------
FROM node:20-slim AS client
WORKDIR /app/SuperAgent/client
COPY SuperAgent/client/package.json SuperAgent/client/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY SuperAgent/client/ ./
RUN npm run build

# --- Stage 2: Python runtime ---------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8080 DB_DIR=/app/db
WORKDIR /app
COPY libs/sales_common /app/libs/sales_common
RUN pip install /app/libs/sales_common
COPY SuperAgent/pyproject.toml /app/SuperAgent/pyproject.toml
COPY SuperAgent/super_agent /app/SuperAgent/super_agent
RUN pip install /app/SuperAgent
COPY SuperAgent/server /app/SuperAgent/server
COPY --from=client /app/SuperAgent/client/dist /app/SuperAgent/client/dist
COPY db /app/db
RUN useradd --create-home --uid 10001 app
USER app
WORKDIR /app/SuperAgent/server
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
