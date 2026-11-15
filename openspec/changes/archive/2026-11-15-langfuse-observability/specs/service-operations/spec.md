## ADDED Requirements

### Requirement: Observability configuration

`.env.example` SHALL document these settings:
- `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` (empty keys disable tracing)
- `LANGFUSE_TRACING_ENVIRONMENT` (default `local`)
- `LANGFUSE_CAPTURE_CONTENT` (default `true`)
- `TELEMETRY_FLUSH_PER_REQUEST` (default `false`)

`scripts/start_local.sh` SHALL pass these settings to every service through the shared `.env`. In `docker compose`, every application service SHALL run with `LANGFUSE_TRACING_ENVIRONMENT=docker`.

#### Scenario: Local tracing enabled
- **WHEN** a developer sets both Langfuse keys in `.env` and runs `scripts/start_local.sh`
- **THEN** the gateway, all agents and both tool services export traces with environment `local`

#### Scenario: Compose environment label
- **WHEN** the stack runs with `docker compose up` and Langfuse keys are set in `.env`
- **THEN** traces have environment `docker`

### Requirement: Langfuse wiring in cloud deployment

`scripts/setup_gcp.sh` SHALL prompt for `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` when the secrets don't exist. Input SHALL be hidden and never echoed, and empty input SHALL skip creating them. When they exist, the script SHALL grant `roles/secretmanager.secretAccessor` on both secrets to the gateway, agent and tool service accounts.

When both secrets exist, `scripts/deploy_cloud.sh` SHALL deploy every service with:
- the two secrets as environment variables
- `LANGFUSE_HOST` (default `https://us.cloud.langfuse.com`, overridable from the environment)
- `LANGFUSE_TRACING_ENVIRONMENT=gcp`
- `LANGFUSE_RELEASE=<image tag>`
- `LANGFUSE_CAPTURE_CONTENT` (default `true`, overridable from the environment)
- `TELEMETRY_FLUSH_PER_REQUEST=true`

When the secrets are absent, it SHALL deploy without them, and tracing stays off. `--dry-run` SHALL print the resulting flags.

#### Scenario: Secrets present
- **WHEN** `deploy_cloud.sh --dry-run` runs after the Langfuse secrets were created
- **THEN** every printed `gcloud run deploy` command includes `LANGFUSE_PUBLIC_KEY=LANGFUSE_PUBLIC_KEY:latest`, `LANGFUSE_SECRET_KEY=LANGFUSE_SECRET_KEY:latest` and `LANGFUSE_TRACING_ENVIRONMENT=gcp`

#### Scenario: Secrets skipped
- **WHEN** the operator left the Langfuse prompts empty during setup
- **THEN** deploys succeed without Langfuse settings and no service exports traces
