"""The approved lineage requires a previously absent model input or column."""

from __future__ import annotations

import pytest

from policyengine.provenance.receipt import content_sha256
from tests.test_replay_exceptions import (
    INPUT,
    _budget_inputs,
    _failed_receipt,
    _judge,
)


@pytest.mark.parametrize(
    ("in_model", "in_data"), [(False, False), (True, False), (False, True)]
)
def test_previous_absence_allows_reviewed_exception(in_model, in_data):
    budget = _budget_inputs(
        previous_status={
            INPUT: {"in_model": in_model, "in_data": in_data, "usable": False}
        }
    )
    gate = _judge(_failed_receipt(), budget=budget)
    assert gate.status == "needs_review"
    assert len(gate.details["applied_exceptions"]) == 1


@pytest.mark.parametrize("usable", [False, True])
def test_previous_supplied_input_requires_fresh_decision_even_if_degenerate(usable):
    budget = _budget_inputs(
        previous_status={INPUT: {"in_model": True, "in_data": True, "usable": usable}}
    )
    gate = _judge(_failed_receipt(), budget=budget)
    assert gate.status == "fail"
    assert gate.details["applied_exceptions"] == []
    assert "a fresh registry decision is required" in gate.summary


@pytest.mark.parametrize(
    ("in_model", "in_data"), [(False, False), (True, False), (False, True)]
)
def test_inconsistent_previous_usable_flag_requires_fresh_decision(in_model, in_data):
    budget = _budget_inputs(
        previous_status={
            INPUT: {"in_model": in_model, "in_data": in_data, "usable": True}
        }
    )
    gate = _judge(_failed_receipt(), budget=budget)
    assert gate.status == "fail"
    assert gate.details["applied_exceptions"] == []
    assert "a fresh registry decision is required" in gate.summary


@pytest.mark.parametrize(
    "previous",
    [
        None,
        {},
        {INPUT: None},
        {INPUT: {}},
        {INPUT: {"in_model": False, "in_data": False}},
        {INPUT: {"in_model": 0, "in_data": False, "usable": False}},
        {INPUT: {"in_model": False, "in_data": "false", "usable": False}},
        {INPUT: {"in_model": False, "in_data": False, "usable": None}},
    ],
)
def test_unknown_or_malformed_previous_status_cannot_authorize_exception(previous):
    result, evidence = _budget_inputs()
    evidence["previous_input_status"] = previous
    result = result.model_copy(update={"evidence_sha256": content_sha256(evidence)})
    gate = _judge(_failed_receipt(), budget=(result, evidence))
    assert gate.status == "fail"
    assert gate.details["applied_exceptions"] == []
    assert "unknown" in gate.summary


def test_missing_previous_status_cannot_authorize_exception():
    result, evidence = _budget_inputs()
    evidence.pop("previous_input_status")
    result = result.model_copy(update={"evidence_sha256": content_sha256(evidence)})
    gate = _judge(_failed_receipt(), budget=(result, evidence))
    assert gate.status == "fail"
    assert gate.details["applied_exceptions"] == []
    assert "unknown" in gate.summary
