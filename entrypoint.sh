#!/bin/bash
set -e

BUCKET="${GCS_DATA_BUCKET:-}"
DB_LOCAL="/app/DiscoveryAgent/data/discover_prospecting_clean.db"

if [ -n "$BUCKET" ]; then
  echo "[entrypoint] Downloading SQLite DB from gs://${BUCKET}..."
  python -c "
from google.cloud import storage
client = storage.Client()
blob = client.bucket('${BUCKET}').blob('discover_prospecting_clean.db')
blob.download_to_filename('${DB_LOCAL}')
print('[entrypoint] DB download complete')
" || echo "[entrypoint] No existing DB in GCS — using bundled copy"

  # Background sync every 5 minutes
  _sync_loop() {
    while true; do
      sleep 300
      python -c "
from google.cloud import storage
client = storage.Client()
client.bucket('${BUCKET}').blob('discover_prospecting_clean.db').upload_from_filename('${DB_LOCAL}')
print('[sync] DB uploaded to GCS')
" || true
    done
  }
  _sync_loop &
  SYNC_PID=$!

  # Upload on shutdown
  _cleanup() {
    kill "$SYNC_PID" 2>/dev/null || true
    python -c "
from google.cloud import storage
client = storage.Client()
client.bucket('${BUCKET}').blob('discover_prospecting_clean.db').upload_from_filename('${DB_LOCAL}')
print('[shutdown] Final DB upload complete')
" || true
  }
  trap _cleanup SIGTERM SIGINT
fi

exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
