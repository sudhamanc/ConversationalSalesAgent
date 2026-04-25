#!/bin/bash
set -e

PROJECT_ID="conversational-sales-agent"
REGION="us-central1"
SERVICE="conversational-sales-agent"

echo "[start] Checking gcloud authentication..."
if ! gcloud auth print-access-token &>/dev/null; then
  echo "[start] Not logged in — starting gcloud auth login..."
  gcloud auth login
fi

gcloud config set project $PROJECT_ID --quiet

echo "[start] Restoring public access..."
gcloud run services add-iam-policy-binding $SERVICE \
  --region=$REGION \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --quiet

echo "[start] Done. Service '$SERVICE' is live at:"
echo "         https://conversational-sales-agent-647996714470.us-central1.run.app"
echo "         https://conversational-sales-agent-enu5rlyquq-uc.a.run.app"
