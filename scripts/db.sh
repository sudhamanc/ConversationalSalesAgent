#!/usr/bin/env bash
# Database operations against $DATABASE_URL (loaded from .env if not already set).
#
# Usage:
#   scripts/db.sh up [--native]                 start a local PostgreSQL 16 for DATABASE_URL, then migrate + seed
#   scripts/db.sh down                          stop the local PostgreSQL started by `up` (data is kept)
#   scripts/db.sh migrate                       apply pending migrations (db/migrations)
#   scripts/db.sh seed                          apply migrations, then seed files once (db/seed)
#   scripts/db.sh reset --yes [--allow-remote]  DROP the public schema, recreate it, migrate + seed
#
# up: an already reachable DATABASE_URL is used as is. Otherwise Docker is tried first
# (container csa-postgres, volume csa-pgdata, bound to 127.0.0.1). When Docker is not
# installed, or the postgres:16 image cannot be pulled (e.g. a proxy blocks Docker Hub),
# it falls back to Homebrew postgresql@16. --native skips Docker. If Docker is installed
# but its engine (Rancher Desktop, Docker Desktop, ...) is not running, up stops and says
# so rather than silently switching to Homebrew.
#
# reset refuses to run without --yes, and refuses any non-local database host
# (anything other than localhost / 127.0.0.1 / ::1 / a local socket) unless
# --allow-remote is also given.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() { sed -n '2,21p' "$0"; }

CMD="${1:-}"
[ -n "$CMD" ] || { usage; exit 2; }
shift
YES=0
ALLOW_REMOTE=0
NATIVE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y) YES=1 ;;
    --allow-remote) ALLOW_REMOTE=1 ;;
    --native) NATIVE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

case "$CMD" in
  up|down|migrate|seed|reset) ;;
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

PG_IMAGE="${PG_IMAGE:-postgres:16}"  # override to use an internal registry mirror
PG_CONTAINER="csa-postgres"
PG_VOLUME="csa-pgdata"
BREW_FORMULA="postgresql@16"
DB_WAIT_SECONDS="${DB_WAIT_SECONDS:-60}"
ENGINE_WAIT_SECONDS="${ENGINE_WAIT_SECONDS:-120}"

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

# ---------------------------------------------------------------------------
# up / down: local PostgreSQL lifecycle (Docker first, Homebrew fallback)
# ---------------------------------------------------------------------------
wait_for_db() {
  # wait_for_db <label> : poll DATABASE_URL until it accepts connections.
  local i
  log_info "Waiting for PostgreSQL ($1) to accept connections"
  for i in $(seq 1 "$DB_WAIT_SECONDS"); do
    db_check quiet && { log_ok "PostgreSQL ($1) is ready"; return 0; }
    sleep 1
  done
  db_check || true
  die "PostgreSQL ($1) did not accept connections within ${DB_WAIT_SECONDS}s"
}

port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

container_engine_app() {
  # Name of a desktop container engine installed on this machine ("" if none found).
  local app
  for app in "Rancher Desktop" "Docker" "OrbStack" "Podman Desktop"; do
    [ -d "/Applications/$app.app" ] && { printf '%s' "$app"; return 0; }
  done
  command -v colima >/dev/null 2>&1 && { printf 'colima'; return 0; }
  return 0
}

engine_running() { docker info >/dev/null 2>&1; }

ensure_engine() {
  # Returns when the Docker engine answers; dies with instructions otherwise.
  # A desktop app that is still booting is waited for (ENGINE_WAIT_SECONDS).
  local app i
  engine_running && return 0
  app="$(container_engine_app)"
  if [ -n "$app" ] && [ "$app" != "colima" ] && pgrep -f "/Applications/$app.app/" >/dev/null 2>&1; then
    log_info "$app is running but its Docker engine is not ready yet; waiting up to ${ENGINE_WAIT_SECONDS}s"
    for i in $(seq 1 "$ENGINE_WAIT_SECONDS"); do
      engine_running && { log_ok "Docker engine is ready"; return 0; }
      sleep 1
    done
    die "$app is running but 'docker info' still fails after ${ENGINE_WAIT_SECONDS}s.
  Check that $app finished starting and that its engine is dockerd/moby, and that
  'docker context ls' marks its context as current (e.g. docker context use rancher-desktop)."
  fi
  case "$app" in
    colima) die "Docker is installed but its engine is not running. Start it with: colima start
  then re-run scripts/db.sh up (or use scripts/db.sh up --native for Homebrew PostgreSQL)." ;;
    '') die "The docker command is installed but its engine is not running and no desktop engine was found.
  Start your Docker engine, then re-run scripts/db.sh up (or use scripts/db.sh up --native)." ;;
    *) die "Docker is installed but its engine is not running. Start $app:
    open -a \"$app\"
  wait until it reports it is running, then re-run scripts/db.sh up
  (or use scripts/db.sh up --native for Homebrew PostgreSQL)." ;;
  esac
}

