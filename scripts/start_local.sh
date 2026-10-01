#!/usr/bin/env bash
# Start the whole system as native processes against a PostgreSQL database.
#
# Usage: scripts/start_local.sh [--only name[,name...]] [--no-ui] [--skip-migrate]
#   --only          start only these services (names from scripts/services.conf)
#   --no-ui         do not start the Vite dev server (UI on :3000)
#   --skip-migrate  do not run migrations + seed before starting
#
# Order: migrations + seed, tool services, agents, gateway, Vite dev server.
# Env: .env at the repo root is loaded without overriding variables already set.
# Required: DATABASE_URL (reachable; scripts/db.sh up starts a local one), GEMINI_MODEL. SESSION_SECRET_KEY is generated for this
# run (with a warning) when missing.
# Logs: logs/<name>.log   PIDs: logs/pids/<name>.pid   Stop: scripts/stop_local.sh
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() { sed -n '2,14p' "$0"; }

ONLY=""
START_UI=1
MIGRATE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --only) [ $# -ge 2 ] || die "--only needs a value"; ONLY="$2"; shift ;;
    --only=*) ONLY="${1#--only=}" ;;
    --no-ui) START_UI=0 ;;
    --skip-migrate) MIGRATE=0 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done

HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-60}"
BIND_HOST="${LOCAL_BIND_HOST:-127.0.0.1}"
UI_PORT=3000

services_load
select_services "$ONLY"
if [ -n "$ONLY" ] && ! is_selected gateway; then
  START_UI=0
fi

# ---------------------------------------------------------------------------
# Configuration checks (nothing is started before these pass)
# ---------------------------------------------------------------------------
load_dotenv "$REPO_ROOT/.env"
require_env DATABASE_URL "Set it in .env (cp .env.example .env) or export it, e.g.
  export DATABASE_URL=postgresql://csa:csa@localhost:5432/csa"
require_env GEMINI_MODEL "Set it in .env or export it, e.g. export GEMINI_MODEL=gemini-3-flash-preview"
if [ -z "${GOOGLE_API_KEY:-}" ] && [ -z "${GOOGLE_GENAI_USE_VERTEXAI:-}" ]; then
  log_warn "GOOGLE_API_KEY is not set; LLM calls will fail unless Vertex AI credentials are configured"
fi
if [ -z "${SESSION_SECRET_KEY:-}" ]; then
  SESSION_SECRET_KEY="$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(48))' 2>/dev/null || openssl rand -base64 48 | tr -d '\n')"
  export SESSION_SECRET_KEY
  log_warn "SESSION_SECRET_KEY not set; generated an ephemeral key for this run (sessions end on restart). Set it in .env to persist sessions."
fi
[ -x "$PYTHON" ] || die "venv python not found at $PYTHON; run scripts/setup_local.sh first"
if ! db_check; then
  die "PostgreSQL at DATABASE_URL is not reachable (error above).
  Start a local one with: scripts/db.sh up   (Docker, or Homebrew if Docker Hub is unreachable)"
fi
CLIENT_DIR="$REPO_ROOT/SuperAgent/client"
if [ "$START_UI" = "1" ] && [ ! -x "$CLIENT_DIR/node_modules/.bin/vite" ]; then
  die "client dependencies missing ($CLIENT_DIR/node_modules); run scripts/setup_local.sh or use --no-ui"
fi

mkdir -p "$LOG_DIR" "$PID_DIR"

pid_alive() { [ -n "$1" ] && kill -0 "$1" 2>/dev/null; }
port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

http_ok() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS -o /dev/null --max-time 3 "$1" 2>/dev/null
  else
    "$PYTHON" -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=3)' "$1" >/dev/null 2>&1
  fi
}

check_free() {
  local name="$1" port="$2" pidfile="$PID_DIR/$1.pid"
  if [ -f "$pidfile" ] && pid_alive "$(cat "$pidfile" 2>/dev/null || true)"; then
    die "$name is already running (PID $(cat "$pidfile")). Run scripts/stop_local.sh first."
  fi
  rm -f "$pidfile"
  if port_in_use "$port"; then
    die "port $port (for $name) is already in use by another process; free it first (not killed automatically)"
  fi
}

for name in "${SELECTED[@]}"; do
  i="$(svc_index "$name")"
  check_free "$name" "${SVC_PORT[$i]}"
  [ -d "$REPO_ROOT/${SVC_DIR[$i]}" ] || die "$name: directory ${SVC_DIR[$i]} not found"
done
[ "$START_UI" = "0" ] || check_free ui "$UI_PORT"

# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------
export DB_DIR="${DB_DIR:-$REPO_ROOT/db}"
if [ "$MIGRATE" = "1" ]; then
  section "Migrations + seed"
  (cd "$REPO_ROOT" && "$PYTHON" -m sales_common.migrate --seed) \
    || die "migrations failed; check DATABASE_URL and that PostgreSQL 16 is running"
fi

# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------
STARTED=()

stop_started() {
  [ "${#STARTED[@]}" -gt 0 ] || return 0
  local list
  list="$(IFS=,; printf '%s' "${STARTED[*]}")"
  log_warn "Stopping services started by this run: $list"
  "$SCRIPTS_DIR/stop_local.sh" --only "$list" || true
}

on_interrupt() {
  trap - INT TERM
  log_warn "Interrupted"
  stop_started
  exit 130
}
trap on_interrupt INT TERM

