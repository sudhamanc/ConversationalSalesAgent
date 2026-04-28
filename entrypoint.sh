#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# ChromaDB: regenerate product embeddings if index was not baked into image
# ---------------------------------------------------------------------------
EMBEDDINGS_DIR="/app/ProductAgent/data/embeddings"
if [ ! -f "$EMBEDDINGS_DIR/chroma.sqlite3" ]; then
  echo "[entrypoint] ChromaDB index not found — running ingest (native amd64, ~30s)..."
  python /app/ProductAgent/scripts/ingest_knowledge.py
  echo "[entrypoint] ChromaDB ingest complete."
else
  echo "[entrypoint] ChromaDB index found — skipping ingest."
fi

# ---------------------------------------------------------------------------
# Unified DB: all agents share a single SQLite file
# ---------------------------------------------------------------------------
DB_LOCAL="/app/SuperAgent/data/sales_agent.db"
GCS_BLOB="sales_agent.db"
BUCKET="${GCS_DATA_BUCKET:-}"

# Ensure the data directory exists
mkdir -p "$(dirname "$DB_LOCAL")"

# Export so every Python process (config.py, agents) sees the absolute path
export SALES_AGENT_DB_PATH="$DB_LOCAL"

if [ -n "$BUCKET" ]; then
  echo "[entrypoint] Downloading unified DB from gs://${BUCKET}/${GCS_BLOB}..."
  python -c "
from google.cloud import storage
client = storage.Client()
blob = client.bucket('${BUCKET}').blob('${GCS_BLOB}')
blob.download_to_filename('${DB_LOCAL}')
print('[entrypoint] Unified DB download complete')
" || echo "[entrypoint] No existing DB in GCS — init_db() will create schema on startup"

  # Background sync every 5 minutes
  _sync_loop() {
    while true; do
      sleep 300
      python -c "
from google.cloud import storage
import subprocess
subprocess.run(['sqlite3', '${DB_LOCAL}', 'PRAGMA wal_checkpoint(TRUNCATE);'], check=False)
client = storage.Client()
client.bucket('${BUCKET}').blob('${GCS_BLOB}').upload_from_filename('${DB_LOCAL}')
print('[sync] Unified DB uploaded to GCS')
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
import subprocess
subprocess.run(['sqlite3', '${DB_LOCAL}', 'PRAGMA wal_checkpoint(TRUNCATE);'], check=False)
client = storage.Client()
client.bucket('${BUCKET}').blob('${GCS_BLOB}').upload_from_filename('${DB_LOCAL}')
print('[shutdown] Final unified DB upload complete')
" || true
  }
  trap _cleanup SIGTERM SIGINT
fi

exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
