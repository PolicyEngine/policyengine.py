"""Trusted evidence boundaries and monotonic lineage for replay exceptions."""

from __future__ import annotations

import copy
import itertools

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import policyengine.provenance.qualification as qualification
from policyengine.provenance.qualification import qualification_verdict
from policyengine.provenance.receipt import content_sha256
from tests.qualification_fixtures import gates
from tests.test_qualification_contracts import _sealed
from tests.test_replay_exceptions import (
    INPUT,
    _budget_inputs,
    _entry,
    _failed_receipt,
    _judge,
    _registry,
    _source_mutant,
)

STATUS_KEYS = ("in_model", "is_input", "in_data", "usable")
BAD_CANDIDATE_STATUSES = [
    dict(zip(STATUS_KEYS, values, strict=True))
    for values in itertools.product((False, True), repeat=4)
    if values != (True, True, False, False)
]
BAD_PREVIOUS_STATUSES = [
    {"in_model": False, "is_input": True, "in_data": False, "usable": False},
    {"in_model": True, "is_input": True, "in_data": False, "usable": True},
    {"in_model": False, "is_input": False, "in_data": True, "usable": True},
]


def _reseal_budget(result, evidence):
    return result.model_copy(
        update={"evidence_sha256": content_sha256(evidence)}
    ), evidence


def _assert_rejected(replay):
    assert replay.status == "fail", replay.canonical_payload()
    assert replay.details["applied_exceptions"] == []
    assert qualification_verdict(gates(replay=replay.status)) == "rejected"


@pytest.mark.parametrize("candidate_state", BAD_CANDIDATE_STATUSES)
def test_candidate_status_must_agree_with_required_missing_input(candidate_state):
    """Includes all three candidate-status attacks from the independent review."""
    result, evidence = _budget_inputs()
    evidence["input_status"][INPUT] = candidate_state
    _assert_rejected(_judge(_failed_receipt(), budget=_reseal_budget(result, evidence)))


@pytest.mark.parametrize("previous_state", BAD_PREVIOUS_STATUSES)
def test_previous_status_fields_must_be_internally_consistent(previous_state):
    """Includes the review's is_input=True/in_model=False predecessor."""
    budget = _budget_inputs(previous_status={INPUT: previous_state})
    _assert_rejected(_judge(_failed_receipt(), budget=budget))


@settings(max_examples=45, deadline=None)
@given(
    year=st.integers(2025, 2029),
    target=st.sampled_from(["candidate", "previous"]),
    index=st.integers(0, len(BAD_CANDIDATE_STATUSES) - 1),
)
def test_contradictory_status_maps_never_qualify(year, target, index):
    result, evidence = _budget_inputs()
    if target == "candidate":
        evidence["input_status"][INPUT] = BAD_CANDIDATE_STATUSES[index]
    else:
        evidence["previous_input_status"][INPUT] = BAD_PREVIOUS_STATUSES[
            index % len(BAD_PREVIOUS_STATUSES)
        ]
    replay = _judge(
        _failed_receipt(year),
        registry=_registry(_entry(years=[year])),
        budget=_reseal_budget(result, evidence),
    )
    _assert_rejected(replay)


IDENTITY_DAMAGE = (
    "different_pair",
    "different_attempt",
    "missing_pair",
    "missing_attempt",
    "malformed_pair",
)


def _damage_identity(evidence, damage):
    if damage == "different_pair":
        evidence["pair_id"] = "f" * 64
    elif damage == "different_attempt":
        evidence["attempt_id"] += "-another"
    elif damage == "missing_pair":
        evidence.pop("pair_id")
    elif damage == "missing_attempt":
        evidence.pop("attempt_id")
    elif damage == "malformed_pair":
        evidence["pair_id"] = "not-a-pair-id"
    else:
        raise AssertionError(damage)


@pytest.mark.parametrize("damage", IDENTITY_DAMAGE)
def test_budget_evidence_identity_is_checked_after_digest_resealing(damage):
    result, evidence = _budget_inputs()
    _damage_identity(evidence, damage)
    _assert_rejected(_judge(_failed_receipt(), budget=_reseal_budget(result, evidence)))


@settings(max_examples=35, deadline=None)
@given(year=st.integers(2025, 2029), damage=st.sampled_from(IDENTITY_DAMAGE))
def test_mismatched_evidence_identity_never_qualifies(year, damage):
    result, evidence = _budget_inputs()
    _damage_identity(evidence, damage)
    replay = _judge(
        _failed_receipt(year),
        registry=_registry(_entry(years=[year])),
        budget=_reseal_budget(result, evidence),
    )
    _assert_rejected(replay)


