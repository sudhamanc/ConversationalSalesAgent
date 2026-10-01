#!/usr/bin/env bash
# Run the golden-dataset eval suite (agents, router, journeys) against real Gemini.
#
# Usage: scripts/eval.sh [--only LIST] [--runs N] [--record]
#   --only    comma list of tiers (agents, router, journeys) and/or agent names
#             (discovery, discovery_agent, ...). Default: agents,router,journeys
#   --runs N  repeat everything N times, resetting the eval database before each
#             run; a case passes only if it passes in every run (default 1)
#   --record  journeys only: write the streamed replies into the goldens as drafts
#             (reviewed=false) instead of scoring them
#
# Env: GOOGLE_API_KEY (billed; the free tier cannot run the suite),
#      EVAL_DATABASE_URL (default postgresql://csa:csa@localhost:5432/csa_eval),
#      EVAL_JUDGE_MODEL (default from test_config.json: gemini-2.5-flash).
# The eval database is reset to db/seed before every run; the dev DATABASE_URL is
# never used. Agents and router run in-process (catalog/serviceability services are
# reused when healthy, else started). Journeys start their own full stack with
# DEBUG=true on the eval database and refuse to run while the dev stack is up.
# Results: evals/results/<timestamp>/ (junit XML, per-agent CSV, router/journey JSON).
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() { sed -n '2,20p' "$0"; }

ONLY="agents,router,journeys"
RUNS=1
RECORD=0
while [ $# -gt 0 ]; do
  case "$1" in
    --only) [ $# -ge 2 ] || die "--only needs a value"; ONLY="$2"; shift ;;
    --only=*) ONLY="${1#--only=}" ;;
    --runs) [ $# -ge 2 ] || die "--runs needs a value"; RUNS="$2"; shift ;;
    --record) RECORD=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done
case "$RUNS" in ''|*[!0-9]*|0) die "--runs must be a positive integer" ;; esac

# ---------------------------------------------------------------------------
# Selection: tiers and agent filter
# ---------------------------------------------------------------------------
RUN_AGENTS=0; RUN_ROUTER=0; RUN_JOURNEYS=0; AGENT_FILTER=()
IFS=',' read -r -a ITEMS <<<"$ONLY"
for item in "${ITEMS[@]}"; do
  item="$(printf '%s' "$item" | tr -d '[:space:]')"
  case "$item" in
    '') ;;
    agents) RUN_AGENTS=1 ;;
    router) RUN_ROUTER=1 ;;
    journeys) RUN_JOURNEYS=1 ;;
    *) RUN_AGENTS=1; AGENT_FILTER+=("${item%_agent}") ;;
  esac
done
[ "$RECORD" = "0" ] || [ "$RUN_JOURNEYS" = "1" ] || die "--record applies to journeys; add journeys to --only"

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
load_dotenv "$REPO_ROOT/.env"
[ -x "$PYTHON" ] || die "venv python not found at $PYTHON; run scripts/setup_local.sh first"
if [ -z "${GOOGLE_API_KEY:-}" ] || [ "${GOOGLE_API_KEY}" = "replace-with-your-gemini-api-key" ]; then
  [ -n "${GOOGLE_GENAI_USE_VERTEXAI:-}" ] || die "GOOGLE_API_KEY is not set (evals call Gemini; a billed key is required)"
fi
require_env GEMINI_MODEL "Set it in .env"

if ! "$PYTHON" -c 'import google.adk.evaluation.metric_evaluator_registry, pandas, rouge_score' >/dev/null 2>&1; then
  section "Installing eval dependencies (evals/requirements.txt)"
  if command -v uv >/dev/null 2>&1; then
    run uv pip install --python "$PYTHON" -r "$REPO_ROOT/evals/requirements.txt"
  else
    run "$PYTHON" -m pip install -r "$REPO_ROOT/evals/requirements.txt"
  fi
fi

EVAL_DATABASE_URL="${EVAL_DATABASE_URL:-postgresql://csa:csa@localhost:5432/csa_eval}"
db_url_is_local "$EVAL_DATABASE_URL" || die "EVAL_DATABASE_URL must be a local database (it is reset on every run)"
[ "$EVAL_DATABASE_URL" != "${DATABASE_URL:-}" ] || die "EVAL_DATABASE_URL must differ from the dev DATABASE_URL"
export EVAL_DATABASE_URL

