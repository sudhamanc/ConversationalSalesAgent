"""Custom ADK metric: ``golden_trajectory_v1``.

ADK's ``tool_trajectory_avg_score`` requires every argument to match exactly,
which cannot work for values created during a run (cart/order/appointment ids,
payment tokens, dates). Goldens therefore list only the *stable* arguments of
each expected call, and this metric checks:

* the golden calls occur in the actual calls in the same order (extra actual
  calls, e.g. a lookup before a write, are allowed), and
* every argument the golden call lists equals the actual argument
  (strings compared case- and whitespace-insensitively, numbers numerically,
  lists of scalars as multisets).

Per invocation the score is matched golden calls / golden calls (1.0 when the
golden expects no calls and none were made; 0.0 when it expects none but some
were made). Registered through ``EvalConfig.custom_metrics`` with
``code_config.name = "evals.metrics.golden_trajectory_v1"``.
"""

from __future__ import annotations

from typing import Any, Optional

from google.adk.evaluation.eval_case import ConversationScenario, Invocation, get_all_tool_calls
from google.adk.evaluation.eval_metrics import EvalMetric, EvalStatus
from google.adk.evaluation.evaluator import EvaluationResult, PerInvocationResult

DEFAULT_THRESHOLD = 1.0


def _norm(value: Any) -> Any:
    if isinstance(value, str):
        text = " ".join(value.split()).lower()
        try:  # models often send numbers as strings ("4", "1200.0")
            return round(float(text), 4)
        except ValueError:
            return text
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    if isinstance(value, list):
        items = [_norm(v) for v in value]
        try:
            return sorted(items)
        except TypeError:
            return items
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    return value


def call_matches(expected_name: str, expected_args: dict, actual_name: str, actual_args: dict) -> bool:
    if expected_name != actual_name:
        return False
    actual_args = actual_args or {}
    for key, value in (expected_args or {}).items():
        if key not in actual_args or _norm(actual_args[key]) != _norm(value):
            return False
    return True


def trajectory_score(expected_calls: list[tuple[str, dict]], actual_calls: list[tuple[str, dict]]) -> float:
    """Fraction of golden calls found in order (greedy subsequence match)."""
    if not expected_calls:
        return 1.0 if not actual_calls else 0.0
    matched, cursor = 0, 0
    for name, args in expected_calls:
        for i in range(cursor, len(actual_calls)):
            if call_matches(name, args, *actual_calls[i]):
                matched += 1
                cursor = i + 1
                break
    return matched / len(expected_calls)


def _calls(invocation: Optional[Invocation]) -> list[tuple[str, dict]]:
    if invocation is None:
        return []
    return [(c.name, dict(c.args or {})) for c in get_all_tool_calls(invocation.intermediate_data)]


def _threshold(eval_metric: EvalMetric) -> float:
    if eval_metric.criterion is not None and eval_metric.criterion.threshold is not None:
        return eval_metric.criterion.threshold
    if eval_metric.threshold is not None:
        return eval_metric.threshold
    return DEFAULT_THRESHOLD


def golden_trajectory_v1(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: Optional[list[Invocation]],
    conversation_scenario: Optional[ConversationScenario] = None,
) -> EvaluationResult:
    threshold = _threshold(eval_metric)
    if not expected_invocations:
        return EvaluationResult(overall_eval_status=EvalStatus.NOT_EVALUATED)

    per_invocation: list[PerInvocationResult] = []
    for actual, expected in zip(actual_invocations, expected_invocations):
        score = trajectory_score(_calls(expected), _calls(actual))
        per_invocation.append(
            PerInvocationResult(
                actual_invocation=actual,
                expected_invocation=expected,
                score=score,
                eval_status=EvalStatus.PASSED if score >= threshold else EvalStatus.FAILED,
            )
        )
    if not per_invocation:
        return EvaluationResult(overall_eval_status=EvalStatus.NOT_EVALUATED)
    overall = sum(r.score for r in per_invocation) / len(per_invocation)
    return EvaluationResult(
        overall_score=overall,
        overall_eval_status=EvalStatus.PASSED if overall >= threshold else EvalStatus.FAILED,
        per_invocation_results=per_invocation,
    )
