# shellcheck shell=bash
# Globals defined here (SVC_*, SA_*, IMAGE_BASE, ...) are consumed by the sourcing scripts.
# shellcheck disable=SC2034
# Shared helpers for the operations scripts in scripts/.
#
# Source it from a script:   source "$(dirname "$0")/lib.sh"
# Quick check:               bash -c 'source scripts/lib.sh; list_services'
#
# Kept compatible with bash 3.2 (macOS default): no associative arrays, no mapfile.

if [ -n "${_CSA_LIB_LOADED:-}" ]; then
  return 0
fi
_CSA_LIB_LOADED=1

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPTS_DIR/.." && pwd)"
SERVICES_CONF="${SERVICES_CONF:-$SCRIPTS_DIR/services.conf}"
LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
PID_DIR="${PID_DIR:-$LOG_DIR/pids}"
VENV_DIR="${VENV_DIR:-$REPO_ROOT/venv}"
PYTHON="${PYTHON:-$VENV_DIR/bin/python}"
DRY_RUN="${DRY_RUN:-0}"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
if [ -t 2 ] && [ -z "${NO_COLOR:-}" ]; then
  _C_RED=$'\033[31m'; _C_GRN=$'\033[32m'; _C_YEL=$'\033[33m'; _C_BLU=$'\033[34m'; _C_OFF=$'\033[0m'
else
  _C_RED=""; _C_GRN=""; _C_YEL=""; _C_BLU=""; _C_OFF=""
fi

_log_prefix() { printf '[%s]' "${LOG_TAG:-$(basename "$0" .sh)}"; }
log_info()  { printf '%s %s\n' "$(_log_prefix)" "$*" >&2; }
log_ok()    { printf '%s %sOK%s %s\n' "$(_log_prefix)" "$_C_GRN" "$_C_OFF" "$*" >&2; }
log_warn()  { printf '%s %sWARN%s %s\n' "$(_log_prefix)" "$_C_YEL" "$_C_OFF" "$*" >&2; }
log_error() { printf '%s %sERROR%s %s\n' "$(_log_prefix)" "$_C_RED" "$_C_OFF" "$*" >&2; }
section()   { printf '\n%s== %s ==%s\n' "$_C_BLU" "$*" "$_C_OFF" >&2; }
die()       { log_error "$*"; exit 1; }

# ---------------------------------------------------------------------------
# Preconditions
# ---------------------------------------------------------------------------
require_cmd() {
  # require_cmd <command> [install hint]
  command -v "$1" >/dev/null 2>&1 || die "Required command '$1' not found.${2:+ $2}"
}

require_env() {
  # require_env <VAR> [how to set it]
  local name="$1" value
  value="$(env_value "$name")"
  [ -n "$value" ] || die "$name is not set.${2:+ $2}"
}

env_value() {
  # Print the value of the variable named $1 (empty when unset). Name is validated.
  case "$1" in
    ''|[0-9]*|*[!A-Za-z0-9_]*) die "invalid variable name: '$1'" ;;
  esac
  eval "printf '%s' \"\${$1:-}\""
}

env_is_set() {
  case "$1" in
    ''|[0-9]*|*[!A-Za-z0-9_]*) return 1 ;;
  esac
  eval "[ -n \"\${$1+x}\" ]"
}

is_dry_run() { [ "${DRY_RUN:-0}" = "1" ]; }

# ---------------------------------------------------------------------------
# Command runner (honors DRY_RUN=1). Commands are printed, never their stdin.
# ---------------------------------------------------------------------------
_quote_cmd() {
  local out="" arg
  for arg in "$@"; do
    out="$out $(printf '%q' "$arg")"
  done
  printf '%s' "${out# }"
}

run() {
  if is_dry_run; then
    printf '[dry-run] %s\n' "$(_quote_cmd "$@")"
    return 0
  fi
  printf '+ %s\n' "$(_quote_cmd "$@")" >&2
  "$@"
}

run_redacted() {
  # run_redacted "<display text without secrets>" <command...>
  # For commands whose argv carries a secret: only the display text is printed.
  local display="$1"
  shift
  if is_dry_run; then
    printf '[dry-run] %s\n' "$display"
    return 0
  fi
  printf '+ %s\n' "$display" >&2
  "$@"
}

run_stdin() {
  # run_stdin <command...> : like run, but forwards stdin (e.g. a secret) without printing it.
  if is_dry_run; then
    cat >/dev/null
    printf '[dry-run] %s <<< [redacted]\n' "$(_quote_cmd "$@")"
    return 0
  fi
  printf '+ %s <<< [redacted]\n' "$(_quote_cmd "$@")" >&2
  "$@"
}

