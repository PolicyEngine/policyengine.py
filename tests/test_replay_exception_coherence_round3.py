"""Independent review regressions reject incoherence at every reported level."""

from __future__ import annotations

import copy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from policyengine.provenance import uk_qualification
from policyengine.provenance.qualification import (
    ReplayReceipt,
    evaluate_replay_receipt,
    qualification_verdict,
)
from policyengine.provenance.qualification_ledger import read_json, write_json
from tests.qualification_fixtures import ISSUED, gates
from tests.test_qualification_contracts import _base_event, _sealed, _status
from tests.test_replay_exception_finalize_review import _stage_real_failed_attempt
from tests.test_replay_exceptions import (
    EVENT,
    MEASURE,
    TEST_ATTEMPT_ID,
    _failed_receipt,
    _judge,
    _probe,
    _real_budget,
    _real_receipt,
)


@pytest.mark.parametrize("level", ["measure_year", "source_row", "head"])
@pytest.mark.parametrize("effect", [1_000_000_000, -1_000_000_000])
@pytest.mark.parametrize("lists_inert", [False, True])
@pytest.mark.parametrize("base_known_gap", [False, True])
def test_every_receipt_row_level_rejects_nonzero_excepted_effect(
    level, effect, lists_inert, base_known_gap
):
    document = _failed_receipt()
    row = copy.deepcopy(document["diff"]["flagged_rows"][0])
    row.update(level=level, key="income_tax" if level == "head" else "row-1")
    row["head_gbp"] = effect
    document["diff"]["flagged_rows"].append(row)
    for flag in row["flags"]:
        document["diff"]["flag_counts"][flag] += 1
    if not lists_inert:
        document["corpus"]["events"][EVENT]["inert_measure_years"] = []
        document["corpus"]["events"][EVENT]["full_supported_grid_complete"] = True
    if base_known_gap:
        document["diff"]["base_events"] = {EVENT: _base_event(inert=[(MEASURE, 2026)])}
    replay = _judge(_sealed(document))
    assert replay.status == "fail", replay.canonical_payload()


def test_finalizer_rejects_nonzero_fiscal_head_in_excepted_real_measure(tmp_path):
    attempt, _, _ = _stage_real_failed_attempt(tmp_path)
    document = read_json(attempt / "replay/receipt.json")
    row = next(
        row
        for row in document["diff"]["flagged_rows"]
        if row["level"] == "head"
        and row["measure_key"]
        == "autumn_budget_2024__sdlt_additional_dwelling_surcharge_2pp"
        and row["year"] == 2026
    )
    row["head_gbp"] = 1_000_000_000
    document = _sealed(document)
    write_json(attempt / "replay/receipt.json", document)
    write_json(
        attempt / "replay/status.json",
        _status(document["request_id"], document).document(),
    )
    finalized = uk_qualification.finalize_attempt(
        attempt,
        tmp_path / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-17T10:00:00Z",
    )
    assert finalized.verdict == "rejected", finalized.canonical_payload()


@pytest.mark.parametrize("level", ["measure_year", "source_row", "head"])
@pytest.mark.parametrize("effect", [1_000_000_000, -1_000_000_000])
def test_archived_real_receipt_rejects_nonzero_excepted_effect_at_every_level(
    level, effect
):
    request, document = _real_receipt()
    row = next(
        row
        for row in document["diff"]["flagged_rows"]
        if row["level"] == level
        and row["measure_key"]
        == "autumn_budget_2024__sdlt_additional_dwelling_surcharge_2pp"
    )
    row["head_gbp"] = effect
    document = _sealed(document)
    budget_result, budget_evidence = _real_budget()
    probe_result, probe_evidence = _probe(request=request)
    replay = evaluate_replay_receipt(
        request,
        _status(request.request_id, document),
        ReplayReceipt.from_document(document),
        budget_inputs_result=budget_result,
        budget_inputs_evidence=budget_evidence,
        probe_result=probe_result,
        probe_evidence=probe_evidence,
        attempt_id=TEST_ATTEMPT_ID,
    )
    assert replay.status == "fail", replay.canonical_payload()


@settings(max_examples=75, deadline=None)
@given(
    level=st.sampled_from(["head", "source_row", "measure_year"]),
    effect=st.one_of(
        st.floats(min_value=1e-12, max_value=1e15, allow_nan=False),
        st.floats(min_value=-1e15, max_value=-1e-12, allow_nan=False),
    ),
    lists_inert=st.booleans(),
    base_known_gap=st.booleans(),
)
def test_any_nonzero_reported_level_forbids_exception_and_qualification(
    level, effect, lists_inert, base_known_gap
):
    document = _failed_receipt()
    row = copy.deepcopy(document["diff"]["flagged_rows"][0])
    row.update(level=level, key="income_tax" if level == "head" else "source-1")
    row["head_gbp"] = effect
    document["diff"]["flagged_rows"].append(row)
    for flag in row["flags"]:
        document["diff"]["flag_counts"][flag] += 1
    if not lists_inert:
        document["corpus"]["events"][EVENT]["inert_measure_years"] = []
        document["corpus"]["events"][EVENT]["full_supported_grid_complete"] = True
    if base_known_gap:
        document["diff"]["base_events"] = {EVENT: _base_event(inert=[(MEASURE, 2026)])}
    replay = _judge(_sealed(document))
    assert replay.status == "fail"
    assert replay.details["applied_exceptions"] == []
    assert qualification_verdict(gates(replay=replay.status)) == "rejected"
