#!/usr/bin/env bash
# Build, push and deploy the multi-service system to Cloud Run.
#
# Usage: scripts/deploy_cloud.sh [--only name[,name...]] [--dry-run] [--local-docker]
#                                [--skip-build] [--migrate|--skip-migrate] [--tag TAG]
#   --only          build + deploy only these services (names from scripts/services.conf)
#   --dry-run       print every command (and the Cloud Build config) without running anything
#   --local-docker  build with local docker (linux/amd64) + docker push instead of Cloud Build
#   --skip-build    deploy images already pushed with --tag
#   --migrate       run the csa-db-init job even when the gateway is not selected
#   --skip-migrate  never run the csa-db-init job
#   --tag TAG       image tag (default: <git short sha>-<UTC timestamp>)
#
# Steps (run scripts/setup_gcp.sh once first):
#   1. build + push images (one parallel Cloud Build for all selected services)
#   2. Cloud Run job csa-db-init: python -m sales_common.migrate --seed (when the gateway is
#      selected, i.e. on a full deploy, or with --migrate)
#   3. tool services, 4. agents (MCP URLs + PUBLIC_URL), 5. gateway (AGENT_URL_* + ALLOWED_ORIGINS)
#   PUBLIC_URL / ALLOWED_ORIGINS use a second pass (services update) when a service is new.
# All services: --add-cloudsql-instances, DATABASE_URL on the /cloudsql socket (no password in
# the URL; libpq/asyncpg read PGPASSWORD from secret DB_PASSWORD), SERVICE_AUTH=gcp_id_token.
# Tools + agents are private (--no-allow-unauthenticated); run.invoker: csa-gateway SA on agents,
# csa-agents SA on tools. The gateway is public (--allow-unauthenticated).
# Overrides: PROJECT_ID, REGION, AR_REPO, SQL_INSTANCE, GEMINI_MODEL, GATEWAY_MIN_INSTANCES,
#            MAX_INSTANCES, SMTP_ENABLED, SMTP_HOST, SMTP_PORT, SMTP_FROM_NAME.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ONLY=""
BUILD_MODE=cloudbuild
SKIP_BUILD=0
MIGRATE=auto
TAG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --only) [ $# -ge 2 ] || die "--only needs a value"; ONLY="$2"; shift ;;
    --only=*) ONLY="${1#--only=}" ;;
    --dry-run) DRY_RUN=1 ;;
    --local-docker) BUILD_MODE=docker ;;
    --skip-build) SKIP_BUILD=1 ;;
    --migrate) MIGRATE=yes ;;
    --skip-migrate) MIGRATE=no ;;
    --tag) [ $# -ge 2 ] || die "--tag needs a value"; TAG="$2"; shift ;;
    --tag=*) TAG="${1#--tag=}" ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done
export DRY_RUN

gcp_defaults
gcp_preflight
services_load
select_services "$ONLY"

if [ -z "$TAG" ]; then
  [ "$SKIP_BUILD" = "0" ] || die "--skip-build needs --tag <existing tag>"
  TAG="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)-$(date -u +%Y%m%d%H%M%S)"
fi
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3-flash-preview}"
GATEWAY_MIN_INSTANCES="${GATEWAY_MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-3}"
DATABASE_URL_CLOUD="postgresql://${DB_USER}@/${DB_NAME}?host=/cloudsql/${SQL_CONNECTION}"

image_for() {
  local i
  i="$(svc_index "$1")"
  printf '%s/%s:%s' "$IMAGE_BASE" "${SVC_CLOUD[$i]}" "$2"
}

cloud_name() {
  local i
  i="$(svc_index "$1")"
  printf '%s' "${SVC_CLOUD[$i]}"
}

service_exists() {
  gcp_exists gcloud run services describe "$1" --region="$REGION" --project="$PROJECT_ID"
}

service_url() {
  # service_url <cloud_run_name> -> https URL ("" when the service does not exist)
  if ! have_gcloud && is_dry_run; then
    printf 'https://%s-dryrun.%s.run.app' "$1" "$REGION"
    return 0
  fi
  gcloud run services describe "$1" --region="$REGION" --project="$PROJECT_ID" \
    --format='value(status.url)' 2>/dev/null || true
}

require_url() {
  # require_url <service name> -> URL of an already deployed service, or die
  local cloud url
  cloud="$(cloud_name "$1")"
  url="$(service_url "$cloud")"
  [ -n "$url" ] || die "$1 ($cloud) is not deployed yet; deploy it first (e.g. --only $1)"
  printf '%s' "$url"
}

join_by() { local d="$1"; shift; local out="" x; for x in "$@"; do out="${out:+$out$d}$x"; done; printf '%s' "$out"; }

section "Plan"
log_info "project=$PROJECT_ID region=$REGION tag=$TAG build=$BUILD_MODE$(is_dry_run && echo ' (dry run)' || true)"
for kind in tool agent gateway; do
  for n in $(svc_names_of_kind "$kind" "${SELECTED[@]}"); do
    printf '  %-8s %-21s -> %s\n' "$kind" "$n" "$(cloud_name "$n")"
  done
