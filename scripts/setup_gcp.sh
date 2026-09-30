#!/usr/bin/env bash
# One-time (idempotent) Google Cloud setup for the multi-service deployment.
#
# Usage: scripts/setup_gcp.sh [--dry-run] [--sync-db-password]
#   --dry-run           print the gcloud commands instead of running them (no prompts)
#   --sync-db-password  reset the Cloud SQL user's password to the DB_PASSWORD secret
#
# Creates, when missing (existing resources are reported as present and left alone):
#   - APIs: run, artifactregistry, secretmanager, sqladmin, cloudbuild, iam
#   - Artifact Registry docker repo  $AR_REPO (default sales-agent-repo)
#   - Cloud SQL PostgreSQL 16 instance $SQL_INSTANCE (default csa-db, db-f1-micro),
#     database csa, user csa (password generated into secret DB_PASSWORD)
#   - Secrets: GOOGLE_API_KEY (prompted, or taken from $GOOGLE_API_KEY), SESSION_SECRET_KEY
#     (generated), SMTP_USER / SMTP_PASSWORD (prompted; empty input skips them)
#   - Service accounts csa-gateway, csa-agents, csa-tools with roles/cloudsql.client and
#     secretAccessor on only the secrets each one needs
# Secret values are read with `read -rs` and are never printed.
# Overrides: PROJECT_ID, REGION, AR_REPO, SQL_INSTANCE, SQL_TIER, DB_NAME, DB_USER.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

SYNC_DB_PASSWORD=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --sync-db-password) SYNC_DB_PASSWORD=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done
export DRY_RUN
gcp_defaults
gcp_preflight
if ! is_dry_run; then
  require_cmd openssl
fi
log_info "project=$PROJECT_ID region=$REGION$(is_dry_run && echo ' (dry run)' || true)"

present() { log_ok "present: $*"; }

gen_secret() { openssl rand -base64 48 | tr -d '\n/+=' | cut -c1-48; }

# ---------------------------------------------------------------------------
section "APIs"
run gcloud services enable \
  run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com \
  sqladmin.googleapis.com cloudbuild.googleapis.com iam.googleapis.com \
  --project="$PROJECT_ID"

# ---------------------------------------------------------------------------
section "Artifact Registry"
if gcp_exists gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" --project="$PROJECT_ID"; then
  present "Artifact Registry repo $AR_REPO"
else
  run gcloud artifacts repositories create "$AR_REPO" --repository-format=docker \
    --location="$REGION" --description="Conversational Sales Agent images" --project="$PROJECT_ID"
fi

# ---------------------------------------------------------------------------
section "Cloud SQL"
if gcp_exists gcloud sql instances describe "$SQL_INSTANCE" --project="$PROJECT_ID"; then
  present "Cloud SQL instance $SQL_INSTANCE"
else
  log_info "Creating Cloud SQL instance $SQL_INSTANCE (takes several minutes)"
  run gcloud sql instances create "$SQL_INSTANCE" --database-version=POSTGRES_16 \
    --edition=ENTERPRISE --tier="$SQL_TIER" --region="$REGION" \
    --storage-type=SSD --storage-size=10 --storage-auto-increase \
    --project="$PROJECT_ID"
fi

if gcp_exists gcloud sql databases describe "$DB_NAME" --instance="$SQL_INSTANCE" --project="$PROJECT_ID"; then
  present "database $DB_NAME"
else
  run gcloud sql databases create "$DB_NAME" --instance="$SQL_INSTANCE" --project="$PROJECT_ID"
fi

create_secret() {
  # create_secret <name> ; value on stdin (never printed)
  run_stdin gcloud secrets create "$1" --replication-policy=automatic --data-file=- --project="$PROJECT_ID"
}

secret_exists() { gcp_exists gcloud secrets describe "$1" --project="$PROJECT_ID"; }

DB_PASSWORD_VALUE=""
if secret_exists DB_PASSWORD; then
  present "secret DB_PASSWORD"
else
  if is_dry_run; then DB_PASSWORD_VALUE="dry-run"; else DB_PASSWORD_VALUE="$(gen_secret)"; fi
  printf '%s' "$DB_PASSWORD_VALUE" | create_secret DB_PASSWORD
fi

db_password() {
  if [ -z "$DB_PASSWORD_VALUE" ]; then
    if is_dry_run; then
      DB_PASSWORD_VALUE="dry-run"
    else
      DB_PASSWORD_VALUE="$(gcloud secrets versions access latest --secret=DB_PASSWORD --project="$PROJECT_ID")"
    fi
  fi
}

USER_EXISTS=0
if have_gcloud && gcloud sql users list --instance="$SQL_INSTANCE" --project="$PROJECT_ID" \
  --format='value(name)' 2>/dev/null | grep -qx "$DB_USER"; then
  USER_EXISTS=1
