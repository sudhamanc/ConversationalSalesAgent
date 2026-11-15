"""cases.jsonl writer and the Langfuse sync (offline: fake Langfuse client, no SDK needed)."""

from __future__ import annotations

import csv
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from evals import langfuse_sync
from evals.cases import append_cases, case_record, cases_from_agent_csv, metric, read_cases


def _router_case(eval_id: str, passed: bool) -> dict:
    return case_record(
        key=f"router/router/{eval_id}",
        tier="router",
        set_name="router",
        input='{"message": "how much for fiber?"}',
        expected={"target": "offer_management_agent"},
        actual={"target": "offer_management_agent" if passed else "product_agent"},
        metrics=[metric("target_match", float(passed), 1.0, passed), metric("valid_decision", 1.0, 1.0, True)],
        passed=passed,
    )


def _journey_case() -> dict:
    return case_record(
        key="journeys/s4-non-serviceable/s4",
        tier="journeys",
        set_name="journeys",
        input=["We're Acme at 1 Main St, Helena MT 59601"],
        expected={"replies": ["Sorry, not serviceable"], "agents": [["discovery_agent", "serviceability_agent"]]},
        actual={"replies": ["Unfortunately not serviceable"], "agents": [["discovery_agent", "serviceability_agent"]]},
        metrics=[metric("turn1_agents_match", 1.0, 1.0, True), metric("rubric", None, None, None)],
        passed=True,
        session_id="gw-session-1",
        trace_ids=["a" * 32, None],
    )


def test_append_and_read_roundtrip(tmp_path):
    assert append_cases(tmp_path, [_router_case("pricing", True)]) == 1
    append_cases(tmp_path, [_journey_case()])
    cases = read_cases(tmp_path / "cases.jsonl")
    assert [c["tier"] for c in cases] == ["router", "journeys"]
    assert cases[1]["trace_ids"] == ["a" * 32]  # missing trace ids dropped


def test_cases_from_agent_csv(tmp_path):
    path = tmp_path / "agent-order_agent.csv"
    columns = ["eval_set_id", "eval_id", "metric_name", "threshold", "score", "eval_status", "prompt",
               "expected_response", "actual_response", "expected_tool_calls", "actual_tool_calls"]
    rows = [
        ["agents/order_agent/order_agent", "create-cart", "golden_trajectory_v1", "1.0", "1.0", "PASSED", "Add fiber", "Added.", "Added!", "create_cart", "create_cart"],
        ["agents/order_agent/order_agent", "create-cart", "final_response_match_v2", "0.8", "0.5", "FAILED", "Add fiber", "Added.", "Added!", "", ""],
        ["agents/order_agent/order_agent", "cancel", "golden_trajectory_v1", "1.0", "", "NOT_EVALUATED", "Cancel", "Done.", "Done.", "", ""],
    ]
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    cases = {c["key"]: c for c in cases_from_agent_csv(path, "order_agent")}
    create = cases["agents/order_agent/order_agent/create-cart"]
    assert create["tier"] == "agents" and create["set"] == "order_agent"
    assert create["passed"] is False
    assert [m["score"] for m in create["metrics"]] == [1.0, 0.5]
    assert create["actual"]["response"] == "Added!"
    assert cases["agents/order_agent/order_agent/cancel"]["metrics"][0]["score"] is None


def test_discover_runs(tmp_path):
    root = tmp_path / "20261114-120000"
    for run in ("run-1", "run-2"):
        append_cases(root / run, [_router_case("x", True)])
    assert [name for _, name in langfuse_sync.discover_runs(root)] == ["20261114-120000-run-1", "20261114-120000-run-2"]
    assert [name for _, name in langfuse_sync.discover_runs(root / "run-2")] == ["20261114-120000-run-2"]


class FakeClient:
    def __init__(self):
        self.datasets: dict[str, list] = {}
        self.items: dict[str, SimpleNamespace] = {}
        self.experiments = []
        self.flushed = False

    def get_dataset(self, name):
        if name not in self.datasets:
            raise LookupError(name)
        return SimpleNamespace(items=[self.items[i] for i in self.datasets[name]])

    def create_dataset(self, *, name, description=None, metadata=None):
        self.datasets[name] = []

    def create_dataset_item(self, *, dataset_name, id, input, expected_output, metadata):
        self.items[id] = SimpleNamespace(id=id, input=input, expected_output=expected_output, metadata=metadata)
        if id not in self.datasets[dataset_name]:
            self.datasets[dataset_name].append(id)

    def run_experiment(self, *, name, run_name, description, data, task, evaluators, metadata, max_concurrency):
        results = []
        for item in data:
            output = task(item=item)
            scores = [e for ev in evaluators for e in ev(input=item.input, output=output,
                                                       expected_output=item.expected_output, metadata=item.metadata)]
            results.append((item.metadata["case_key"], output, scores))
        self.experiments.append({"name": name, "run_name": run_name, "metadata": metadata, "results": results})

    def flush(self):
        self.flushed = True


@pytest.fixture
def sdk():
    sessions = []

    @contextmanager
    def propagate_attributes(**kwargs):
        sessions.append(kwargs["session_id"])
        yield

    return SimpleNamespace(Evaluation=lambda **kw: kw, propagate_attributes=propagate_attributes, sessions=sessions)


def test_sync_creates_datasets_runs_and_scores(sdk):
    client = FakeClient()
    cases = [_router_case("pricing", True), _router_case("product", False), _journey_case()]
    summary = langfuse_sync.sync_cases(cases, "20261114-run-1", client=client, sdk=sdk, metadata={"git_commit": "abc"})

    assert summary == {"csa-golden-journeys": 1, "csa-golden-router": 2}
    assert client.flushed
    by_name = {e["name"]: e for e in client.experiments}
    router = by_name["csa-golden-router"]
    assert router["run_name"] == "20261114-run-1" and router["metadata"] == {"git_commit": "abc"}
    results = {key: (output, scores) for key, output, scores in router["results"]}
    output, scores = results["router/router/product"]
    assert output == {"target": "product_agent"}  # replayed, not recomputed
    assert {s["name"]: s["value"] for s in scores} == {"target_match": 0.0, "valid_decision": 1.0, "passed": 0.0}
    assert [s for s in scores if s["name"] == "passed"][0]["data_type"] == "BOOLEAN"

    journey_key, _, journey_scores = by_name["csa-golden-journeys"]["results"][0]
    assert journey_key == "journeys/s4-non-serviceable/s4"
    assert [s["name"] for s in journey_scores] == ["turn1_agents_match", "passed"]  # unscored metric skipped
    assert sdk.sessions == ["gw-session-1"]  # journey joined its gateway session


def test_sync_is_idempotent_on_items(sdk):
    client = FakeClient()
    langfuse_sync.sync_cases([_router_case("pricing", True)], "r1", client=client, sdk=sdk, metadata={})
    langfuse_sync.sync_cases([_router_case("pricing", True)], "r2", client=client, sdk=sdk, metadata={})
    assert len(client.datasets["csa-golden-router"]) == 1
    assert langfuse_sync.item_id("router/router/pricing") in client.items


def test_main_refuses_without_keys(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert langfuse_sync.main([str(tmp_path)]) == 2
    assert "LANGFUSE_PUBLIC_KEY" in capsys.readouterr().err