@settings(max_examples=55, deadline=None)
@given(
    year=st.integers(2025, 2029),
    later_absent_pairs=st.integers(1, 15),
    noise=st.sets(st.sampled_from(["another_input", "old_input", "noise"])),
)
def test_ever_usable_input_cannot_reauthorize_after_any_absent_chain(
    year, later_absent_pairs, noise
):
    """Each later absent pair retains the same monotonic certified history."""
    history = sorted(noise | {INPUT})
    for _ in range(later_absent_pairs):
        result, evidence = _budget_inputs()
        evidence["previous_ever_usable_inputs"] = history
        evidence["ever_usable_inputs"] = history
        result = result.model_copy(
            update={"details": {**result.details, "ever_usable_inputs": history}}
        )
        replay = _judge(
            _failed_receipt(year),
            registry=_registry(_entry(years=[year])),
            budget=_reseal_budget(result, evidence),
        )
        _assert_rejected(replay)
        assert "a fresh registry decision is required" in str(replay.model_dump())


def test_head_level_invariant_kills_skip_head_coherence_mutant():
    mutant = _source_mutant(
        "        and row.head_gbp not in (None, 0)\n    ]",
        '        and row.level != "head" and row.head_gbp not in (None, 0)\n    ]',
    )
    document = _failed_receipt()
    row = copy.deepcopy(document["diff"]["flagged_rows"][0])
    row.update(level="head", key="income_tax", head_gbp=1_000_000_000)
    document["diff"]["flagged_rows"].append(row)
    for flag in row["flags"]:
        document["diff"]["flag_counts"][flag] += 1
    replay = _judge(_sealed(document), evaluator=mutant)
    with pytest.raises(AssertionError):
        _assert_rejected(replay)


def test_history_invariant_kills_predecessor_only_lineage_mutant(monkeypatch):
    mutant = _source_mutant(
        "if name in ever_usable_inputs:",
        'if state["usable"]:',
        function=qualification._replay_lineage_problem,
    )
    monkeypatch.setattr(qualification, "_replay_lineage_problem", mutant)
    result, evidence = _budget_inputs()
    evidence["previous_ever_usable_inputs"] = [INPUT]
    evidence["ever_usable_inputs"] = [INPUT]
    result = result.model_copy(
        update={"details": {**result.details, "ever_usable_inputs": [INPUT]}}
    )
    replay = _judge(_failed_receipt(), budget=_reseal_budget(result, evidence))
    with pytest.raises(AssertionError):
        _assert_rejected(replay)


def test_history_marker_invariant_kills_skip_marker_consistency_mutant(monkeypatch):
    result, evidence = _budget_inputs()
    # Both rehashed arrays erase a usable input still recorded by the producer.
    result = result.model_copy(
        update={"details": {**result.details, "ever_usable_inputs": [INPUT]}}
    )
    budget = _reseal_budget(result, evidence)
    _assert_rejected(_judge(_failed_receipt(), budget=budget))
    mutant = _source_mutant(
        "if recorded_ever is None or recorded_ever != _input_name_set(\n"
        '        evidence.get("ever_usable_inputs")\n'
        "    ):",
        "if False:",
        function=qualification._replay_missing_inputs,
    )
    monkeypatch.setattr(qualification, "_replay_missing_inputs", mutant)
    replay = _judge(_failed_receipt(), budget=budget)
    assert replay.status == "needs_review"
    assert replay.details["applied_exceptions"]
    with pytest.raises(AssertionError):
        _assert_rejected(replay)


def test_status_invariant_kills_skip_missing_map_consistency_mutant(monkeypatch):
    mutant = _source_mutant(
        "or missing\n        != {",
        "or False and missing\n        != {",
        function=qualification._replay_missing_inputs,
    )
    monkeypatch.setattr(qualification, "_replay_missing_inputs", mutant)
    result, evidence = _budget_inputs()
    evidence["input_status"][INPUT] = {
        "in_model": True,
        "is_input": True,
        "in_data": True,
        "usable": False,
    }
    replay = _judge(_failed_receipt(), budget=_reseal_budget(result, evidence))
    with pytest.raises(AssertionError):
        _assert_rejected(replay)


def test_identity_invariant_kills_skip_budget_identity_mutant(monkeypatch):
    mutant = _source_mutant(
        "or not _replay_budget_identity_matches(evidence, attempt_id)",
        "or False",
        function=qualification._replay_missing_inputs,
    )
    monkeypatch.setattr(qualification, "_replay_missing_inputs", mutant)
    result, evidence = _budget_inputs()
    _damage_identity(evidence, "different_attempt")
    replay = _judge(_failed_receipt(), budget=_reseal_budget(result, evidence))
    with pytest.raises(AssertionError):
        _assert_rejected(replay)
