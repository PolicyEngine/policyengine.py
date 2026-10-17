"""Data-limited replay exceptions retain a review floor and expire with inputs.

The copied real fixtures contain national aggregates and provenance metadata only.
A frozen v1 evaluator provides a differential oracle for unchanged receipt cases.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

import policyengine.provenance.qualification as qualification
from policyengine.provenance.qualification import (
    GateResult,
    ReplayDataLimitedException,
    ReplayExceptionRegistry,
    ReplayQualificationRequest,
    ReplayReceipt,
    evaluate_replay_receipt,
    qualification_verdict,
)
from policyengine.provenance.receipt import content_sha256
from tests.qualification_fixtures import FIXTURES, gates, golden, make_pair
from tests.test_qualification_contracts import (
    CONTRADICTIONS,
    EVENT,
    KNOWN_GAP_CASES,
    MEASURE,
    POLICY_CASES,
    _base_event,
    _clean_receipt,
    _edit,
    _receipt_with,
    _rejected_receipt,
    _sealed,
    _status,
    _with_requested_wheels,
)

EXCEPTION_FIXTURES = Path(__file__).parent / "fixtures" / "replay_exceptions"
INPUT = "additional_residential_property_purchased"
TEST_ATTEMPT_ID = f"{make_pair().pair_id}/test-attempt"
RANK = {"pass": 0, "needs_review": 1, "unavailable": 2, "fail": 3, "error": 3}
EXCEPTION_METADATA = {
    "exception_registry_sha256",
    "applied_exceptions",
    "budget_inputs_result_sha256",
    "probe_result_sha256",
    "probe_evidence_sha256",
}


def _json(name):
    return json.loads((EXCEPTION_FIXTURES / name).read_text())


def _main_evaluator():
    namespace = dict(vars(qualification))
    metadata = _json("main_policy_metadata.json")
    namespace.update(
        REPLAY_POLICY_ID=metadata["policy"],
        replay_policy_sha256=lambda: metadata["policy_sha256"],
    )
    source = (EXCEPTION_FIXTURES / "main_replay_policy.py.txt").read_text()
    exec(compile(source, "frozen_main_replay_policy", "exec"), namespace)
    return namespace["evaluate_replay_receipt"]


MAIN_EVALUATOR = _main_evaluator()


def _entry(**overrides):
    return {
        "id": "test-purchase-input",
        "codes": ["construction_inert", "lost_response"],
        "event": EVENT,
        "measure_key": MEASURE,
        "years": [2026],
        "requires_missing_inputs": [INPUT],
        "cause": "Purchases are absent from the candidate data.",
        "issue": "PolicyEngine/policyengine-uk-data#573",
        "decided_under": "cos d1344",
        "review": "Independent review required before adoption.",
        "approved_lineage": "Never supplied usably by any certified data release.",
        "publication": "Not computable while the input is unavailable.",
        "probe": {
            "input_variable": overrides.get("requires_missing_inputs", [INPUT])[0],
            "input_entity": "household",
            "year": 2026,
            "positive_input_gbp": 300_000,
            "output_variable": "sdlt_on_residential_property_transactions",
            "parameter": "gov.hmrc.stamp_duty.residential.purchase.additional.rate",
            "rate_increment": 0.02,
            "expected_change_gbp": 6_000,
            "absolute_tolerance_gbp": 1,
            "region": "LONDON",
        },
        **overrides,
    }


def _registry(*entries):
    return ReplayExceptionRegistry.model_validate({"exceptions": list(entries)})


def _budget_inputs(
    missing=(INPUT,),
    *,
    status="needs_review",
    newly_missing=None,
    previous_status=None,
    attempt_id=TEST_ATTEMPT_ID,
    request=None,
):
    previous = (
        {
            name: {
                "in_model": False,
                "is_input": False,
                "in_data": False,
                "usable": False,
            }
            for name in {*missing, INPUT}
        }
        if previous_status is None
        else {
            name: {"is_input": state.get("in_model", False), **state}
            for name, state in previous_status.items()
        }
    )
    previous_ever = sorted(
        name for name, state in previous.items() if state.get("usable")
    )
    states = {
        name: {
            "in_model": True,
            "is_input": True,
            "in_data": name not in missing,
            "usable": name not in missing,
        }
        for name in {*missing, INPUT}
    }
    evidence = {
        "pair_id": attempt_id.partition("/")[0],
        "attempt_id": attempt_id,
        "input_status": states,
        "previous_input_status": previous,
        "previous_ever_usable_inputs": previous_ever,
        "ever_usable_inputs": sorted(
            set(previous_ever)
            | {name for name, state in states.items() if state["usable"]}
        ),
        "ever_usable_inputs_basis": "seeded from direct predecessor",
        "missing_inputs": sorted(missing),
        "newly_missing_inputs": sorted(
            missing if newly_missing is None else newly_missing
        ),
    }
    result = GateResult(
        gate_id="budget_inputs",
        status=status,
        summary="Candidate input coverage.",
        evidence_sha256=content_sha256(evidence),
        details={
            "missing_inputs": len(missing),
            "newly_missing_inputs": evidence["newly_missing_inputs"],
        },
    )
    return result, evidence


def _probe(registry=None, request=None, *, attempt_id=TEST_ATTEMPT_ID):
    """Build same-attempt evidence matching every registered probe specification."""
    if registry is None:
        registry, _ = qualification._replay_exceptions()
    if request is None:
        request = ReplayQualificationRequest.model_validate(
            golden("qualification_request_golden")
        )
    evidence = {
        "attempt_id": attempt_id,
        "candidate_model_version": request.candidate.policyengine_uk.version,
        "probes": [
            {
                "exception_id": entry.id,
                "spec_sha256": content_sha256(entry.probe.model_dump(mode="json")),
                "status": "pass",
                "installed_model_version": request.candidate.policyengine_uk.version,
                "positive_baseline_gbp": 0,
                "positive_reform_gbp": entry.probe.expected_change_gbp,
                "zero_baseline_gbp": 0,
                "zero_reform_gbp": 0,
                "positive_change_gbp": entry.probe.expected_change_gbp,
                "zero_change_gbp": 0,
            }
            for entry in registry.exceptions
        ],
    }
    return (
        GateResult(
            gate_id="replay_probe",
            status="pass",
            summary="Synthetic positive-input and zero-input probes passed.",
            evidence_sha256=content_sha256(evidence),
        ),
        evidence,
    )


def _failed_receipt(year=2026, *, extra_failures=(), rows=None):
    rows = (
        [{"flags": ["structural", "inertness"], "base_gbp": 2.5e9, "head_gbp": 0}]
        if rows is None
        else rows
    )
    document = _receipt_with(
        [{"year": year, **row} for row in rows],
        inert=[(MEASURE, year)],
        missing=[],
        complete=False,
        integrity="failed",
        sealed=False,
    )
    document["status"] = "failed"
    document["integrity"]["failures"] = [
        {
            "code": "construction_inert",
            "detail": "Identical worlds because the input is absent.",
            "event": EVENT,
            "measure_key": MEASURE,
            "year": year,
        },
        *extra_failures,
    ]
    return _sealed(document)


def _judge(
    document,
    *,
    registry=None,
    budget=None,
    probe="default",
    request=None,
    evaluator=None,
    attempt_id=TEST_ATTEMPT_ID,
):
    request = request or ReplayQualificationRequest.model_validate(
        golden("qualification_request_golden")
    )
    result, evidence = budget if budget is not None else _budget_inputs()
    evaluator = evaluator or evaluate_replay_receipt
    registry = registry if registry is not None else _registry(_entry())
    probe_result, probe_evidence = (
        _probe(registry, request, attempt_id=attempt_id)
        if probe == "default"
        else probe
    )
    return evaluator(
        request,
        _status(request.request_id, document),
        ReplayReceipt.from_document(document),
        exception_registry=registry,
        budget_inputs_result=result,
        budget_inputs_evidence=evidence,
        probe_result=probe_result,
        probe_evidence=probe_evidence,
        attempt_id=attempt_id,
    )


def _legacy_result(document, request=None):
    request = request or ReplayQualificationRequest.model_validate(
        golden("qualification_request_golden")
    )
    return MAIN_EVALUATOR(
        request,
        _status(request.request_id, document),
        ReplayReceipt.from_document(document),
    )


def _unchanged_payload(gate):
    """Policy version and mandatory new provenance fields are the only allowance."""
    payload = gate.model_dump(mode="json")
    for key in EXCEPTION_METADATA | {"policy", "policy_sha256"}:
        payload["details"].pop(key, None)
    return payload


def _assert_narrow_mismatch_unchanged(
    dimension, year=2026, noise=(), *, evaluator=None
):
    entry = _entry(years=[year])
    document = _failed_receipt(year)
    budget = _budget_inputs([INPUT, *noise])
    if dimension == "code":
        entry["codes"] = ["lost_response"]
    elif dimension == "event":
        entry["event"] = "another_event"
    elif dimension == "measure_key":
        entry["measure_key"] = "another_measure"
    elif dimension == "year":
        entry["years"] = [year + 1]
    elif dimension == "missing_input":
        budget = _budget_inputs(noise)
    elif dimension == "extra_failure":
        document["integrity"]["failures"].append(
            {"code": "event_outputs_missing", "detail": "Unrelated missing output."}
        )
    else:
        raise AssertionError(dimension)
    document = _sealed(document)
    gate = _judge(
        document, registry=_registry(entry), budget=budget, evaluator=evaluator
    )
    legacy = _legacy_result(document)
    assert gate.status == legacy.status == "fail"
    assert _unchanged_payload(gate) == _unchanged_payload(legacy)


@settings(max_examples=65, deadline=None)
@given(
    year=st.integers(2025, 2029),
    other_years=st.sets(st.integers(2024, 2035), max_size=5),
    missing=st.sets(st.sampled_from([INPUT, "other_input", "persistent_input"])),
    distractor_count=st.integers(0, 3),
    status=st.sampled_from(["pass", "needs_review", "fail"]),
)
def test_applied_exceptions_always_require_a_named_review(
    year, other_years, missing, distractor_count, status
):
    """Invariant 1: arbitrary valid registries and input results retain the floor."""
    missing = sorted(missing | {INPUT})
    registry = _registry(
        _entry(years=sorted(other_years | {year})),
        *[
            _entry(id=f"unrelated-{i}", event=f"unrelated_event_{i}")
            for i in range(distractor_count)
        ],
    )
    gate = _judge(
        _failed_receipt(year),
        registry=registry,
        budget=_budget_inputs(missing, status=status),
    )
    assert gate.status == "needs_review", gate.summary
    assert qualification_verdict(gates(replay=gate.status)) == "needs_review"
    assert len(gate.details["applied_exceptions"]) == 1
    assert gate.details["applied_exceptions"][0]["year"] == year
    assert set(gate.details["applied_exceptions"][0]["codes"]) == {
        "construction_inert",
        "lost_response",
    }
    items = gate.details["review_items"]
    assert any(
        item.get("exception_id") == "test-purchase-input"
        and item.get("publication") == _entry()["publication"]
        and item.get("approved_lineage") == _entry()["approved_lineage"]
        and item.get("cause") == _entry()["cause"]
        and INPUT in item.get("requires_missing_inputs", [])
        for item in items
    )


@settings(max_examples=90, deadline=None)
@given(
    dimension=st.sampled_from(
        ["code", "event", "measure_key", "year", "missing_input", "extra_failure"]
    ),
    year=st.integers(2025, 2029),
    noise=st.sets(st.sampled_from(["irrelevant_input", "other_input"])),
)
def test_unmatched_fields_and_extra_integrity_failures_are_noops(
    dimension, year, noise
):
    """Invariant 2: each narrow mismatch preserves the old failed verdict."""
    _assert_narrow_mismatch_unchanged(dimension, year, sorted(noise))


def _existing_receipt_cases():
    cases = []
    for name, case in POLICY_CASES.items():
        rows, inert, complete, integrity, *_ = case
        cases.append((name, _receipt_with(rows, inert, complete, integrity), None))
    for name, case in KNOWN_GAP_CASES.items():
        inert, missing, unsupported, base_events, *_ = case
        cases.append(
            (
                f"known-gap: {name}",
                _receipt_with(
                    inert=inert,
                    missing=missing,
                    unsupported=unsupported,
                    base_events=base_events,
                    complete=not (inert or missing),
                    integrity="incomplete" if inert or missing else "complete",
                ),
                None,
            )
        )
    for name, edit in CONTRADICTIONS.items():
        cases.append((name, _edit(_clean_receipt(), edit), None))
    cases.extend(
        [
            ("rejected", _rejected_receipt(), None),
            ("failed", _failed_receipt(), None),
            (
                "golden",
                _sealed(_with_requested_wheels(golden("replay_receipt_golden"))),
                None,
            ),
        ]
    )
    for folder in [FIXTURES / "receipt_6.4.1_attempt1", FIXTURES / "receipt_6.5.0"]:
        request = ReplayQualificationRequest.model_validate(
            json.loads((folder / "REQUEST.json").read_text())
        )
        cases.append(
            (
                folder.name,
                json.loads((folder / "REPLAY_RECEIPT.json").read_text()),
                request,
            )
        )
    return cases


@pytest.mark.parametrize(
    ("name", "document", "replay_request"),
    _existing_receipt_cases(),
    ids=[case[0] for case in _existing_receipt_cases()],
)
def test_empty_registry_preserves_existing_replay_receipts(
    name, document, replay_request
):
    """Invariant 3: all existing decision-table and real-fixture receipt cases."""
    current = _judge(document, request=replay_request, registry=_registry())
    legacy = _legacy_result(document, request=replay_request)
    assert _unchanged_payload(current) == _unchanged_payload(legacy), name


@settings(max_examples=80, deadline=None)
@given(
    year=st.integers(2025, 2029),
    included=st.booleans(),
    extra_kind=st.sampled_from(["mapping", "lost_response"]),
    extra_year=st.integers(2024, 2035),
    extra_base=st.sampled_from([1e6, -1e6, 2.5e9]),
)
def test_adding_a_regression_never_improves_a_verdict(
    year, included, extra_kind, extra_year, extra_base
):
    """Invariant 4 covers both matched and unmatched new regression rows."""
    registry = _registry(_entry(years=[year] if included else [year + 1]))
    document = _failed_receipt(year)
    before = _judge(document, registry=registry)
    row = {
        **document["diff"]["flagged_rows"][0],
        "flags": ["mapping" if extra_kind == "mapping" else "structural"],
        "year": extra_year,
        "base_gbp": extra_base,
        "head_gbp": 0,
    }
    document["diff"]["flagged_rows"].append(row)
    for flag in row["flags"]:
        document["diff"]["flag_counts"][flag] += 1
    after = _judge(_sealed(document), registry=registry)
    assert RANK[after.status] >= RANK[before.status]
    if extra_kind == "mapping" or extra_year != year:
        assert after.status == "fail"


@settings(max_examples=45, deadline=None)
@given(
    years=st.sets(st.integers(2025, 2029), min_size=1),
    missing=st.sets(st.sampled_from([INPUT, "another_input"])),
    codes=st.lists(
        st.sampled_from(["construction_inert", "lost_response"]),
        min_size=1,
        unique=True,
    ),
)
def test_exception_evaluation_and_recorded_digests_are_deterministic(
    years, missing, codes
):
    """Invariant 5 compares every result field, including all provenance digests."""
    registry = _registry(_entry(years=sorted(years), codes=codes))
    document = _failed_receipt(min(years))
    budget = _budget_inputs(sorted(missing))
    first = _judge(document, registry=registry, budget=budget)
    second = _judge(copy.deepcopy(document), registry=registry, budget=budget)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.details["exception_registry_sha256"] == content_sha256(
        registry.canonical_payload()
    )
    if first.details["applied_exceptions"]:
        assert first.details["budget_inputs_result_sha256"] == content_sha256(
            budget[0].canonical_payload()
        )
    else:
        assert first.details["budget_inputs_result_sha256"] is None


def _real_receipt():
    """Recreate the unavailable REQUEST from execution, retaining original aggregates.

    The archived fixture has no request document. Its bytes and digest remain
    unchanged on disk; only a test copy receives this reconstructed request id.
    """
    document = _json("replay_receipt_uk2.134.7_failed.json")
    raw = golden("qualification_request_golden")
    execution = document["execution"]
    candidate = raw["candidate"]
    candidate["policyengine"].update(
        version=execution["packages"]["policyengine"]["version"],
        packaged_bundle_manifest_sha256=execution["packaged_bundle_manifest_sha256"],
    )
    for name, field in [
        ("policyengine-uk", "policyengine_uk"),
        ("policyengine-core", "policyengine_core"),
    ]:
        candidate[field] = {
            key: execution["packages"][name][key] for key in ("version", "wheel_sha256")
        }
    candidate["data"]["sha256"] = execution["dataset_sha256"]
    candidate["expected_release_bundle"] = execution["release_bundle"]
    request = ReplayQualificationRequest.model_validate(raw)
    document["request_id"] = request.request_id
    return request, _sealed(document)


def _real_budget(*, attempt_id=TEST_ATTEMPT_ID, request=None):
    """Add explicit never-usable lineage to copies of the archived evidence."""
    evidence = _json("uk2.134.7_budget_inputs.json")
    evidence.update(
        {
            "pair_id": attempt_id.partition("/")[0],
            "attempt_id": attempt_id,
            "input_status": {
                name: {
                    "in_model": True,
                    "is_input": True,
                    "in_data": False,
                    "usable": False,
                }
                for name in evidence["missing_inputs"]
            },
            "previous_input_status": {
                INPUT: {
                    "in_model": False,
                    "is_input": False,
                    "in_data": False,
                    "usable": False,
                }
            },
            "previous_ever_usable_inputs": [],
            "ever_usable_inputs": [],
            "ever_usable_inputs_basis": "seeded from direct predecessor",
        }
    )
    result = GateResult.model_validate(_json("uk2.134.7_budget_inputs.result.json"))
    return result.model_copy(
        update={"evidence_sha256": content_sha256(evidence)}
    ), evidence


def test_real_21347_failed_receipt_has_exactly_five_reviewed_measure_years():
    """Invariant 6: the production registry handles the real data limitation."""
    request, document = _real_receipt()
    budget = _real_budget()
    receipt = ReplayReceipt.from_document(document)
    probe_result, probe_evidence = _probe(request=request)
    gate = evaluate_replay_receipt(
        request,
        _status(request.request_id, document),
        receipt,
        budget_inputs_result=budget[0],
        budget_inputs_evidence=budget[1],
        probe_result=probe_result,
        probe_evidence=probe_evidence,
        attempt_id=TEST_ATTEMPT_ID,
    )
    assert gate.status == "needs_review", gate.summary
    applied = gate.details["applied_exceptions"]
    assert len(applied) == 5
    assert {item["id"] for item in applied} == {"ab2024-sdlt-hrad-purchase-input"}
    assert sorted(item["year"] for item in applied) == list(range(2025, 2030))
    assert all(
        set(item["codes"]) == {"construction_inert", "lost_response"}
        for item in applied
    )
    assert gate.details["regressions"] == []
    assert all(item["publication"] for item in applied)
    assert gate.details["probe_result_sha256"] == content_sha256(
        probe_result.canonical_payload()
    )
    assert gate.details["probe_evidence_sha256"] == content_sha256(probe_evidence)
    assert gate.details["budget_inputs_result_sha256"] == content_sha256(
        budget[0].canonical_payload()
    )
    registry_file = (
        Path(qualification.__file__).parents[1]
        / "data/qualification/uk_replay_exceptions.json"
    )
    assert (
        gate.details["exception_registry_sha256"]
        == hashlib.sha256(registry_file.read_bytes()).hexdigest()
    )


@pytest.mark.parametrize("change", ["input_available", "extra_integrity_failure"])
def test_real_21347_receipt_fails_when_exception_conditions_no_longer_hold(change):
    request, document = _real_receipt()
    result, evidence = _real_budget()
    if change == "input_available":
        evidence["missing_inputs"].remove(INPUT)
        evidence["newly_missing_inputs"].remove(INPUT)
        details = copy.deepcopy(result.details)
        details["newly_missing_inputs"].remove(INPUT)
        details["missing_inputs"] -= 1
        result = result.model_copy(
            update={"details": details, "evidence_sha256": content_sha256(evidence)}
        )
    else:
        document["integrity"]["failures"].append(
            {"code": "event_outputs_missing", "detail": "Synthetic unrelated failure."}
        )
        document = _sealed(document)
    probe_result, probe_evidence = _probe(request=request)
    gate = evaluate_replay_receipt(
        request,
        _status(request.request_id, document),
        ReplayReceipt.from_document(document),
        budget_inputs_result=result,
        budget_inputs_evidence=evidence,
        probe_result=probe_result,
        probe_evidence=probe_evidence,
        attempt_id=TEST_ATTEMPT_ID,
    )
    assert gate.status == "fail"


@pytest.mark.parametrize("status", ["error", "unavailable"])
def test_unavailable_budget_inputs_cannot_authorize_an_exception(status):
    gate = _judge(_failed_receipt(), budget=_budget_inputs(status=status))
    assert gate.status == "fail"


@pytest.mark.parametrize(
    "change", ["wrong_gate", "wrong_digest", "missing_result", "missing_evidence"]
)
def test_unbound_budget_input_evidence_cannot_authorize_an_exception(change):
    result, evidence = _budget_inputs()
    if change == "wrong_gate":
        result = result.model_copy(update={"gate_id": "some_other_gate"})
    elif change == "wrong_digest":
        result = result.model_copy(update={"evidence_sha256": "0" * 64})
    elif change == "missing_result":
        result = None
    else:
        evidence = None
    assert _judge(_failed_receipt(), budget=(result, evidence)).status == "fail"


def test_inputs_missing_in_both_pairs_still_authorize_review():
    gate = _judge(_failed_receipt(), budget=_budget_inputs(newly_missing=[]))
    assert gate.status == "needs_review"


def test_exception_never_excuses_a_base_gap_with_a_material_value():
    document = _failed_receipt()
    document["diff"]["base_events"] = {EVENT: _base_event(inert=[(MEASURE, 2026)])}
    assert _judge(_sealed(document)).status == "fail"


def test_exception_never_excuses_failures_under_complete_integrity():
    document = _failed_receipt()
    document["status"] = "complete"
    document["integrity"]["status"] = "complete"
    assert _judge(_sealed(document)).status == "fail"


@pytest.mark.parametrize("codes", [["event_run_failed"], ["mapping"], ["incomplete"]])
def test_registry_cannot_expand_the_exception_to_other_failure_kinds(codes):
    with pytest.raises(ValidationError):
        _registry(_entry(codes=codes))


@pytest.mark.parametrize(
    "dropped", ["code", "event", "measure_key", "year", "missing_input"]
)
def test_narrow_match_invariants_kill_five_predicate_mutants(monkeypatch, dropped):
    """Execute actual matcher replacements; the invariant assertion kills each.

    Mutants remove the code, event, measure key, year, or missing-input predicate.
    The unmodified invariant is exercised above by Hypothesis as well.
    """

    def mutant(self, code, event, measure_key, year, missing_inputs):
        predicates = {
            "code": code in self.codes,
            "event": event == self.event,
            "measure_key": measure_key == self.measure_key,
            "year": year in self.years,
            "missing_input": set(self.requires_missing_inputs) <= missing_inputs,
        }
        return all(value for key, value in predicates.items() if key != dropped)

    monkeypatch.setattr(ReplayDataLimitedException, "matches", mutant)
    with pytest.raises(AssertionError):
        _assert_narrow_mismatch_unchanged(dropped)


def test_registry_preserves_comment_through_json_roundtrip():
    registry = ReplayExceptionRegistry.model_validate(
        {"_comment": "Reviewed like code.", "exceptions": [_entry()]}
    )
    assert (
        ReplayExceptionRegistry.model_validate_json(registry.model_dump_json())
        == registry
    )
    payload = registry.canonical_payload()
    assert payload["_comment"] == "Reviewed like code."
    assert ReplayExceptionRegistry.model_validate(payload) == registry


@pytest.mark.parametrize("code", ["lost_response", "event_run_failed", "mapping"])
def test_only_construction_inert_can_be_excepted_as_a_receipt_failure(code):
    document = _failed_receipt()
    document["integrity"]["failures"][0]["code"] = code
    assert _judge(_sealed(document)).status == "fail"


def test_a_missing_result_is_not_excused_when_it_is_also_listed_inert():
    document = _failed_receipt()
    document["corpus"]["events"][EVENT]["missing_measure_years"] = [
        {"measure_key": MEASURE, "year": 2026}
    ]
    assert _judge(_sealed(document)).status == "fail"


def _source_mutant(before, after, function=evaluate_replay_receipt):
    source = dedent(inspect.getsource(function))
    assert source.count(before) == 1, (
        "Mutation site changed; update this explicit mutant."
    )
    namespace = dict(vars(qualification))
    exec(
        compile(source.replace(before, after), "mutant_replay_policy", "exec"),
        namespace,
    )
    return namespace[function.__name__]


def test_extra_failure_invariant_kills_all_to_any_mutant():
    mutant = _source_mutant("and all(\n", "and any(\n")
    with pytest.raises(AssertionError):
        _assert_narrow_mismatch_unchanged("extra_failure", evaluator=mutant)


def test_review_floor_invariant_kills_automatic_pass_mutant():
    mutant = _source_mutant(
        'if review_items:\n        return GateResult(\n            gate_id="replay",\n            status="needs_review",',
        'if review_items:\n        return GateResult(\n            gate_id="replay",\n            status="pass",',
    )
    with pytest.raises(AssertionError):
        gate = _judge(_failed_receipt(rows=[]), evaluator=mutant)
        assert qualification_verdict(gates(replay=gate.status)) != "qualified"


def test_every_existing_replay_evaluation_matches_main_with_an_empty_registry(tmp_path):
    """Invariant 3 also covers each generated receipt in the full existing suite.

    A child pytest wraps the suite's evaluator; every invocation is compared
    with the frozen main policy, including receipts created by Hypothesis.
    """
    plugin = tmp_path / "replay_differential_plugin.py"
    plugin.write_text(
        """from tests.test_replay_exceptions import (
    MAIN_EVALUATOR, _registry, _unchanged_payload,
)
from policyengine.provenance.qualification import evaluate_replay_receipt