# ---------------------------------------------------------------------------
# .env loading (KEY=VALUE lines; never overrides variables already set)
# ---------------------------------------------------------------------------
load_dotenv() {
  local file="${1:-$REPO_ROOT/.env}" line key value
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in ''|'#'*) continue ;; esac
    line="${line#export }"
    case "$line" in *=*) ;; *) continue ;; esac
    key="${line%%=*}"
    value="${line#*=}"
    key="$(printf '%s' "$key" | tr -d '[:space:]')"
    case "$key" in ''|[0-9]*|*[!A-Za-z0-9_]*) continue ;; esac
    if [[ "$value" =~ ^\"(.*)\"[[:space:]]*$ ]] || [[ "$value" =~ ^\'(.*)\'[[:space:]]*$ ]]; then
      value="${BASH_REMATCH[1]}"
    else
      value="${value%%[[:space:]]#*}"
      value="${value%"${value##*[![:space:]]}"}"
    fi
    if ! env_is_set "$key"; then
      export "$key=$value"
    fi
  done <"$file"
}

# ---------------------------------------------------------------------------
# Service manifest
# ---------------------------------------------------------------------------
SVC_NAME=(); SVC_DIR=(); SVC_MODULE=(); SVC_PORT=(); SVC_KIND=(); SVC_CLOUD=(); SVC_A2A=(); SVC_MCP=()

services_load() {
  [ -f "$SERVICES_CONF" ] || die "service manifest not found: $SERVICES_CONF"
  SVC_NAME=(); SVC_DIR=(); SVC_MODULE=(); SVC_PORT=(); SVC_KIND=(); SVC_CLOUD=(); SVC_A2A=(); SVC_MCP=()
  local name dir module port kind cloud a2a mcp
  while IFS='|' read -r name dir module port kind cloud a2a mcp || [ -n "$name" ]; do
    case "$name" in ''|'#'*) continue ;; esac
    case "$kind" in tool|agent|gateway) ;; *) die "services.conf: bad kind '$kind' for $name" ;; esac
    SVC_NAME+=("$name"); SVC_DIR+=("$dir"); SVC_MODULE+=("$module"); SVC_PORT+=("$port")
    SVC_KIND+=("$kind"); SVC_CLOUD+=("$cloud"); SVC_A2A+=("$a2a"); SVC_MCP+=("${mcp:-}")
  done <"$SERVICES_CONF"
  [ "${#SVC_NAME[@]}" -gt 0 ] || die "services.conf lists no services"
}

list_services() {
  # One row per service: name dir module port kind cloud_run_name a2a_name mcp_deps
  [ "${#SVC_NAME[@]}" -gt 0 ] || services_load
  local i
  for i in "${!SVC_NAME[@]}"; do
    printf '%-21s %-27s %-42s %-5s %-8s %-24s %-29s %s\n' "${SVC_NAME[$i]}" "${SVC_DIR[$i]}" \
      "${SVC_MODULE[$i]}" "${SVC_PORT[$i]}" "${SVC_KIND[$i]}" "${SVC_CLOUD[$i]}" "${SVC_A2A[$i]:--}" "${SVC_MCP[$i]:--}"
  done
}

svc_index() {
  # svc_index <name> -> prints the manifest index; returns 1 if unknown
  local i
  for i in "${!SVC_NAME[@]}"; do
    if [ "${SVC_NAME[$i]}" = "$1" ]; then
      printf '%s' "$i"
      return 0
    fi
  done
  return 1
}

svc_names_of_kind() {
  # svc_names_of_kind <kind> [name...] -> names of that kind, manifest order, optionally
  # restricted to the given names
  local kind="$1" i n
  shift
  for i in "${!SVC_NAME[@]}"; do
    [ "${SVC_KIND[$i]}" = "$kind" ] || continue
    if [ "$#" -eq 0 ]; then
      printf '%s\n' "${SVC_NAME[$i]}"
    else
      for n in "$@"; do
        if [ "$n" = "${SVC_NAME[$i]}" ]; then
          printf '%s\n' "$n"
        fi
      done
    fi
  done
}

