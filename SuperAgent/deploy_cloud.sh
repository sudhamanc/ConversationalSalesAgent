#!/bin/bash
set -e

PROJECT_ID="conversational-sales-agent"
REGION="us-central1"
SERVICE="conversational-sales-agent"
REPO="sales-agent-repo"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/sales-agent"

# Change to workspace root (one level up from SuperAgent/)
cd "$(dirname "$0")/.."

echo "[deploy] Checking gcloud authentication..."
if ! gcloud auth print-access-token &>/dev/null; then
  echo "[deploy] Not logged in — starting gcloud auth login..."
  gcloud auth login
fi

gcloud config set project $PROJECT_ID --quiet

echo "[deploy] Configuring Docker for Artifact Registry..."
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

echo "[deploy] Building Docker image..."
docker build --platform linux/amd64 -t $IMAGE:latest .

echo "[deploy] Pushing image to Artifact Registry..."
docker push $IMAGE:latest

echo "[deploy] Deploying to Cloud Run..."
gcloud run deploy $SERVICE \
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
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,SESSION_SECRET_KEY=SESSION_SECRET_KEY:latest" \
  --set-env-vars="GEMINI_MODEL=gemini-3-flash-preview,LLM_PROVIDER=google,ENABLE_SUB_AGENTS=true,SERVER_HOST=0.0.0.0,SERVER_PORT=8000,LOG_LEVEL=info,DEBUG=false,SMTP_ENABLED=false,MODEL_TEMPERATURE=0.7,MODEL_MAX_OUTPUT_TOKENS=2048,RATE_LIMIT_RPM=20,RATE_LIMIT_RPH=200,GCS_DATA_BUCKET=conversational-sales-agent-data,SAFETY_DANGEROUS=BLOCK_LOW_AND_ABOVE,SAFETY_HARASSMENT=BLOCK_LOW_AND_ABOVE,SAFETY_HATE_SPEECH=BLOCK_LOW_AND_ABOVE,SAFETY_SEXUALLY_EXPLICIT=BLOCK_LOW_AND_ABOVE,ALLOWED_ORIGINS=https://conversational-sales-agent-647996714470.us-central1.run.app" \
  --allow-unauthenticated \
  --quiet

echo "[deploy] Deployment complete. Live at:"
echo "          https://conversational-sales-agent-647996714470.us-central1.run.app"
echo "          https://conversational-sales-agent-enu5rlyquq-uc.a.run.app"