count = 0

def pytest_collection_modifyitems(items):
    modules = {item.module for item in items}
    for module in modules:
        if module.__name__ == "tests.test_qualification_contracts":
            module.evaluate_replay_receipt = compare

def compare(*args, **kwargs):
    global count
    actual = evaluate_replay_receipt(*args, **kwargs, exception_registry=_registry())
    expected = MAIN_EVALUATOR(*args)
    assert _unchanged_payload(actual) == _unchanged_payload(expected)
    count += 1
    return actual

def pytest_terminal_summary(terminalreporter):
    assert count > 0
    terminalreporter.write_line(f"Differential replay evaluations: {count}")
"""
    )
    environment = dict(os.environ)
    environment["POLICYENGINE_SKIP_COUNTRY_IMPORTS"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(tmp_path), environment.get("PYTHONPATH", "")]
    )
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--noconftest",
            "tests/test_qualification_contracts.py",
            "-p",
            "replay_differential_plugin",
            "-q",
        ],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "Differential replay evaluations:" in run.stdout


def _assert_every_required_input_missing(required, missing, *, year=2026):
    document = _failed_receipt(year)
    gate = _judge(
        document,
        registry=_registry(_entry(years=[year], requires_missing_inputs=required)),
        budget=_budget_inputs(sorted(missing)),
    )
    if set(required) <= set(missing):
        assert gate.status == "needs_review"
        assert gate.details["applied_exceptions"]
        assert set(
            gate.details["applied_exceptions"][0]["requires_missing_inputs"]
        ) == set(required)
    else:
        assert gate.status == "fail"
        assert _unchanged_payload(gate) == _unchanged_payload(_legacy_result(document))


@settings(max_examples=80, deadline=None)
@given(
    required=st.lists(
        st.sampled_from([INPUT, "second_required_input", "third_required_input"]),
        min_size=2,
        max_size=3,
        unique=True,
    ),
    missing=st.sets(
        st.sampled_from(
            [INPUT, "second_required_input", "third_required_input", "unrelated_input"]
        )
    ),
    year=st.integers(2025, 2029),
)
def test_every_required_missing_input_must_be_reported_missing(required, missing, year):
    """Invariant 2 requires all names, including multi-input registry entries."""
    _assert_every_required_input_missing(required, missing, year=year)


def test_required_input_invariant_kills_subset_to_any_mutant(monkeypatch):
    mutant = _source_mutant(
        "set(self.requires_missing_inputs) <= missing_inputs",
        "bool(set(self.requires_missing_inputs) & missing_inputs)",
        function=ReplayDataLimitedException.matches,
    )
    monkeypatch.setattr(ReplayDataLimitedException, "matches", mutant)
    with pytest.raises(AssertionError):
        _assert_every_required_input_missing([INPUT, "second_required_input"], [INPUT])


def _assert_diff_only_exception(*, input_missing=True, base=2.5e9, evaluator=None):
    document = _receipt_with(
        rows=[{"flags": ["structural"], "base_gbp": base, "head_gbp": 0}],
        inert=[],
        complete=True,
        integrity="complete",
    )
    gate = _judge(
        document,
        registry=_registry(_entry(codes=["lost_response"])),
        budget=_budget_inputs([INPUT] if input_missing else []),
        evaluator=evaluator,
    )
    if input_missing:
        assert gate.status == "needs_review"
        assert len(gate.details["applied_exceptions"]) == 1
        assert gate.details["applied_exceptions"][0]["codes"] == ["lost_response"]
        assert gate.details["regressions"] == []
    else:
        assert gate.status == "fail"
        assert _unchanged_payload(gate) == _unchanged_payload(_legacy_result(document))


@pytest.mark.parametrize("input_missing", [True, False])
@pytest.mark.parametrize("base", [1e6, -1e6, 2.5e9])
def test_diff_only_lost_response_requires_the_missing_input(input_missing, base):
    """The £0 total branch works without corpus inertness or integrity failures."""
    _assert_diff_only_exception(input_missing=input_missing, base=base)


def test_diff_only_invariant_kills_mutant_removing_zero_total_exception():
    mutant = _source_mutant(
        'if not except_regression(record, "lost_response"):', "if True:"
    )
    with pytest.raises(AssertionError):
        _assert_diff_only_exception(evaluator=mutant)


@settings(max_examples=80, deadline=None)
@given(
    value=st.floats(allow_nan=False, allow_infinity=False).filter(
        lambda value: value != 0
    ),
    level=st.sampled_from(["measure_year", "source_row"]),
    base_known_gap=st.booleans(),
)
def test_any_nonzero_candidate_effect_prevents_an_exception(
    value, level, base_known_gap
):
    document = _failed_receipt()
    row = copy.deepcopy(document["diff"]["flagged_rows"][0])
    row.update(level=level, key="total" if level == "measure_year" else "source-1")
    row["head_gbp"] = value
    if level == "measure_year":
        document["diff"]["flagged_rows"][0] = row
    else:
        document["diff"]["flagged_rows"].append(row)
        for flag in row["flags"]:
            document["diff"]["flag_counts"][flag] += 1
    if base_known_gap:
        document["diff"]["base_events"] = {EVENT: _base_event(inert=[(MEASURE, 2026)])}
    gate = _judge(_sealed(document))
    assert gate.status == "fail"
    assert gate.details["applied_exceptions"] == []
    assert gate.details["regressions"]


@settings(max_examples=40, deadline=None)
@given(
    year=st.integers(2025, 2029),
    missing=st.sets(st.sampled_from([INPUT, "another_input", "noise"])),
)
def test_a_previously_usable_input_never_authorizes_the_exception(year, missing):
    gate = _judge(
        _failed_receipt(year),
        registry=_registry(_entry(years=[year])),
        budget=_budget_inputs(
            sorted(missing | {INPUT}),
            previous_status={
                INPUT: {"in_model": True, "in_data": True, "usable": True}
            },
        ),
    )
    assert gate.status == "fail"
    assert gate.details["applied_exceptions"] == []
    assert "fresh registry decision" in str(gate.model_dump()).lower()


def test_missing_previous_input_lineage_fails_closed():
    gate = _judge(_failed_receipt(), budget=_budget_inputs(previous_status={}))
    assert gate.status == "fail"
    assert gate.details["applied_exceptions"] == []


def _invalid_probe(change, registry=None, request=None):
    result, evidence = _probe(registry or _registry(_entry()), request)
    if change == "missing_result":
        return None, evidence
    if change == "missing_evidence":
        return result, None
    if change == "wrong_digest":
        return result.model_copy(update={"evidence_sha256": "0" * 64}), evidence
    if change == "wrong_gate":
        return result.model_copy(update={"gate_id": "other_probe"}), evidence
    if change == "failed_result":
        return result.model_copy(update={"status": "fail"}), evidence
    if change == "failed_probe":
        evidence["probes"][0]["status"] = "fail"
    elif change == "missing_probe":
        evidence["probes"] = []
    elif change == "wrong_spec":
        evidence["probes"][0]["spec_sha256"] = "0" * 64
    elif change == "wrong_attempt":
        evidence["attempt_id"] = "another-attempt"
    elif change == "wrong_model":
        evidence["candidate_model_version"] = "0.0.0"
    elif change == "zero_control_moves":
        evidence["probes"][0]["zero_change_gbp"] = 1
    elif change == "positive_control_inert":
        evidence["probes"][0]["positive_change_gbp"] = 0
    else:
        raise AssertionError(change)
    return result.model_copy(
        update={"evidence_sha256": content_sha256(evidence)}
    ), evidence


PROBE_FAILURES = [
    "missing_result",
    "missing_evidence",
    "wrong_digest",
    "wrong_gate",
    "failed_result",
    "failed_probe",
    "missing_probe",
    "wrong_spec",
    "wrong_attempt",
    "wrong_model",
    "zero_control_moves",
    "positive_control_inert",
]


@settings(max_examples=45, deadline=None)
@given(change=st.sampled_from(PROBE_FAILURES), year=st.integers(2025, 2029))
def test_failing_missing_or_unbound_probe_never_authorizes_an_exception(change, year):
    registry = _registry(_entry(years=[year]))
    gate = _judge(
        _failed_receipt(year), registry=registry, probe=_invalid_probe(change, registry)
    )
    assert gate.status == "fail"
    assert gate.details["applied_exceptions"] == []


def test_real_21347_receipt_fails_without_a_positive_input_probe():
    request, document = _real_receipt()
    registry, _ = qualification._replay_exceptions()
    gate = _judge(
        document,
        registry=registry,
        request=request,
        budget=_real_budget(),
        probe=(None, None),
    )
    assert gate.status == "fail"
    assert gate.details["applied_exceptions"] == []


def test_nonzero_effect_invariant_kills_skip_coherence_mutant():
    mutant = _source_mutant(
        "        and row.head_gbp not in (None, 0)\n    ]",
        "        and False\n    ]",
    )
    document = _failed_receipt(
        rows=[
            {
                "flags": ["structural", "inertness"],
                "base_gbp": 2.5e9,
                "head_gbp": 1_000_000_000,
            }
        ]
    )
    gate = _judge(document, evaluator=mutant)
    with pytest.raises(AssertionError):
        assert gate.status == "fail"


def test_previously_usable_invariant_kills_skip_lineage_mutant():
    mutant = _source_mutant("if lineage_problem is not None:", "if False:")
    budget = _budget_inputs(
        previous_status={
            INPUT: {"in_model": True, "in_data": True, "usable": True},
        }
    )
    gate = _judge(_failed_receipt(), budget=budget, evaluator=mutant)
    with pytest.raises(AssertionError):
        assert gate.status == "fail"


def test_failing_probe_invariant_kills_skip_probe_mutant():
    mutant = _source_mutant(
        """if not _replay_probe_passes(
                entry, request, probe_result, probe_evidence, attempt_id
            ):""",
        "if False:",
    )
    gate = _judge(
        _failed_receipt(), evaluator=mutant, probe=_invalid_probe("failed_probe")
    )
    with pytest.raises(AssertionError):
        assert gate.status == "fail"


def test_same_attempt_invariant_kills_accept_another_attempt_mutant(monkeypatch):
    mutant = _source_mutant(
        '        or evidence.get("attempt_id") != attempt_id\n',
        "",
        function=qualification._replay_probe_passes,
    )
    monkeypatch.setattr(qualification, "_replay_probe_passes", mutant)
    gate = _judge(_failed_receipt(), probe=_invalid_probe("wrong_attempt"))
    with pytest.raises(AssertionError):
        assert gate.status == "fail"