done

# ---------------------------------------------------------------------------
# 1. Build + push
# ---------------------------------------------------------------------------
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [ "$SKIP_BUILD" = "1" ]; then
  log_info "Skipping build; deploying tag $TAG"
elif [ "$BUILD_MODE" = "cloudbuild" ]; then
  section "Build + push (Cloud Build)"
  CB="$TMP_DIR/cloudbuild.yaml"
  {
    printf 'steps:\n'
    for n in "${SELECTED[@]}"; do
      i="$(svc_index "$n")"
      printf -- '- id: build-%s\n  name: gcr.io/cloud-builders/docker\n  waitFor: ["-"]\n' "$n"
      printf '  args: ["build", "-f", "%s/Dockerfile", "-t", "%s", "-t", "%s", "."]\n' \
        "${SVC_DIR[$i]}" "$(image_for "$n" "$TAG")" "$(image_for "$n" latest)"
    done
    printf 'images:\n'
    for n in "${SELECTED[@]}"; do
      printf -- '- %s\n- %s\n' "$(image_for "$n" "$TAG")" "$(image_for "$n" latest)"
    done
    printf 'options:\n  machineType: E2_HIGHCPU_8\ntimeout: 3600s\n'
  } >"$CB"
  if is_dry_run; then
    printf -- '--- cloudbuild.yaml ---\n'; cat "$CB"; printf -- '---\n'
  fi
  run gcloud builds submit "$REPO_ROOT" --config="$CB" --ignore-file=.dockerignore --project="$PROJECT_ID"
else
  section "Build + push (local docker)"
  is_dry_run || require_cmd docker
  run gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
  for n in "${SELECTED[@]}"; do
    i="$(svc_index "$n")"
    run docker build --platform linux/amd64 -f "$REPO_ROOT/${SVC_DIR[$i]}/Dockerfile" \
      -t "$(image_for "$n" "$TAG")" -t "$(image_for "$n" latest)" "$REPO_ROOT"
    run docker push "$(image_for "$n" "$TAG")"
    run docker push "$(image_for "$n" latest)"
  done
fi

# ---------------------------------------------------------------------------
# 2. Migrations + seed (Cloud Run job, gateway image)
# ---------------------------------------------------------------------------
if [ "$MIGRATE" = "yes" ] || { [ "$MIGRATE" = "auto" ] && is_selected gateway; }; then
  section "Migrations + seed (Cloud Run job $DB_JOB)"
  if is_selected gateway; then JOB_IMAGE="$(image_for gateway "$TAG")"; else JOB_IMAGE="$(image_for gateway latest)"; fi
  run gcloud run jobs deploy "$DB_JOB" --image="$JOB_IMAGE" --region="$REGION" --project="$PROJECT_ID" \
    --service-account="$SA_GATEWAY" --set-cloudsql-instances="$SQL_CONNECTION" \
    --set-env-vars="^@^DATABASE_URL=${DATABASE_URL_CLOUD}@DB_DIR=/app/db@LOG_LEVEL=INFO" \
    --set-secrets="PGPASSWORD=DB_PASSWORD:latest" \
    --command=python --args=-m,sales_common.migrate,--seed \
    --tasks=1 --max-retries=0 --task-timeout=600s --quiet
  run gcloud run jobs execute "$DB_JOB" --region="$REGION" --project="$PROJECT_ID" --wait
else
  log_info "Skipping migrations (gateway not selected; use --migrate to force)"
fi

# ---------------------------------------------------------------------------
# 3-5. Deploy services in dependency order
# ---------------------------------------------------------------------------
secret_available() {
  # SMTP secrets are optional (setup_gcp.sh lets you skip them)
  if ! have_gcloud; then is_dry_run && return 0; fi
  gcloud secrets describe "$1" --project="$PROJECT_ID" >/dev/null 2>&1
}

DEPLOYED_URLS=()

