# Spec Delta: service-operations

## ADDED Requirements

### Requirement: Local database lifecycle

`scripts/db.sh up` SHALL provide a PostgreSQL 16 database for `DATABASE_URL` and then apply migrations and seed:
- use `DATABASE_URL` as is when it already accepts connections
- otherwise, for a local host, start Docker container `csa-postgres` (image `PG_IMAGE`, default `postgres:16`, volume `csa-pgdata`, bound to `127.0.0.1`) with the user, password and database from `DATABASE_URL`
- fall back to Homebrew `postgresql@16` when Docker is not installed, when the image cannot be pulled, or when `--native` is given, creating the role and database from `DATABASE_URL`

`scripts/db.sh down` SHALL stop whichever of the two is running and keep its data.

#### Scenario: Image pull blocked
- **WHEN** Docker is running but `PG_IMAGE` cannot be pulled
- **THEN** `up` warns, uses Homebrew `postgresql@16`, and completes migrate + seed

#### Scenario: Container engine not running
- **WHEN** Docker is installed, its engine does not answer, and the desktop app is not running
- **THEN** `up` exits non-zero naming the app to start (e.g. `open -a "Rancher Desktop"`) and does not fall back to Homebrew

#### Scenario: Engine still booting
- **WHEN** the desktop app is running but its engine is not ready
- **THEN** `up` waits up to `ENGINE_WAIT_SECONDS` (default 120) before failing

#### Scenario: Database already reachable
- **WHEN** `DATABASE_URL` accepts connections
- **THEN** `up` starts nothing and only applies pending migrations and seed

### Requirement: Local start database preflight

`scripts/start_local.sh` SHALL verify that `DATABASE_URL` accepts connections before starting any process.

#### Scenario: Database unreachable
- **WHEN** `start_local.sh` runs and the database refuses connections
- **THEN** it prints the connection error and `scripts/db.sh up`, exits non-zero, and starts nothing
