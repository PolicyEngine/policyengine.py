"""Review bounds require usable baseline values for each candidate metric."""

import copy

import pytest

from policyengine.provenance.uk_candidate import compare_metric_reports, metrics_review

BOUNDS = {"default": {"relative": 0.02, "absolute": 5e8}}


def _report():
    return {
        "status": "ok",
        "metrics_version": "m1",
        "partition_version": "p1",
        "metrics": [
            {
                "metric_id": "income_tax",
                "year": 2027,
                "kind": "receipt",
                "value": 3e11,
            },
            {
                "metric_id": "relative_poverty",
                "year": 2027,
                "kind": "poverty",
                "value": 0.17,
            },
        ],
        "identities": [{"identity_id": "weights:household", "status": "pass"}],
    }


@pytest.mark.parametrize(
    "baseline_value", [float("nan"), float("inf"), -float("inf"), None, "invalid"]
)
def test_unusable_baseline_cannot_claim_a_large_move_is_within_bounds(baseline_value):
    candidate, previous = _report(), _report()
    candidate["metrics"][0]["value"] = 1e12
    previous["metrics"][0]["value"] = baseline_value

    status, summary, _ = compare_metric_reports(candidate, previous, BOUNDS)

    assert status == "fail"
    assert "previous" in summary and "non-finite" in summary
    gate, _ = metrics_review(
        candidate_report=candidate, previous_report=previous, bounds=BOUNDS
    )
    assert gate.status == "fail"
    assert gate.evidence_sha256


def test_a_baseline_row_without_a_value_cannot_pass():
    candidate, previous = _report(), _report()
    del previous["metrics"][0]["value"]
    assert compare_metric_reports(candidate, previous, BOUNDS)[0] == "fail"


def test_a_metric_without_a_baseline_requires_review():
    candidate, previous = _report(), _report()
    previous["metrics"] = previous["metrics"][1:]
    status, summary, evidence = compare_metric_reports(candidate, previous, BOUNDS)
    assert status == "needs_review"
    assert "no baseline" in summary and "income_tax" in summary
    assert evidence["metrics_without_baseline"] == ["income_tax 2027"]


@pytest.mark.parametrize("side", ["candidate", "previous"])
def test_a_duplicate_metric_cannot_hide_an_unusable_value(side):
    candidate, previous = _report(), _report()
    report = candidate if side == "candidate" else previous
    report["metrics"].insert(0, {**report["metrics"][0], "value": float("nan")})
    status, summary, _ = compare_metric_reports(candidate, previous, BOUNDS)
    assert status == "fail"
    assert "duplicate metrics" in summary and side in summary


def test_duplicate_finite_baselines_cannot_select_the_most_favourable_comparison():
    candidate, previous = _report(), _report()
    candidate["metrics"][0]["value"] = 1e12
    previous["metrics"].append({**previous["metrics"][0], "value": 1e12})
    status, summary, _ = compare_metric_reports(candidate, previous, BOUNDS)
    assert status == "fail"
    assert "previous report has duplicate metrics: income_tax 2027" in summary


def test_an_unusable_cross_report_cannot_pass_either_review_step():
    candidate, previous, cross = _report(), _report(), _report()
    cross["metrics"][0]["value"] = float("nan")
    gate, evidence = metrics_review(
        candidate_report=candidate,
        previous_report=previous,
        cross_report=cross,
        bounds=BOUNDS,
    )
    assert gate.status == "fail"
    assert "model_only" in evidence and "data_only" in evidence
    assert "data_only: the previous report has non-finite" in gate.summary


def test_valid_baselines_preserve_bounds_and_do_not_mutate_reports():
    candidate, previous = _report(), _report()
    original = copy.deepcopy((candidate, previous))
    assert compare_metric_reports(candidate, previous, BOUNDS)[0] == "pass"
    assert (candidate, previous) == original
    candidate["metrics"][0]["value"] = 1e12
    status, _, evidence = compare_metric_reports(candidate, previous, BOUNDS)
    assert status == "needs_review"
    assert evidence["moves_beyond_bounds"][0]["metric_id"] == "income_tax"