deploy_service() {
  local name="$1" i kind cloud sa auth memory min_instances url existing_url
  local envs=() secrets=() dep var tool a pass2=()
  i="$(svc_index "$name")"
  kind="${SVC_KIND[$i]}"
  cloud="${SVC_CLOUD[$i]}"
  memory=1Gi
  min_instances=0
  auth=--no-allow-unauthenticated

  existing_url=""
  if service_exists "$cloud"; then existing_url="$(service_url "$cloud")"; fi

  envs=("DATABASE_URL=$DATABASE_URL_CLOUD" "SERVICE_AUTH=gcp_id_token" "LOG_LEVEL=INFO")
  secrets=("PGPASSWORD=DB_PASSWORD:latest")
  case "$kind" in
    tool)
      sa="$SA_TOOLS"
      [ "$name" != "catalog" ] || memory=2Gi
      [ "$name" != "serviceability" ] || envs+=("USE_MOCK_DATA=${USE_MOCK_DATA:-true}")
      ;;
    agent)
      sa="$SA_AGENTS"
      envs+=("GEMINI_MODEL=$GEMINI_MODEL")
      secrets+=("GOOGLE_API_KEY=GOOGLE_API_KEY:latest")
      if [ -n "$existing_url" ]; then envs+=("PUBLIC_URL=$existing_url"); fi
      if [ -n "${SVC_MCP[$i]}" ]; then
        IFS=',' read -r -a deps <<<"${SVC_MCP[$i]}"
        for dep in "${deps[@]}"; do
          var="${dep%%=*}"; tool="${dep#*=}"
          envs+=("$var=$(require_url "$tool")/mcp/")
        done
      fi
      if [ "$name" = "communication" ]; then
        local smtp_enabled="${SMTP_ENABLED:-}"
        if secret_available SMTP_USER && secret_available SMTP_PASSWORD; then
          secrets+=("SMTP_USER=SMTP_USER:latest" "SMTP_PASSWORD=SMTP_PASSWORD:latest")
          smtp_enabled="${smtp_enabled:-true}"
        else
          log_warn "SMTP secrets not found; communication agent deploys with simulated email"
          smtp_enabled=false
        fi
        envs+=("SMTP_ENABLED=$smtp_enabled" "SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}"
          "SMTP_PORT=${SMTP_PORT:-587}" "SMTP_FROM_NAME=${SMTP_FROM_NAME:-ComSales Notifications}")
      fi
      ;;
    gateway)
      sa="$SA_GATEWAY"
      auth=--allow-unauthenticated
      min_instances="$GATEWAY_MIN_INSTANCES"
      envs+=("GEMINI_MODEL=$GEMINI_MODEL" "RUN_MIGRATIONS=false" "SUGGESTIONS_ENABLED=${SUGGESTIONS_ENABLED:-true}")
      secrets+=("GOOGLE_API_KEY=GOOGLE_API_KEY:latest" "SESSION_SECRET_KEY=SESSION_SECRET_KEY:latest")
      if [ -n "$existing_url" ]; then envs+=("ALLOWED_ORIGINS=$existing_url"); fi
      for a in "${!SVC_NAME[@]}"; do
        [ "${SVC_KIND[$a]}" = "agent" ] || continue
        envs+=("$(a2a_env_var "${SVC_A2A[$a]}")=$(require_url "${SVC_NAME[$a]}")")
      done
      ;;
  esac

  section "Deploy $name ($cloud)"
  run gcloud run deploy "$cloud" --image="$(image_for "$name" "$TAG")" \
    --region="$REGION" --project="$PROJECT_ID" --platform=managed \
    --service-account="$sa" --add-cloudsql-instances="$SQL_CONNECTION" \
    --set-env-vars="^@^$(join_by @ "${envs[@]}")" \
    --set-secrets="$(join_by , "${secrets[@]}")" \
    --memory="$memory" --cpu=1 --min-instances="$min_instances" --max-instances="$MAX_INSTANCES" \
    --timeout=300 --execution-environment=gen2 "$auth" --quiet

  url="$(service_url "$cloud")"
  [ -n "$url" ] || die "could not read the URL of $cloud after deploy"

  # Second pass for a brand-new service: its own URL is only known after the first deploy.
  if [ -z "$existing_url" ]; then
    case "$kind" in
      agent) pass2=("PUBLIC_URL=$url") ;;
      gateway) pass2=("ALLOWED_ORIGINS=$url") ;;
    esac
    if [ "${#pass2[@]}" -gt 0 ]; then
      run gcloud run services update "$cloud" --region="$REGION" --project="$PROJECT_ID" \
        --update-env-vars="^@^$(join_by @ "${pass2[@]}")" --quiet
    fi
  fi

  case "$kind" in
    agent)
      run gcloud run services add-iam-policy-binding "$cloud" --region="$REGION" --project="$PROJECT_ID" \
        --member="serviceAccount:$SA_GATEWAY" --role=roles/run.invoker --quiet --format=none
      ;;
    tool)
      run gcloud run services add-iam-policy-binding "$cloud" --region="$REGION" --project="$PROJECT_ID" \
        --member="serviceAccount:$SA_AGENTS" --role=roles/run.invoker --quiet --format=none
      ;;
  esac
  DEPLOYED_URLS+=("$(printf '%-21s %s' "$name" "$url")")
}

for kind in tool agent gateway; do
  for n in $(svc_names_of_kind "$kind" "${SELECTED[@]}"); do
    deploy_service "$n"
  done
done

section "Deployed"
for line in "${DEPLOYED_URLS[@]}"; do printf '  %s\n' "$line"; done
if is_selected gateway; then
  printf '\nGateway (public): %s\nE2E: venv/bin/python scripts/e2e_test.py --base-url %s\n' \
    "$(service_url csa-gateway)" "$(service_url csa-gateway)"
fi