fail_service() {
  local name="$1" reason="$2" log="$LOG_DIR/$1.log"
  log_error "$name $reason"
  if [ -f "$log" ]; then
    printf -- '----- last 20 lines of %s -----\n' "$log" >&2
    tail -n 20 "$log" >&2 || true
    printf -- '-----\n' >&2
  fi
  trap - INT TERM
  stop_started
  exit 1
}

start_process() {
  # start_process <name> <workdir> <env assignments...> -- <command...>
  local name="$1" workdir="$2" log="$LOG_DIR/$1.log" envs=()
  shift 2
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do envs+=("$1"); shift; done
  shift
  : >"$log"
  (cd "$workdir" && exec env "${envs[@]}" "$@") >>"$log" 2>&1 </dev/null &
  local pid=$!
  printf '%s\n' "$pid" >"$PID_DIR/$name.pid"
  STARTED+=("$name")
  log_info "started $name (PID $pid) -> logs/$name.log"
}

start_service() {
  local name="$1" i port kind envs=() dep var tool ti a
  i="$(svc_index "$name")"
  port="${SVC_PORT[$i]}"
  kind="${SVC_KIND[$i]}"
  envs=(PYTHONUNBUFFERED=1 "PORT=$port" "SERVICE_AUTH=${SERVICE_AUTH:-none}" "DB_DIR=$DB_DIR")
  case "$kind" in
    agent)
      envs+=("PUBLIC_URL=http://127.0.0.1:$port")
      if [ -n "${SVC_MCP[$i]}" ]; then
        IFS=',' read -r -a deps <<<"${SVC_MCP[$i]}"
        for dep in "${deps[@]}"; do
          var="${dep%%=*}"; tool="${dep#*=}"
          ti="$(svc_index "$tool")" || die "services.conf: $name depends on unknown tool '$tool'"
          envs+=("$var=http://127.0.0.1:${SVC_PORT[$ti]}/mcp/")
        done
      fi
      ;;
    gateway)
      envs+=(RUN_MIGRATIONS=false "SESSION_SECRET_KEY=$SESSION_SECRET_KEY"
        "ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:$UI_PORT,http://127.0.0.1:$UI_PORT,http://localhost:8000}")
      for a in "${!SVC_NAME[@]}"; do
        [ "${SVC_KIND[$a]}" = "agent" ] || continue
        envs+=("$(a2a_env_var "${SVC_A2A[$a]}")=http://127.0.0.1:${SVC_PORT[$a]}")
      done
      ;;
  esac
  start_process "$name" "$(svc_workdir "$name")" "${envs[@]}" -- \
    "$PYTHON" -m uvicorn "${SVC_MODULE[$i]}" --host "$BIND_HOST" --port "$port"
}

wait_healthy() {
  local name="$1" url="$2" pid deadline
  pid="$(cat "$PID_DIR/$name.pid")"
  deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
  while :; do
    if ! pid_alive "$pid"; then
      fail_service "$name" "exited before becoming healthy ($url)"
    fi
    if http_ok "$url"; then
      log_ok "$name healthy ($url)"
      return 0
    fi
    if [ "$(date +%s)" -ge "$deadline" ]; then
      fail_service "$name" "did not become healthy within ${HEALTH_TIMEOUT}s ($url)"
    fi
    sleep 1
  done
}

start_tier() {
  local kind="$1" names=() n i
  while IFS= read -r n; do [ -n "$n" ] && names+=("$n"); done < <(svc_names_of_kind "$kind" "${SELECTED[@]}")
  [ "${#names[@]}" -gt 0 ] || return 0
  section "Starting ${kind} services: ${names[*]}"
  for n in "${names[@]}"; do start_service "$n"; done
  for n in "${names[@]}"; do
    i="$(svc_index "$n")"
    wait_healthy "$n" "http://127.0.0.1:${SVC_PORT[$i]}$(svc_health_path "$n")"
  done
}

start_tier tool
start_tier agent
start_tier gateway

if [ "$START_UI" = "1" ]; then
  section "Starting UI (Vite dev server)"
  start_process ui "$CLIENT_DIR" "BROWSER=none" -- "$CLIENT_DIR/node_modules/.bin/vite" --port "$UI_PORT" --strictPort
  wait_healthy ui "http://localhost:$UI_PORT/"
fi

trap - INT TERM

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section "Running"
printf '%-21s %-8s %-34s %-8s %s\n' SERVICE KIND URL PID LOG
for name in "${SELECTED[@]}"; do
  i="$(svc_index "$name")"
  printf '%-21s %-8s %-34s %-8s %s\n' "$name" "${SVC_KIND[$i]}" \
    "http://127.0.0.1:${SVC_PORT[$i]}" "$(cat "$PID_DIR/$name.pid")" "logs/$name.log"
done
if [ "$START_UI" = "1" ]; then
  printf '%-21s %-8s %-34s %-8s %s\n' ui vite "http://localhost:$UI_PORT" "$(cat "$PID_DIR/ui.pid")" "logs/ui.log"
fi
printf '\nOpen %s   Stop: scripts/stop_local.sh   E2E: venv/bin/python scripts/e2e_test.py\n' \
  "$([ "$START_UI" = "1" ] && echo "http://localhost:$UI_PORT" || echo "http://127.0.0.1:8000")"
