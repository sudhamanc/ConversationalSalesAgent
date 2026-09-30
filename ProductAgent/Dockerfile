# Product agent (A2A). Build context = repo root:
#   docker build -f ProductAgent/Dockerfile .
# No PyTorch / embedding model: knowledge search runs in services/catalog.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8080
WORKDIR /app
COPY libs/sales_common /app/libs/sales_common
RUN pip install /app/libs/sales_common
COPY ProductAgent /app/ProductAgent
RUN pip install /app/ProductAgent
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn product_agent.server:app --host 0.0.0.0 --port ${PORT}"]
