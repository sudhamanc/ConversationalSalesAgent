FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8080
WORKDIR /app
COPY libs/sales_common /app/libs/sales_common
RUN pip install /app/libs/sales_common
COPY ServiceFulfillmentAgent /app/ServiceFulfillmentAgent
RUN pip install /app/ServiceFulfillmentAgent
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn service_fulfillment_agent.server:app --host 0.0.0.0 --port ${PORT}"]
