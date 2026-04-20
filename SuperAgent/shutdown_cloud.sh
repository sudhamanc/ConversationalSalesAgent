#!/bin/bash
set -e

PROJECT_ID="conversational-sales-agent"
REGION="us-central1"
SERVICE="conversational-sales-agent"

echo "[shutdown] Checking gcloud authentication..."
if ! gcloud auth print-access-token &>/dev/null; then
  echo "[shutdown] Not logged in — starting gcloud auth login..."
  gcloud auth login
fi

gcloud config set project $PROJECT_ID --quiet

echo "[shutdown] Removing public access (requiring authentication)..."
gcloud run services remove-iam-policy-binding $SERVICE \
  --region=$REGION \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --quiet 2>/dev/null || true

echo "[shutdown] Done. '$SERVICE' is now private — public access blocked."
echo "           The container will scale to zero automatically when idle."
echo "           To restore public access: run ./start_cloud.sh"
