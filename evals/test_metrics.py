"""Unit tests for the golden_trajectory_v1 metric (offline)."""

from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_metrics import EvalMetric, EvalStatus
from google.genai import types

from evals.metrics import golden_trajectory_v1, trajectory_score


def test_in_order_subsequence_with_stable_args():
    expected = [("search_companies", {"company_name": "Beacon Wealth Advisors"})]
    actual = [("get_high_priority_opportunities", {}), ("search_companies", {"company_name": "beacon  wealth advisors"})]
    assert trajectory_score(expected, actual) == 1.0


def test_wrong_stable_argument_fails():
    expected = [("check_service_availability", {"zip_code": "19103"})]
    actual = [("check_service_availability", {"street": "1 A St", "zip_code": "19107"})]
    assert trajectory_score(expected, actual) == 0.0


def test_order_matters_and_partial_credit():
    expected = [("create_cart", {}), ("add_to_cart", {})]
    assert trajectory_score(expected, [("add_to_cart", {}), ("create_cart", {})]) == 0.5


def test_numbers_and_lists_are_normalized():
    expected = [("compare_products", {"product_ids": ["FIB-1G", "FIB-5G"]}), ("setup_payment_plan", {"total_amount": 1200})]
    actual = [("compare_products", {"product_ids": ["fib-5g", "FIB-1G"]}), ("setup_payment_plan", {"total_amount": 1200.0})]
    assert trajectory_score(expected, actual) == 1.0


def test_numeric_strings_match_numbers():
    expected = [("setup_payment_plan", {"total_amount": 1200, "num_installments": 4})]
    assert trajectory_score(expected, [("setup_payment_plan", {"total_amount": "1200.0", "num_installments": "4"})]) == 1.0
    assert trajectory_score(expected, [("setup_payment_plan", {"total_amount": "1300", "num_installments": "4"})]) == 0.0


def test_no_expected_calls_means_none_allowed():
    assert trajectory_score([], []) == 1.0
    assert trajectory_score([], [("get_order", {})]) == 0.0


def _inv(calls):
    return Invocation(
        user_content=types.Content(role="user", parts=[types.Part(text="x")]),
        intermediate_data=IntermediateData(tool_uses=[types.FunctionCall(name=n, args=a) for n, a in calls]),
    )


def test_metric_function_thresholds():
    metric = EvalMetric(metric_name="golden_trajectory_v1", threshold=1.0)
    result = golden_trajectory_v1(metric, [_inv([("get_order", {"order_id": "ORD-1"})])],
                                  [_inv([("get_order", {"order_id": "ORD-1"})])])
    assert result.overall_eval_status == EvalStatus.PASSED and result.overall_score == 1.0
    result = golden_trajectory_v1(metric, [_inv([("get_order", {"order_id": "ORD-2"})])],
                                  [_inv([("get_order", {"order_id": "ORD-1"})])])
    assert result.overall_eval_status == EvalStatus.FAILED