section "Eval database"
EVAL_DATABASE_URL="$EVAL_DATABASE_URL" "$PYTHON" - <<'PY' || die "could not create the eval database (is PostgreSQL up? scripts/db.sh up)"
import os
from urllib.parse import urlsplit, urlunsplit
import psycopg
url = os.environ["EVAL_DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
try:
    psycopg.connect(url, connect_timeout=5).close()
except psycopg.OperationalError as exc:
    if "does not exist" not in str(exc):
        raise
    parts = urlsplit(url)
    name = parts.path.lstrip("/")
    admin = urlunsplit(parts._replace(path="/postgres"))
    with psycopg.connect(admin, autocommit=True, connect_timeout=5) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    print(f"created database {name}")
PY
log_ok "eval database reachable"

STAMP="$(date +%Y%m%d-%H%M%S)"
RESULTS_ROOT="$REPO_ROOT/evals/results/$STAMP"
mkdir -p "$RESULTS_ROOT"

http_ok() { curl -fsS -o /dev/null --max-time 3 "$1" 2>/dev/null; }
port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

STARTED_TOOLS=0
STARTED_STACK=0
cleanup() {
  if [ "$STARTED_STACK" = "1" ]; then "$SCRIPTS_DIR/stop_local.sh" || true; fi
  if [ "$STARTED_TOOLS" = "1" ]; then "$SCRIPTS_DIR/stop_local.sh" --only catalog,serviceability || true; fi
}
trap cleanup EXIT

ensure_tool_services() {
  if http_ok http://127.0.0.1:8101/healthz && http_ok http://127.0.0.1:8102/healthz; then
    log_ok "reusing catalog :8101 and serviceability :8102 (read-only reference data)"
    return 0
  fi
  DATABASE_URL="$EVAL_DATABASE_URL" "$SCRIPTS_DIR/start_local.sh" --only catalog,serviceability --no-ui --skip-migrate
  STARTED_TOOLS=1
}

pytest_run() {
  # pytest_run <run dir> <label> <pytest args...>
  local dir="$1" label="$2"
  shift 2
  RUN_EVALS=1 EVAL_RESULTS_DIR="$dir" DATABASE_URL="$EVAL_DATABASE_URL" \
    "$PYTHON" -m pytest -p no:cacheprovider -q -rA --junitxml="$dir/$label.xml" "$@"
}

# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------
FAILED=0
for run_no in $(seq 1 "$RUNS"); do
  RUN_DIR="$RESULTS_ROOT/run-$run_no"
  mkdir -p "$RUN_DIR"
  section "Run $run_no/$RUNS: reset eval database to seed"
  DATABASE_URL="$EVAL_DATABASE_URL" "$SCRIPTS_DIR/db.sh" reset --yes

  if [ "$RUN_AGENTS" = "1" ] || [ "$RUN_ROUTER" = "1" ]; then
    ensure_tool_services
    targets=()
    [ "$RUN_AGENTS" = "1" ] && targets+=("$REPO_ROOT/evals/test_agents.py")
    [ "$RUN_ROUTER" = "1" ] && targets+=("$REPO_ROOT/evals/test_router.py")
    kexpr=()
    if [ "${#AGENT_FILTER[@]}" -gt 0 ]; then
      expr="$(printf ' or %s' "${AGENT_FILTER[@]}")"
      [ "$RUN_ROUTER" = "1" ] && expr="$expr or router"
      kexpr=(-k "${expr# or }")
    fi
    section "Run $run_no: agents/router"
    pytest_run "$RUN_DIR" agents-router "${targets[@]}" "${kexpr[@]}" || FAILED=1
    if [ "$STARTED_TOOLS" = "1" ]; then
      "$SCRIPTS_DIR/stop_local.sh" --only catalog,serviceability || true
      STARTED_TOOLS=0
    fi
  fi

  if [ "$RUN_JOURNEYS" = "1" ]; then
    section "Run $run_no: journeys"
    port_in_use 8000 && die "port 8000 is in use: stop the dev stack (scripts/stop_local.sh) before journey evals"
    DATABASE_URL="$EVAL_DATABASE_URL" DEBUG=true "$SCRIPTS_DIR/start_local.sh" --no-ui --skip-migrate
    STARTED_STACK=1
    EVAL_RECORD="$( [ "$RECORD" = "1" ] && echo 1 || echo 0 )" pytest_run "$RUN_DIR" journeys \
      "$REPO_ROOT/evals/test_journeys.py" || FAILED=1
    "$SCRIPTS_DIR/stop_local.sh" || true
    STARTED_STACK=0
  fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section "Summary ($RESULTS_ROOT)"
"$PYTHON" - "$RESULTS_ROOT" <<'PY' | tee "$RESULTS_ROOT/summary.txt"
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(sys.argv[1])
rows = []
for xml in sorted(root.glob("run-*/*.xml")):
    for case in ET.parse(xml).getroot().iter("testcase"):
        status = "PASS"
        if case.find("failure") is not None or case.find("error") is not None:
            status = "FAIL"
        elif case.find("skipped") is not None:
            status = "SKIP (" + (case.find("skipped").get("message") or "")[:70] + ")"
        rows.append((xml.parent.name, case.get("name"), status))
width = max((len(r[1]) for r in rows), default=10)
for run, name, status in rows:
    print(f"{run:<7} {name:<{width}}  {status}")
print(f"\n{sum(r[2] == 'PASS' for r in rows)} passed, {sum(r[2] == 'FAIL' for r in rows)} failed, "
      f"{sum(r[2].startswith('SKIP') for r in rows)} skipped")
PY
if [ "$FAILED" = "1" ]; then
  log_error "eval failures (details: pytest output above, $RESULTS_ROOT)"
  exit 1
fi
log_ok "eval suite passed"