docker_up() {
  # Returns 0 when the container is running, 2 when the image cannot be pulled
  # (caller falls back to Homebrew). Other failures are fatal.
  local state
  state="$(docker container inspect -f '{{.State.Status}}' "$PG_CONTAINER" 2>/dev/null || true)"
  if [ "$state" = "running" ]; then
    log_ok "Container $PG_CONTAINER is already running"
    return 0
  fi
  if [ -n "$state" ]; then
    run docker start "$PG_CONTAINER" >/dev/null
    return 0
  fi
  if ! docker image inspect "$PG_IMAGE" >/dev/null 2>&1; then
    log_info "Pulling $PG_IMAGE"
    if ! run docker pull "$PG_IMAGE"; then
      log_warn "Could not pull $PG_IMAGE from the registry (network or proxy blocks the Docker engine)"
      return 2
    fi
  fi
  port_in_use "$DB_PORT_PART" && die "port $DB_PORT_PART is in use by something that does not accept DATABASE_URL
  (see the error above). Stop it or change the port in DATABASE_URL, then re-run."
  run_redacted "docker run -d --name $PG_CONTAINER -p 127.0.0.1:$DB_PORT_PART:5432 -v $PG_VOLUME:/var/lib/postgresql/data $PG_IMAGE" \
    docker run -d --name "$PG_CONTAINER" \
      -e POSTGRES_USER="$DB_USER_PART" -e POSTGRES_PASSWORD="$DB_PASSWORD_PART" -e POSTGRES_DB="$DB_NAME_PART" \
      -p "127.0.0.1:$DB_PORT_PART:5432" -v "$PG_VOLUME:/var/lib/postgresql/data" \
      "$PG_IMAGE" >/dev/null
}

brew_up() {
  local prefix psql_bin i
  if ! command -v brew >/dev/null 2>&1; then
    case "$(uname -s)" in
      Darwin) die "Homebrew is not installed (https://brew.sh). Install it, or install PostgreSQL 16 yourself
  and make DATABASE_URL point at it." ;;
      *) die "No Docker image and no Homebrew. Install PostgreSQL 16 with your package manager
  (e.g. sudo apt-get install postgresql-16), create the role and database from DATABASE_URL, then re-run." ;;
    esac
  fi
  [ "$DB_PORT_PART" = "5432" ] || die "Homebrew PostgreSQL listens on 5432 but DATABASE_URL uses port $DB_PORT_PART"
  if ! brew list --versions "$BREW_FORMULA" >/dev/null 2>&1; then
    run brew install "$BREW_FORMULA"
  fi
  prefix="$(brew --prefix "$BREW_FORMULA")"
  psql_bin="$prefix/bin/psql"
  if ! "$prefix/bin/pg_isready" -h localhost -p 5432 -q 2>/dev/null; then
    port_in_use 5432 && die "port 5432 is in use by something that does not accept DATABASE_URL. Stop it, then re-run."
    run brew services start "$BREW_FORMULA"
    for i in $(seq 1 "$DB_WAIT_SECONDS"); do
      "$prefix/bin/pg_isready" -h localhost -p 5432 -q 2>/dev/null && break
      sleep 1
    done
  fi
  # Homebrew's cluster has a superuser named after the OS user; create the app role and database.
  log_info "Ensuring role '$DB_USER_PART' and database '$DB_NAME_PART' exist"
  "$psql_bin" -h localhost -p 5432 -d postgres -X -q -v ON_ERROR_STOP=1 \
    -v role="$DB_USER_PART" -v db="$DB_NAME_PART" -v pw="$DB_PASSWORD_PART" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'role', :'pw')
  WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'db', :'role')
  WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db') \gexec
SQL
}

db_up() {
  if db_check quiet; then
    log_ok "PostgreSQL at DATABASE_URL is already reachable; using it"
    return 0
  fi
  db_url_is_local "$DATABASE_URL" || {
    db_check || true
    die "DATABASE_URL points at a non-local host; up only starts local databases. Fix the connection above."
  }
  db_url_parts "$DATABASE_URL"
  if port_in_use "$DB_PORT_PART"; then
    log_warn "Port $DB_PORT_PART is open but DATABASE_URL does not connect:"
    db_check || true
  fi

  if [ "$NATIVE" = "1" ]; then
    log_info "--native given: using Homebrew $BREW_FORMULA"
  elif ! command -v docker >/dev/null 2>&1; then
    log_info "Docker not installed: using Homebrew $BREW_FORMULA"
    NATIVE=1
  else
    ensure_engine
    local rc=0
    docker_up || rc=$?
    if [ "$rc" = "2" ]; then
      log_warn "Falling back to Homebrew $BREW_FORMULA"
      NATIVE=1
    elif [ "$rc" != "0" ]; then
      die "could not start container $PG_CONTAINER"
    fi
  fi

  if [ "$NATIVE" = "1" ]; then
    brew_up
    wait_for_db "Homebrew $BREW_FORMULA"
  else
    wait_for_db "Docker container $PG_CONTAINER"
  fi
}

db_down() {
  local stopped=0
  if command -v docker >/dev/null 2>&1 && engine_running \
    && [ "$(docker container inspect -f '{{.State.Status}}' "$PG_CONTAINER" 2>/dev/null)" = "running" ]; then
    run docker stop "$PG_CONTAINER" >/dev/null
    log_ok "Stopped container $PG_CONTAINER (data kept in volume $PG_VOLUME)"
    stopped=1
  fi
  if command -v brew >/dev/null 2>&1 && brew services list 2>/dev/null | grep -Eq "^$BREW_FORMULA[[:space:]]+started"; then
    run brew services stop "$BREW_FORMULA"
    log_ok "Stopped Homebrew $BREW_FORMULA (data kept)"
    stopped=1
  fi
  [ "$stopped" = "1" ] || log_info "No local PostgreSQL started by db.sh up is running"
}

case "$CMD" in
  up)
    db_up
    migrate --seed
    ;;
  down) db_down ;;
  migrate) migrate ;;
  seed) migrate --seed ;;
  reset)
    reset_schema
    migrate --seed
    ;;
esac
log_ok "db.sh $CMD complete"
