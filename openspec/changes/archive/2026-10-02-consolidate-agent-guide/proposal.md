# Proposal: Remove BootStrapAgent and Move the Agent Service Guide into README

## Why

- `BootStrapAgent/` is dead code: an ADK 1.20 template using in-process `sub_agents`. It is not in `services.conf`, compose or setup, and it contradicts the current one-A2A-service-per-agent design. Docs still point sessions at it ("Bootstrap Template").
- The real build pattern lives in `docs/agent-service-guide.md`, separate from the README that readers start with.

## What Changes

- Delete `BootStrapAgent/`.
- Move `docs/agent-service-guide.md` into README.md as the "Agent Service Guide" section; delete the file.
- Repoint every reference (CLAUDE.md, AGENTS.md, per-agent docs, SuperAgent README, BASELINE.md, `openspec/config.yaml`, architecture brief, `requirements.txt`, an `.env.example` comment) to the README section. Replace "ADK Bootstrap Template" wording with the agent service pattern.

BASELINE.md sections affected: 3, 8 (guide location).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-services`: adds that the README documents the agent service pattern.

## Non-goals

- Changing any agent's code or behavior.
- Rewriting historical documents (`openspec/changes/archive/*`, `CustomerCommunicationAgent/IMPLEMENTATION_SUMMARY.md`).

## Impact

- **Code:** none (dead folder removed).
- **Docs:** README.md gains the guide; references across ~35 files are repointed.