SELECTED=()
select_services() {
  # select_services "<comma list or empty>" -> SELECTED=(names...) in dependency order
  # (tools, agents, gateway, i.e. manifest order). Unknown names are fatal.
  local only="$1" requested=() n i
  SELECTED=()
  if [ -z "$only" ]; then
    SELECTED=("${SVC_NAME[@]}")
    return 0
  fi
  IFS=',' read -r -a requested <<<"$only"
  for n in "${requested[@]}"; do
    n="$(printf '%s' "$n" | tr -d '[:space:]')"
    [ -n "$n" ] || continue
    svc_index "$n" >/dev/null || die "unknown service '$n' (known: ${SVC_NAME[*]})"
  done
  for i in "${!SVC_NAME[@]}"; do
    for n in "${requested[@]}"; do
      n="$(printf '%s' "$n" | tr -d '[:space:]')"
      if [ "$n" = "${SVC_NAME[$i]}" ]; then
        SELECTED+=("$n")
        break
      fi
    done
  done
  [ "${#SELECTED[@]}" -gt 0 ] || die "--only selected no services"
}

is_selected() {
  local n
  for n in "${SELECTED[@]}"; do
    [ "$n" = "$1" ] && return 0
  done
  return 1
}

svc_workdir() {
  # Directory uvicorn runs from (absolute).
  local i
  i="$(svc_index "$1")" || die "unknown service '$1'"
  if [ "${SVC_KIND[$i]}" = "gateway" ]; then
    printf '%s/%s/server' "$REPO_ROOT" "${SVC_DIR[$i]}"
  else
    printf '%s/%s' "$REPO_ROOT" "${SVC_DIR[$i]}"
  fi
}

svc_health_path() {
  local i
  i="$(svc_index "$1")" || die "unknown service '$1'"
  if [ "${SVC_KIND[$i]}" = "gateway" ]; then printf '/health'; else printf '/healthz'; fi
}

a2a_env_var() {
  # a2a_env_var discovery_agent -> AGENT_URL_DISCOVERY_AGENT
  printf 'AGENT_URL_%s' "$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"
}

# ---------------------------------------------------------------------------
# Database URL helpers
# ---------------------------------------------------------------------------
db_url_host() {
  # Print the host of a libpq URL ("" for a default unix socket). Uses Python for robust parsing.
  local py="$PYTHON"
  [ -x "$py" ] || py="$(command -v python3 || true)"
  [ -n "$py" ] || die "python3 is required to parse DATABASE_URL"
  DB_URL_TO_PARSE="$1" "$py" - <<'PY'
import os
from urllib.parse import urlsplit, parse_qs
url = os.environ["DB_URL_TO_PARSE"]
parts = urlsplit(url)
host = parts.hostname or ""
if not host:
    host = (parse_qs(parts.query).get("host") or [""])[0]
print(host)
PY
}

db_url_is_local() {
  local host
  host="$(db_url_host "$1")"
  case "$host" in
    ''|localhost|127.0.0.1|::1|0.0.0.0) return 0 ;;
    /cloudsql*) return 1 ;;
    /*) return 0 ;;  # local unix socket directory
    *) return 1 ;;
  esac
}

# ---------------------------------------------------------------------------
# Google Cloud defaults (override with environment variables)
# ---------------------------------------------------------------------------
gcp_defaults() {
  PROJECT_ID="${PROJECT_ID:-conversational-sales-agent}"
  REGION="${REGION:-us-central1}"
  AR_REPO="${AR_REPO:-sales-agent-repo}"
  SQL_INSTANCE="${SQL_INSTANCE:-csa-db}"
  SQL_TIER="${SQL_TIER:-db-f1-micro}"
  DB_NAME="${DB_NAME:-csa}"
  DB_USER="${DB_USER:-csa}"
  DB_JOB="${DB_JOB:-csa-db-init}"
  SA_GATEWAY="csa-gateway@${PROJECT_ID}.iam.gserviceaccount.com"
  SA_AGENTS="csa-agents@${PROJECT_ID}.iam.gserviceaccount.com"
  SA_TOOLS="csa-tools@${PROJECT_ID}.iam.gserviceaccount.com"
  SQL_CONNECTION="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"
  IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"
  export CLOUDSDK_CORE_PROJECT="$PROJECT_ID"
}

have_gcloud() { command -v gcloud >/dev/null 2>&1; }

gcp_preflight() {
  # Real runs need gcloud and an authenticated account; dry runs work without gcloud.
  if is_dry_run; then
    have_gcloud || log_warn "gcloud not installed: dry run assumes no resources exist yet"
    return 0
  fi
  require_cmd gcloud "Install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
  gcloud auth print-access-token >/dev/null 2>&1 || die "gcloud is not authenticated; run: gcloud auth login"
}

gcp_exists() {
  # gcp_exists <read-only gcloud command...> : true when the command succeeds.
  # In a dry run without gcloud, resources are assumed absent.
  if ! have_gcloud; then
    is_dry_run && return 1
    die "gcloud not installed"
  fi
  "$@" >/dev/null 2>&1
}
