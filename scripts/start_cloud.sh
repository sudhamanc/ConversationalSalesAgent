#!/usr/bin/env bash
# Resume a paused cloud deployment (reverse of scripts/shutdown_cloud.sh):
#   1. start Cloud SQL (activation policy ALWAYS)
#   2. restore public (allUsers) invoker access on the gateway
#   3. print the gateway URL
#
# Usage: scripts/start_cloud.sh [--dry-run]
# Overrides: PROJECT_ID, REGION, SQL_INSTANCE, GATEWAY_SERVICE (default csa-gateway)
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done
export DRY_RUN
gcp_defaults
gcp_preflight
GATEWAY_SERVICE="${GATEWAY_SERVICE:-csa-gateway}"

section "Cloud SQL: start $SQL_INSTANCE"
run gcloud sql instances patch "$SQL_INSTANCE" --activation-policy=ALWAYS --project="$PROJECT_ID" --quiet
log_ok "Cloud SQL activation policy ALWAYS"

section "Gateway: restore public access"
run gcloud run services add-iam-policy-binding "$GATEWAY_SERVICE" --region="$REGION" \
  --project="$PROJECT_ID" --member=allUsers --role=roles/run.invoker --quiet --format=none
log_ok "$GATEWAY_SERVICE is public"

if is_dry_run && ! have_gcloud; then
  url="https://${GATEWAY_SERVICE}-dryrun.${REGION}.run.app"
else
  url="$(gcloud run services describe "$GATEWAY_SERVICE" --region="$REGION" --project="$PROJECT_ID" \
    --format='value(status.url)' 2>/dev/null || true)"
fi
[ -n "$url" ] || die "could not read the URL of $GATEWAY_SERVICE (is it deployed? scripts/deploy_cloud.sh)"
printf '\nGateway URL: %s\n' "$url"
