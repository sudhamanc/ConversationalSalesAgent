#!/usr/bin/env bash
# Pause the cloud deployment to stop costs:
#   1. remove public (allUsers) invoker access from the gateway (anonymous requests -> HTTP 403)
#   2. stop Cloud SQL (activation policy NEVER)
# Cloud Run services scale to zero on their own. Resume with scripts/start_cloud.sh.
#
# Usage: scripts/shutdown_cloud.sh [--dry-run]
# Overrides: PROJECT_ID, REGION, SQL_INSTANCE, GATEWAY_SERVICE (default csa-gateway)
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done
export DRY_RUN
gcp_defaults
gcp_preflight
GATEWAY_SERVICE="${GATEWAY_SERVICE:-csa-gateway}"

section "Gateway: remove public access"
public=1
if have_gcloud && ! is_dry_run; then
  if ! gcloud run services get-iam-policy "$GATEWAY_SERVICE" --region="$REGION" --project="$PROJECT_ID" \
      --flatten='bindings[].members' --filter='bindings.role:roles/run.invoker AND bindings.members:allUsers' \
      --format='value(bindings.members)' 2>/dev/null | grep -q allUsers; then
    public=0
  fi
fi
if [ "$public" = "1" ]; then
  run gcloud run services remove-iam-policy-binding "$GATEWAY_SERVICE" --region="$REGION" \
    --project="$PROJECT_ID" --member=allUsers --role=roles/run.invoker --quiet --format=none
  log_ok "$GATEWAY_SERVICE is private (anonymous requests get HTTP 403)"
else
  log_ok "$GATEWAY_SERVICE already private"
fi

section "Cloud SQL: stop $SQL_INSTANCE"
run gcloud sql instances patch "$SQL_INSTANCE" --activation-policy=NEVER --project="$PROJECT_ID" --quiet
log_ok "Cloud SQL activation policy NEVER (instance stopped). Resume: scripts/start_cloud.sh"