fi
if [ "$USER_EXISTS" = "1" ]; then
  present "database user $DB_USER"
  if [ "$SYNC_DB_PASSWORD" = "1" ]; then
    db_password
    run_redacted "gcloud sql users set-password $DB_USER --instance=$SQL_INSTANCE --password=[DB_PASSWORD secret]" \
      gcloud sql users set-password "$DB_USER" --instance="$SQL_INSTANCE" --password="$DB_PASSWORD_VALUE" --project="$PROJECT_ID"
  fi
else
  db_password
  run_redacted "gcloud sql users create $DB_USER --instance=$SQL_INSTANCE --password=[DB_PASSWORD secret]" \
    gcloud sql users create "$DB_USER" --instance="$SQL_INSTANCE" --password="$DB_PASSWORD_VALUE" --project="$PROJECT_ID"
fi
DB_PASSWORD_VALUE=""

# ---------------------------------------------------------------------------
section "Secrets"
prompt_secret() {
  # prompt_secret <name> <required 0|1> ; prints nothing, sets PROMPTED_VALUE
  local name="$1" required="$2" value=""
  PROMPTED_VALUE=""
  if env_is_set "$name" && [ -n "$(env_value "$name")" ]; then
    PROMPTED_VALUE="$(env_value "$name")"
    log_info "$name taken from the environment"
    return 0
  fi
  [ -t 0 ] || die "$name is missing and stdin is not a terminal; export $name or run interactively"
  while :; do
    if [ "$required" = "1" ]; then
      read -rs -p "Enter $name (input hidden): " value
    else
      read -rs -p "Enter $name (input hidden, empty to skip): " value
    fi
    printf '\n' >&2
    if [ -n "$value" ] || [ "$required" = "0" ]; then break; fi
    log_warn "$name is required"
  done
  PROMPTED_VALUE="$value"
}

ensure_secret() {
  # ensure_secret <name> <generate|required|optional>
  local name="$1" mode="$2"
  if secret_exists "$name"; then
    present "secret $name"
    return 0
  fi
  if is_dry_run; then
    case "$mode" in
      generate) printf 'x' | create_secret "$name" ;;
      *) printf 'x' | create_secret "$name"; log_info "(a real run prompts for $name with hidden input)" ;;
    esac
    return 0
  fi
  case "$mode" in
    generate) gen_secret | create_secret "$name" ;;
    required|optional)
      prompt_secret "$name" "$([ "$mode" = required ] && echo 1 || echo 0)"
      if [ -z "$PROMPTED_VALUE" ]; then
        log_warn "skipped secret $name (deploy_cloud.sh deploys without it)"
        return 0
      fi
      printf '%s' "$PROMPTED_VALUE" | create_secret "$name"
      PROMPTED_VALUE=""
      ;;
  esac
}

ensure_secret GOOGLE_API_KEY required
ensure_secret SESSION_SECRET_KEY generate
ensure_secret SMTP_USER optional
ensure_secret SMTP_PASSWORD optional

# ---------------------------------------------------------------------------
section "Service accounts and IAM"
ensure_sa() {
  local email="$1" display="$2"
  if gcp_exists gcloud iam service-accounts describe "$email" --project="$PROJECT_ID"; then
    present "service account $email"
  else
    run gcloud iam service-accounts create "${email%%@*}" --display-name="$display" --project="$PROJECT_ID"
  fi
}

ensure_sa "$SA_GATEWAY" "CSA gateway (public Cloud Run service)"
ensure_sa "$SA_AGENTS" "CSA A2A agent services"
ensure_sa "$SA_TOOLS" "CSA tool services (catalog, serviceability)"

for sa in "$SA_GATEWAY" "$SA_AGENTS" "$SA_TOOLS"; do
  run gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$sa" \
    --role=roles/cloudsql.client --condition=None --quiet --format=none
done

grant_secret() {
  # grant_secret <secret> <sa...> : secretAccessor on one secret (skipped if the secret is absent)
  local secret="$1" sa
  shift
  if ! is_dry_run && ! secret_exists "$secret"; then
    log_warn "secret $secret not present; no access granted"
    return 0
  fi
  for sa in "$@"; do
    run gcloud secrets add-iam-policy-binding "$secret" --member="serviceAccount:$sa" \
      --role=roles/secretmanager.secretAccessor --project="$PROJECT_ID" --quiet --format=none
  done
}

grant_secret DB_PASSWORD "$SA_GATEWAY" "$SA_AGENTS" "$SA_TOOLS"
grant_secret GOOGLE_API_KEY "$SA_GATEWAY" "$SA_AGENTS"
grant_secret SESSION_SECRET_KEY "$SA_GATEWAY"
grant_secret SMTP_USER "$SA_AGENTS"
grant_secret SMTP_PASSWORD "$SA_AGENTS"

section "Done"
cat >&2 <<EOF
Cloud SQL connection name: $SQL_CONNECTION
Images:                    $IMAGE_BASE/<service>
Next: scripts/deploy_cloud.sh   (Cloud Run invoker bindings are set per service at deploy time)
EOF
