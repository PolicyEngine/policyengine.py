"""Independent attacks on the proposed data-limited exception policy.

These tests preserve the independent review attacks as regression checks.
Synthetic probe evidence and no representative microdata are used.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from policyengine.provenance.qualification import qualification_verdict
from policyengine.provenance.receipt import content_sha256
from policyengine.provenance.uk_candidate import budget_inputs
from tests.qualification_fixtures import gates, make_pair
from tests.test_qualification_contracts import _base_event, _sealed
from tests.test_replay_exceptions import (
    EVENT,
    INPUT,
    MEASURE,
    TEST_ATTEMPT_ID,
    _entry,
    _failed_receipt,
    _judge,
    _registry,
)


def _actual_budget(values, *, previously_missing):
    table = pd.DataFrame({"household_weight": [1.0, 2.0]})
    if values is not None:
        table[INPUT] = values
    result, evidence = budget_inputs(
        make_pair(),
        Path("unused.h5"),
        model_input_variables=["household_weight", INPUT],
        critical_inputs=["household_weight"],
        accepted_gaps={},
        previous_missing_inputs=[INPUT] if previously_missing else [],
        previous_input_status={
            INPUT: {
                "in_model": True,
                "is_input": True,
                "in_data": not previously_missing,
                "usable": not previously_missing,
            }
        },
        previous_unusable_critical=[],
        tables={"household": table},
    )
    evidence["attempt_id"] = TEST_ATTEMPT_ID
    return result.model_copy(
        update={"evidence_sha256": content_sha256(evidence)}
    ), evidence


def test_exception_cannot_reactivate_after_a_previously_supplied_input_is_dropped():
    """A previous usable input requires a fresh registry decision if lost."""
    document = _failed_receipt()
    supplied = _actual_budget([0, 100_000], previously_missing=True)
    dropped = _actual_budget(None, previously_missing=False)
    assert supplied[0].status == "pass"
    assert _judge(document, budget=supplied).status == "fail"
    assert dropped[0].status == "needs_review"
    assert dropped[1]["newly_missing_inputs"] == [INPUT]
    replay = _judge(document, budget=dropped)
    assert replay.status == "fail"
    assert "fresh registry decision" in str(replay.model_dump()).lower()
    combined = [
        dropped[0] if gate.gate_id == "budget_inputs" else gate
        for gate in gates(replay=replay.status)
    ]
    assert qualification_verdict(combined) == "rejected"


@pytest.mark.parametrize("year", [2025, 2026, 2029])
def test_different_inert_measure_in_the_registered_year_still_fails(year):
    document = _failed_receipt(year)
    other = "another_measure_disabled_by_a_model_regression"
    document["corpus"]["events"][EVENT]["inert_measure_years"].append(
        {"measure_key": other, "year": year}
    )
    document["integrity"]["failures"].append(
        {
            "code": "construction_inert",
            "detail": "A different measure also became inert.",
            "event": EVENT,
            "measure_key": other,
            "year": year,
        }
    )
    replay = _judge(_sealed(document), registry=_registry(_entry(years=[year])))
    assert replay.status == "fail"
    assert replay.details["applied_exceptions"] == []


@pytest.mark.parametrize("flag", ["mapping", "coverage"])
def test_matching_waiver_cannot_hide_an_unmatched_diff_failure(flag):
    document = _failed_receipt()
    document["diff"]["flagged_rows"].append(
        {
            "event": EVENT,
            "measure_key": "unrelated_lost_result",
            "year": 2026,
            "level": "measure_year",
            "key": "total",
            "flags": [flag],
            "base_gbp": 2_500_000_000,
            "head_gbp": None,
        }
    )
    document["diff"]["flag_counts"][flag] += 1
    replay = _judge(_sealed(document))
    assert replay.status == "fail"
    assert replay.details["applied_exceptions"]
    expected = "mapping" if flag == "mapping" else "lost_result"
    assert expected in {row["kind"] for row in replay.details["regressions"]}


@pytest.mark.parametrize("reverse_registry", [False, True])
def test_overlapping_registry_entries_cannot_produce_qualified(reverse_registry):
    # Partitioning a failure's codes between different reviewed entries must
    # preserve the review floor, independently of file ordering.
    entries = [
        _entry(id="integrity", codes=["construction_inert"]),
        _entry(id="lost-response", codes=["lost_response"]),
        _entry(id="zzz-overlap"),
    ]
    if reverse_registry:
        entries.reverse()
    replay = _judge(_failed_receipt(), registry=_registry(*entries))
    assert replay.status == "needs_review"
    assert qualification_verdict(gates(replay=replay.status)) == "needs_review"
    assert {row["id"] for row in replay.details["applied_exceptions"]} == {
        "integrity",
        "lost-response",
    }


def test_base_known_gap_cannot_remove_construction_exception_review_floor():
    document = _failed_receipt(rows=[])
    document["diff"]["base_events"] = {EVENT: _base_event(inert=[(MEASURE, 2026)])}
    replay = _judge(_sealed(document))
    assert replay.details["known_gaps"]
    assert replay.details["applied_exceptions"]
    assert replay.status == "needs_review"
    assert qualification_verdict(gates(replay=replay.status)) != "qualified"
