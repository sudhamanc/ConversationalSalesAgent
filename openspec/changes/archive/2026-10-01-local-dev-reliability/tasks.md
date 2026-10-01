# Tasks: Local Development Reliability

## 1. Scripts

- [x] 1.1 Add `db_url_parts` and `db_check` to `scripts/lib.sh`; verify `bash -n scripts/lib.sh`
- [x] 1.2 Add `up` / `down` / `--native` / `PG_IMAGE` to `scripts/db.sh`; verify: reachable DB reused; engine-not-ready wait and message (`DOCKER_HOST` pointed at a missing socket); pull failure falls back to Homebrew (`PG_IMAGE=registry.invalid/postgres:16`); `down` stops Homebrew; `up --native` starts Homebrew, ensures role/db, seeds; `up` creates `csa-postgres` and seeds
- [x] 1.3 Add the database preflight to `scripts/start_local.sh`; verify it exits with the `db.sh up` hint when PostgreSQL is stopped
- [x] 1.4 Update the next steps printed by `scripts/setup_local.sh`

## 2. Gateway

- [x] 2.1 `build_router`: `thinking_level=MINIMAL` for `gemini-3*`, `max_output_tokens=1024`; verify live: 5/5 messages route with `finish_reason=STOP`, and a chat turn through `/api/chat` is answered by `discovery_agent`; `pytest SuperAgent/tests` passes
- [x] 2.2 Load only the repo-root `.env` in `super_agent/config.py`; delete `SuperAgent/server/.env.example`; verify `pytest SuperAgent/tests` passes

## 3. Docs and cleanup

- [x] 3.1 Update `README.md` (local start, `db.sh up` decision order, proxy note, database operations), `db/README.md`, `SuperAgent/README.md`, `AGENTS.md`; verify no doc references the removed `docker run` line or `SuperAgent/server/.env`
- [x] 3.2 Delete legacy root documents and their README reference; verify `git grep` finds no links to them
- [x] 3.3 Require an OpenSpec change for every new change in `CLAUDE.md` and `AGENTS.md`
