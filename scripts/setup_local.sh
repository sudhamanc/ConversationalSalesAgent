#!/usr/bin/env bash
# One-time local setup:
#   - Python 3.12 virtual environment at ./venv (created or reused)
#   - editable installs of libs/sales_common and every service in scripts/services.conf
#   - React client dependencies (npm ci in SuperAgent/client)
#   - .env copied from .env.example ONLY when .env does not exist (never overwritten)
#
# Usage: scripts/setup_local.sh [--skip-python] [--skip-npm] [--no-dev]
#   --skip-python  do not create the venv or install Python packages
#   --skip-npm     do not install client dependencies
#   --no-dev       do not install pytest / pytest-asyncio
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

SKIP_PYTHON=0
SKIP_NPM=0
DEV=1
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-python) SKIP_PYTHON=1 ;;
    --skip-npm) SKIP_NPM=1 ;;
    --no-dev) DEV=0 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done

services_load
cd "$REPO_ROOT"
WARNINGS=()

# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------
pick_python() {
  local candidate
  for candidate in python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        command -v "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

python_version() { "$1" -c 'import sys; print("%d.%d" % sys.version_info[:2])'; }

if [ "$SKIP_PYTHON" = "0" ]; then
  section "Python virtual environment ($VENV_DIR)"
  USE_UV=0
  if command -v uv >/dev/null 2>&1; then
    USE_UV=1
    log_info "uv found: $(uv --version)"
  fi

  if [ -x "$VENV_DIR/bin/python" ]; then
    VENV_VER="$(python_version "$VENV_DIR/bin/python")"
    log_info "Reusing existing venv (Python $VENV_VER)"
    if [ "$VENV_VER" != "3.12" ]; then
      WARNINGS+=("venv uses Python $VENV_VER; Python 3.12 is the supported version (delete ./venv to recreate)")
    fi
  else
    BASE_PY="$(pick_python)" || die "Python >= 3.11 not found (Python 3.12 recommended)."
    BASE_VER="$(python_version "$BASE_PY")"
    [ "$BASE_VER" = "3.12" ] || WARNINGS+=("created venv with Python $BASE_VER; Python 3.12 is the supported version")
    if [ "$USE_UV" = "1" ]; then
      run uv venv --python "$BASE_PY" "$VENV_DIR"
    else
      run "$BASE_PY" -m venv "$VENV_DIR"
    fi
  fi
  PY="$VENV_DIR/bin/python"
  [ -x "$PY" ] || die "venv python missing at $PY"

  pip_install() {
    if [ "$USE_UV" = "1" ]; then
      run uv pip install --python "$PY" "$@"
    else
      run "$PY" -m pip install --disable-pip-version-check "$@"
    fi
  }

  if [ "$USE_UV" = "0" ]; then
    run "$PY" -m pip install --disable-pip-version-check --upgrade pip
  fi

  section "Installing libs/sales_common (editable)"
  pip_install -e "$REPO_ROOT/libs/sales_common"

  section "Installing services (editable)"
  EDITABLE_ARGS=()
  for i in "${!SVC_NAME[@]}"; do
    dir="$REPO_ROOT/${SVC_DIR[$i]}"
    if [ -f "$dir/pyproject.toml" ] || [ -f "$dir/setup.py" ]; then
      EDITABLE_ARGS+=(-e "$dir")
      log_info "  ${SVC_NAME[$i]} -> ${SVC_DIR[$i]}"
    else
      WARNINGS+=("${SVC_NAME[$i]}: ${SVC_DIR[$i]} has no pyproject.toml; not installed")
    fi
  done
  if [ "${#EDITABLE_ARGS[@]}" -gt 0 ]; then
    pip_install "${EDITABLE_ARGS[@]}"
  fi
  if [ "$DEV" = "1" ]; then
    pip_install "pytest>=8" "pytest-asyncio>=0.24"
  fi
  log_ok "Python packages installed into $VENV_DIR"
fi

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
if [ "$SKIP_NPM" = "0" ]; then
  section "Client dependencies (SuperAgent/client)"
  if command -v npm >/dev/null 2>&1; then
    (cd "$REPO_ROOT/SuperAgent/client" && run npm ci --no-audit --no-fund)
    log_ok "npm ci complete"
  else
    WARNINGS+=("npm not found; client dependencies not installed (Node 20+ required for the UI)")
  fi
fi

# ---------------------------------------------------------------------------
# .env (never overwritten)
# ---------------------------------------------------------------------------
section ".env"
if [ -e "$REPO_ROOT/.env" ]; then
  log_ok ".env already exists; kept unchanged"
elif [ -f "$REPO_ROOT/.env.example" ]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  chmod 600 "$REPO_ROOT/.env" 2>/dev/null || true
  log_ok "Created .env from .env.example; edit it and set GOOGLE_API_KEY, GEMINI_MODEL and DATABASE_URL"
else
  WARNINGS+=(".env.example not found; .env not created")
fi

if [ "${#WARNINGS[@]}" -gt 0 ]; then
  section "Warnings"
  for w in "${WARNINGS[@]}"; do log_warn "$w"; done
fi

cat >&2 <<EOF

Next steps:
  1. Edit .env (GOOGLE_API_KEY; GEMINI_MODEL and DATABASE_URL defaults work locally)
  2. scripts/db.sh up              # local PostgreSQL 16 (Docker, Homebrew fallback) + migrations + seed
  3. scripts/start_local.sh        # start all services + UI
EOF
