#!/usr/bin/env bash
# Database operations against $DATABASE_URL (loaded from .env if not already set).
#
# Usage:
#   scripts/db.sh migrate                       apply pending migrations (db/migrations)
#   scripts/db.sh seed                          apply migrations, then seed files once (db/seed)
#   scripts/db.sh reset --yes [--allow-remote]  DROP the public schema, recreate it, migrate + seed
#
# reset refuses to run without --yes, and refuses any non-local database host
# (anything other than localhost / 127.0.0.1 / ::1 / a local socket) unless
# --allow-remote is also given.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() { sed -n '2,12p' "$0"; }

CMD="${1:-}"
[ -n "$CMD" ] || { usage; exit 2; }
shift
YES=0
ALLOW_REMOTE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y) YES=1 ;;
    --allow-remote) ALLOW_REMOTE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

case "$CMD" in
  migrate|seed|reset) ;;
  -h|--help|help) usage; exit 0 ;;
  *) usage; die "unknown command: $CMD" ;;
esac

# Guard the destructive command before touching anything else.
if [ "$CMD" = "reset" ] && [ "$YES" != "1" ]; then
  die "reset drops every table in the database. Re-run with --yes to confirm: scripts/db.sh reset --yes"
fi

load_dotenv "$REPO_ROOT/.env"
require_env DATABASE_URL "Set it in .env (see .env.example), e.g. DATABASE_URL=postgresql://csa:csa@localhost:5432/csa"
[ -x "$PYTHON" ] || die "venv python not found at $PYTHON; run scripts/setup_local.sh first"
export DB_DIR="${DB_DIR:-$REPO_ROOT/db}"
[ -d "$DB_DIR/migrations" ] || die "DB_DIR=$DB_DIR has no migrations/ directory"

migrate() {
  if [ "${1:-}" = "--seed" ]; then
    log_info "Applying migrations and seed data from $DB_DIR"
  else
    log_info "Applying migrations from $DB_DIR"
  fi
  (cd "$REPO_ROOT" && "$PYTHON" -m sales_common.migrate "$@")
}

reset_schema() {
  local host libpq_url
  host="$(db_url_host "$DATABASE_URL")"
  if ! db_url_is_local "$DATABASE_URL"; then
    if [ "$ALLOW_REMOTE" != "1" ]; then
      die "refusing to reset non-local database host '${host}'. Add --allow-remote if you really mean it."
    fi
    log_warn "Resetting REMOTE database host '${host}' (--allow-remote given)"
  fi
  log_warn "Dropping and recreating schema 'public' on host '${host:-local socket}'"
  libpq_url="$DATABASE_URL"
  case "$libpq_url" in postgresql+*://*) libpq_url="postgresql://${libpq_url#*://}" ;; esac
  local sql="DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
  if command -v psql >/dev/null 2>&1; then
    psql "$libpq_url" -X -q -v ON_ERROR_STOP=1 -c "$sql"
  else
    DB_RESET_SQL="$sql" "$PYTHON" - <<'PY'
import os
import psycopg
from sales_common.db import database_url
with psycopg.connect(database_url(), autocommit=True) as conn:
    conn.execute(os.environ["DB_RESET_SQL"])
PY
  fi
  log_ok "Schema public recreated"
}

case "$CMD" in
  migrate) migrate ;;
  seed) migrate --seed ;;
  reset)
    reset_schema
    migrate --seed
    ;;
esac
log_ok "db.sh $CMD complete"
