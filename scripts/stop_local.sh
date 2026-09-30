#!/usr/bin/env bash
# Stop processes started by scripts/start_local.sh, using ONLY the PIDs it recorded
# in logs/pids/<name>.pid. No pattern-based or port-wide killing.
#
# Usage: scripts/stop_local.sh [--only name[,name...]]   (names from services.conf, plus "ui")
# Each process gets SIGTERM, then SIGKILL after STOP_TIMEOUT seconds (default 10).
# A PID is only signalled when its command line still looks like the service we
# started (uvicorn / vite), which protects against PID reuse.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --only) [ $# -ge 2 ] || die "--only needs a value"; ONLY="$2"; shift ;;
    --only=*) ONLY="${1#--only=}" ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done
STOP_TIMEOUT="${STOP_TIMEOUT:-10}"

services_load
# Stop in reverse start order: ui, gateway, agents, tools.
ORDER=(ui)
for (( k=${#SVC_NAME[@]}-1; k>=0; k-- )); do ORDER+=("${SVC_NAME[$k]}"); done

TARGETS=()
if [ -z "$ONLY" ]; then
  TARGETS=("${ORDER[@]}")
else
  IFS=',' read -r -a requested <<<"$ONLY"
  for n in "${requested[@]}"; do
    [ "$n" = "ui" ] || svc_index "$n" >/dev/null || die "unknown service '$n'"
  done
  for o in "${ORDER[@]}"; do
    for n in "${requested[@]}"; do
      if [ "$n" = "$o" ]; then TARGETS+=("$o"); break; fi
    done
  done
fi

expected_pattern() {
  if [ "$1" = "ui" ]; then printf 'vite'; else printf 'uvicorn'; fi
}

stop_one() {
  local name="$1" pidfile="$PID_DIR/$1.pid" pid cmdline waited=0
  [ -f "$pidfile" ] || return 0
  pid="$(tr -dc '0-9' <"$pidfile")"
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    log_info "$name: not running (stale pid file removed)"
    rm -f "$pidfile"
    return 0
  fi
  cmdline="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  case "$cmdline" in
    *"$(expected_pattern "$name")"*) ;;
    *)
      log_warn "$name: PID $pid is now '${cmdline:-?}', not ours; not killing (pid file removed)"
      rm -f "$pidfile"
      return 0
      ;;
  esac
  kill -TERM "$pid" 2>/dev/null || true
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$waited" -ge "$STOP_TIMEOUT" ]; then
      log_warn "$name: PID $pid did not exit after ${STOP_TIMEOUT}s; sending SIGKILL"
      kill -KILL "$pid" 2>/dev/null || true
      break
    fi
    sleep 1
    waited=$((waited + 1))
  done
  rm -f "$pidfile"
  log_ok "stopped $name (PID $pid)"
}

if [ ! -d "$PID_DIR" ]; then
  log_info "nothing to stop ($PID_DIR does not exist)"
  exit 0
fi
for name in "${TARGETS[@]}"; do
  stop_one "$name"
done
