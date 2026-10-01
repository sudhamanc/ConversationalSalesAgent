# project-baseline Specification

## Purpose
TBD - created by archiving change project-baseline. Update Purpose after archive.
## Requirements
### Requirement: Maintained system baseline

The repository SHALL contain `openspec/BASELINE.md`, a system map that lists:
- every service in `scripts/services.conf` with its port
- for every agent: its tools, the journey context it writes and reads, the tables it owns, its prompt, tests and golden eval set
- the gateway workflow, routing and handoff rules
- the journey-context contract
- the operational commands
- change recipes
- the index of capability specs
- known open defects

CLAUDE.md SHALL direct every session to read it before exploring code.

#### Scenario: New session starts work on an agent
- **WHEN** a session needs an agent's port, tools, context keys or tables
- **THEN** BASELINE.md provides them without reading the agent's code

### Requirement: Baseline kept in sync

Every OpenSpec change that alters a service, port, tool, context key, handoff rule, command or known issue SHALL update BASELINE.md in the same change. `tests/test_baseline_doc.py` SHALL fail when a service, port or agent tool is missing from BASELINE.md.

#### Scenario: Tool added without updating the baseline
- **WHEN** an agent gains a tool (and `evals/golden/tool_schemas.json` is re-snapshotted) but BASELINE.md is not updated
- **THEN** `pytest tests/test_baseline_doc.py` fails, naming the missing tool

#### Scenario: Port changed in services.conf
- **WHEN** a port changes in `scripts/services.conf` but not in BASELINE.md
- **THEN** `pytest tests/test_baseline_doc.py` fails, naming the service

