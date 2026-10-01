"""openspec/BASELINE.md must stay in sync with the service manifest and agent tools.

Offline: no database, API key or network. Fix failures by updating BASELINE.md
(and, for tools, re-snapshotting with `python -m evals.record_golden --snapshot-tools`).
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE = (REPO_ROOT / "openspec" / "BASELINE.md").read_text()
SERVICES = [
    line.split("|")
    for line in (REPO_ROOT / "scripts" / "services.conf").read_text().splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
TOOLS = json.loads((REPO_ROOT / "evals" / "golden" / "tool_schemas.json").read_text())


@pytest.mark.parametrize("fields", SERVICES, ids=lambda f: f[0])
def test_service_and_port_listed(fields):
    name, directory, module, port = fields[0], fields[1], fields[2], fields[3]
    rows = [line for line in BASELINE.splitlines() if line.startswith(f"| {name} |")]
    assert rows, f"service {name!r} missing from the BASELINE.md services table"
    assert f"| {port} |" in rows[0], f"{name}: port {port} not in its BASELINE.md row: {rows[0]}"
    assert module in rows[0], f"{name}: module {module!r} not in its BASELINE.md row"


@pytest.mark.parametrize("agent", sorted(TOOLS))
def test_agent_tools_listed(agent):
    rows = [line for line in BASELINE.splitlines() if line.startswith(f"| **{agent}**")]
    assert rows, f"agent {agent!r} missing from the BASELINE.md agents table"
    missing = [tool for tool in TOOLS[agent] if tool not in rows[0]]
    assert not missing, f"{agent}: tools missing from BASELINE.md: {missing}"
