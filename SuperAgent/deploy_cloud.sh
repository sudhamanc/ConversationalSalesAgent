#!/bin/bash
set -e

PROJECT_ID="conversational-sales-agent"
REGION="us-central1"
SERVICE="conversational-sales-agent"
REPO="sales-agent-repo"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/sales-agent"

# Use --project flag instead of gcloud config set (avoids quota-project warning hang)
export CLOUDSDK_CORE_PROJECT="$PROJECT_ID"

# Change to workspace root (one level up from SuperAgent/)
cd "$(dirname "$0")/.."

echo "[deploy] Checking gcloud authentication..."
if ! gcloud auth print-access-token --project=$PROJECT_ID &>/dev/null; then
  echo "[deploy] Not logged in — starting gcloud auth login..."
  gcloud auth login
fi
echo "[deploy] ✓ Authenticated"

echo "[deploy] Configuring Docker for Artifact Registry..."
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet --project=$PROJECT_ID
echo "[deploy] ✓ Docker configured"

echo "[deploy] Building Docker image (linux/amd64)..."
echo "[deploy]   Image: $IMAGE:latest"
docker build --platform linux/amd64 -t $IMAGE:latest .
echo "[deploy] ✓ Image built"

echo "[deploy] Pushing image to Artifact Registry..."
docker push $IMAGE:latest
echo "[deploy] ✓ Image pushed"

echo "[deploy] Deploying to Cloud Run (this may take 2-5 minutes)..."
echo "[deploy]   Service: $SERVICE | Region: $REGION | Memory: 4Gi | CPU: 2"
gcloud run deploy $SERVICE \
  --project=$PROJECT_ID \
  --image=$IMAGE:latest \
  --platform=managed \
  --region=$REGION \
  --port=8000 \
  --memory=4Gi \
  --cpu=2 \
  --min-instances=0 \
  --max-instances=1 \
  --concurrency=10 \
  --timeout=300 \
  --execution-environment=gen2 \
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,SESSION_SECRET_KEY=SESSION_SECRET_KEY:latest,SMTP_USER=SMTP_USER:latest,SMTP_PASSWORD=SMTP_PASSWORD:latest" \
  --set-env-vars="GEMINI_MODEL=gemini-3-flash-preview,LLM_PROVIDER=google,ENABLE_SUB_AGENTS=true,SERVER_HOST=0.0.0.0,SERVER_PORT=8000,LOG_LEVEL=info,DEBUG=false,SMTP_ENABLED=true,SMTP_HOST=smtp.gmail.com,SMTP_PORT=587,SMTP_FROM_NAME=ComSales Notifications,MODEL_TEMPERATURE=0.7,MODEL_MAX_OUTPUT_TOKENS=2048,RATE_LIMIT_RPM=20,RATE_LIMIT_RPH=200,GCS_DATA_BUCKET=conversational-sales-agent-data,SALES_AGENT_DB_PATH=/app/SuperAgent/data/sales_agent.db,SAFETY_DANGEROUS=BLOCK_LOW_AND_ABOVE,SAFETY_HARASSMENT=BLOCK_LOW_AND_ABOVE,SAFETY_HATE_SPEECH=BLOCK_LOW_AND_ABOVE,SAFETY_SEXUALLY_EXPLICIT=BLOCK_LOW_AND_ABOVE,ALLOWED_ORIGINS=https://conversational-sales-agent-647996714470.us-central1.run.app" \
  --allow-unauthenticated

echo "[deploy] ✓ Deployment complete. Live at:"
echo "          https://conversational-sales-agent-647996714470.us-central1.run.app"
echo "          https://conversational-sales-agent-enu5rlyquq-uc.a.run.app"
