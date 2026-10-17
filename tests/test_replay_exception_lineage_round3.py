"""Certified cumulative history prevents a usable input from being forgotten."""

from __future__ import annotations

import copy
from pathlib import Path

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from policyengine.provenance.qualification import (
    PreviousCertificate,
    QualificationReceipt,
    ReplayQualificationRequest,
)
from policyengine.provenance.receipt import content_sha256
from policyengine.provenance.uk_candidate import budget_inputs
from tests.qualification_fixtures import gates, golden, make_pair, make_receipt
from tests.test_qualification_contracts import _receipt_with, _sealed
from tests.test_replay_exceptions import INPUT, _failed_receipt, _judge


def _coverage(pair, *, supplied=False, formula=False, removed=False, previous=None):
    inputs = ["household_weight"] + ([] if formula or removed else [INPUT])
    variables = ["household_weight"] + ([] if removed else [INPUT])
    table = pd.DataFrame({"household_weight": [1.0, 2.0]})
    if supplied:
        table[INPUT] = [0, 300_000]
    previous_status = previous[1]["input_status"] if previous else None
    # Mirror orchestration: retain old variables, including removed/formula
    # entries, while adding the candidate's newly introduced input names.
    if previous_status is not None:
        previous_status = dict(previous_status)
        for name in variables:
            previous_status.setdefault(
                name,
                {
                    "in_model": False,
                    "is_input": False,
                    "in_data": False,
                    "usable": False,
                },
            )
    result, evidence = budget_inputs(
        pair,
        Path("unused.h5"),
        model_input_variables=inputs,
        model_variables=variables,
        critical_inputs=["household_weight"],
        accepted_gaps={},
        previous_missing_inputs=previous[1]["missing_inputs"] if previous else None,
        previous_unusable_critical=[],
        previous_input_status=previous_status,
        previous_ever_usable_inputs=(
            previous[1]["ever_usable_inputs"] if previous else None
        ),
        tables={"household": table},
    )
    evidence["attempt_id"] = f"{pair.pair_id}/test-attempt"
    result = result.model_copy(update={"evidence_sha256": content_sha256(evidence)})
    return result, evidence


def _replay_for_pair(pair, document, coverage):
    raw = golden("qualification_request_golden")
    candidate = raw["candidate"]
    candidate["policyengine_uk"].update(
        version=pair.model.version, wheel_sha256=pair.model.wheel_sha256
    )
    candidate["policyengine_core"].update(
        version=pair.core.version, wheel_sha256=pair.core.wheel_sha256
    )
    candidate["data"].update(
        build_id=pair.data.build_id,
        revision=pair.data.dataset_revision,
        sha256=pair.data.dataset_sha256,
    )
    candidate["expected_release_bundle"].update(
        model_version=pair.model.version, data_version=pair.data.release_version
    )
    request = ReplayQualificationRequest.model_validate(raw)
    document["request_id"] = request.request_id
    document["execution"]["packages"]["policyengine-uk"].update(
        version=pair.model.version, wheel_sha256=pair.model.wheel_sha256
    )
    document["execution"]["packages"]["policyengine-core"].update(
        version=pair.core.version, wheel_sha256=pair.core.wheel_sha256
    )
    document["execution"]["release_bundle"] = candidate["expected_release_bundle"]
    document["execution"]["dataset_sha256"] = pair.data.dataset_sha256
    return _judge(
        _sealed(document),
        budget=coverage,
        request=request,
        attempt_id=f"{pair.pair_id}/test-attempt",
    )


def _qualification(pair, coverage, replay, previous=None):
    actual = {"budget_inputs": coverage[0], "replay": replay}
    receipt = make_receipt(
        pair,
        gate_results=[actual.get(gate.gate_id, gate) for gate in gates()],
    )
    if previous is not None:
        certificate = PreviousCertificate(
            bundle_version=previous.harness.policyengine_version,
            model_version=previous.pair.model.version,
            core_version=previous.pair.core.version,
            data_release_version=previous.pair.data.release_version,
            dataset_sha256=previous.pair.data.dataset_sha256,
            certificate_sha256=previous.receipt_sha256,
            qualification_pair_id=previous.pair_id,
            model_wheel_sha256=previous.pair.model.wheel_sha256,
            core_wheel_sha256=previous.pair.core.wheel_sha256,
        )
        receipt = receipt.model_copy(update={"previous_certificate": certificate})
    return QualificationReceipt.model_validate(receipt.canonical_payload())


@pytest.mark.parametrize("intermediate", ["formula", "removed"])
def test_three_pair_history_cannot_reactivate_expired_exception(
    intermediate,
):
    """A usable -> B absent/responding -> C absent/inert must be rejected.

    B's reform can respond through an alternate formula or another model input,
    so it needs no data-limited exception. Every gate and receipt is well formed.
    """
    pair_a = make_pair(model="2.135.0", data="1.59.0", dataset_sha="1" * 64)
    pair_b = make_pair(model="2.135.1", data="1.60.0", dataset_sha="2" * 64)
    pair_c = make_pair(model="2.135.2", data="1.61.0", dataset_sha="3" * 64)
    coverage_a = _coverage(pair_a, supplied=True)
    assert coverage_a[1]["input_status"][INPUT]["usable"] is True
    # A clean diff has no flagged row for the unchanged, responding measure;
    # C's subsequent diff records B's unchanged material £2.5bn base effect.
    responding = _receipt_with
    receipt_a = _qualification(
        pair_a, coverage_a, _replay_for_pair(pair_a, responding(), coverage_a)
    )
    assert receipt_a.promotable

    coverage_b = _coverage(
        pair_b,
        formula=intermediate == "formula",
        removed=intermediate == "removed",
        previous=coverage_a,
    )
    receipt_b = _qualification(
        pair_b,
        coverage_b,
        _replay_for_pair(pair_b, responding(), coverage_b),
        previous=receipt_a,
    )
    assert coverage_b[0].status == "pass"
    assert receipt_b.verdict == "qualified"
    assert receipt_b.promotable
    assert receipt_b.previous_certificate.qualification_pair_id == receipt_a.pair_id
    assert coverage_b[1]["previous_input_status"][INPUT]["usable"] is True
    assert INPUT in coverage_b[1]["ever_usable_inputs"]
    assert (
        next(g for g in receipt_b.gates if g.gate_id == "replay").details[
            "applied_exceptions"
        ]
        == []
    )

    coverage_c = _coverage(pair_c, previous=coverage_b)
    replay_c = _replay_for_pair(pair_c, _failed_receipt(), coverage_c)
    receipt_c = _qualification(pair_c, coverage_c, replay_c, previous=receipt_b)
    assert coverage_c[0].status == "needs_review"
    assert receipt_c.verdict == "rejected"
    assert receipt_c.previous_certificate.qualification_pair_id == receipt_b.pair_id
    assert replay_c.details["applied_exceptions"] == []
    assert "a fresh registry decision is required" in replay_c.summary


def test_rehashed_current_history_must_agree_with_its_result_marker():
    pair_a = make_pair(model="2.135.0", data="1.59.0", dataset_sha="1" * 64)
    pair_b = make_pair(model="2.135.1", data="1.60.0", dataset_sha="2" * 64)
    pair_c = make_pair(model="2.135.2", data="1.61.0", dataset_sha="3" * 64)
    coverage_a = _coverage(pair_a, supplied=True)
    coverage_b = _coverage(pair_b, removed=True, previous=coverage_a)
    result, evidence = _coverage(pair_c, previous=coverage_b)
    evidence = copy.deepcopy(evidence)
    # Rehashing both history arrays cannot erase the producer's independent
    # result marker, even after the immediate predecessor stopped using INPUT.
    assert INPUT in result.details["ever_usable_inputs"]
    assert evidence["previous_input_status"][INPUT]["usable"] is False
    for key in ("previous_ever_usable_inputs", "ever_usable_inputs"):
        evidence[key] = [name for name in evidence[key] if name != INPUT]
    result = result.model_copy(update={"evidence_sha256": content_sha256(evidence)})

    replay = _replay_for_pair(pair_c, _failed_receipt(), (result, evidence))

    assert replay.status == "fail"
    assert replay.details["applied_exceptions"] == []


@pytest.mark.parametrize("damage", ["missing", "malformed", "contradictory"])
def test_current_history_requires_a_valid_consistent_result_marker(damage):
    pair = make_pair()
    result, evidence = _coverage(pair, previous=_coverage(pair))
    control = _replay_for_pair(pair, _failed_receipt(), (result, evidence))
    assert control.status == "needs_review"
    assert len(control.details["applied_exceptions"]) == 1
    details = copy.deepcopy(result.details)
    if damage == "missing":
        details.pop("ever_usable_inputs")
    elif damage == "malformed":
        details["ever_usable_inputs"] = [True]
    else:
        details["ever_usable_inputs"] = []
    result = result.model_copy(update={"details": details})

    replay = _replay_for_pair(pair, _failed_receipt(), (result, evidence))

    assert replay.status == "fail"
    assert replay.details["applied_exceptions"] == []


def test_legacy_history_seed_uses_recomputed_predecessor_coverage():
    pair = make_pair()
    previous_status = {
        INPUT: {
            "in_model": True,
            "is_input": False,
            "in_data": True,
            "usable": True,
        },
    }
    _, evidence = budget_inputs(
        pair,
        Path("unused.h5"),
        model_input_variables=[INPUT],
        critical_inputs=[],
        accepted_gaps={},
        previous_missing_inputs=[],
        previous_unusable_critical=[],
        previous_input_status=previous_status,
        tables={"household": pd.DataFrame()},
    )
    assert evidence["pair_id"] == pair.pair_id
    assert evidence["previous_ever_usable_inputs"] == [INPUT]
    assert evidence["ever_usable_inputs"] == [INPUT]
    assert evidence["ever_usable_inputs_basis"] == "seeded from direct predecessor"


def test_formula_backed_supplied_candidate_seeds_cumulative_history():
    _, evidence = _coverage(make_pair(), supplied=True, formula=True)
    assert evidence["input_status"][INPUT]["is_input"] is False
    assert evidence["input_status"][INPUT]["usable"] is True
    assert INPUT in evidence["ever_usable_inputs"]
    assert evidence["ever_usable_inputs_basis"] == "candidate inputs"


@settings(max_examples=40, deadline=None)
@given(
    states=st.lists(
        st.sampled_from(["input", "formula", "removed"]), min_size=1, max_size=15
    )
)
def test_usable_input_history_survives_every_intermediate_model_state(states):
    pair = make_pair()
    coverage = _coverage(pair, supplied=True)
    for state in states:
        previous = coverage
        coverage = _coverage(
            pair,
            formula=state == "formula",
            removed=state == "removed",
            previous=previous,
        )
        assert INPUT in coverage[1]["previous_ever_usable_inputs"]
        assert INPUT in coverage[1]["ever_usable_inputs"]
        assert set(previous[1]["ever_usable_inputs"]).issubset(
            coverage[1]["ever_usable_inputs"]
        )
        assert coverage[1]["ever_usable_inputs_basis"] == (
            "carried from direct predecessor"
        )


@pytest.mark.parametrize("bad_history", [None, {}, [INPUT, INPUT], [True], [""]])
def test_malformed_certified_cumulative_history_cannot_be_reseeded(
    tmp_path, bad_history
):
    from policyengine.provenance.uk_candidate import (
        PreviousPairUnavailable,
        _previous_gate_evidence,
    )
    from tests.test_uk_candidate_gates import (
        _previous_identity,
        _write_previous_receipt,
    )

    pair = make_pair()
    _, evidence = _coverage(pair)
    evidence["ever_usable_inputs"] = bad_history
    _write_previous_receipt(
        tmp_path,
        pair,
        {
            "supported_years": {"supported_years": [2025, 2026]},
            "budget_inputs": evidence,
        },
    )
    with pytest.raises(PreviousPairUnavailable, match="fresh registry decision"):
        _previous_gate_evidence(tmp_path, _previous_identity(pair))


def test_cumulative_history_cannot_omit_a_current_usable_variable(tmp_path):
    from policyengine.provenance.uk_candidate import (
        PreviousPairUnavailable,
        _previous_gate_evidence,
    )
    from tests.test_uk_candidate_gates import (
        _previous_identity,
        _write_previous_receipt,
    )

    pair = make_pair()
    _, evidence = _coverage(pair, supplied=True)
    evidence["ever_usable_inputs"] = ["household_weight"]
    _write_previous_receipt(
        tmp_path,
        pair,
        {
            "supported_years": {"supported_years": [2025, 2026]},
            "budget_inputs": evidence,
        },
    )
    with pytest.raises(PreviousPairUnavailable, match="fresh registry decision"):
        _previous_gate_evidence(tmp_path, _previous_identity(pair))


@pytest.mark.parametrize("identity", ["pair_id", "attempt_id"])
def test_certified_cumulative_history_rejects_another_evidence_identity(
    tmp_path, identity
):
    from policyengine.provenance.uk_candidate import (
        PreviousPairUnavailable,
        _previous_gate_evidence,
    )
    from tests.test_uk_candidate_gates import (
        _previous_identity,
        _write_previous_receipt,
    )

    pair = make_pair()
    _, evidence = _coverage(pair)
    evidence[identity] = "another-attempt" if identity == "attempt_id" else "0" * 64
    _write_previous_receipt(
        tmp_path,
        pair,
        {
            "supported_years": {"supported_years": [2025, 2026]},
            "budget_inputs": evidence,
        },
    )
    with pytest.raises(PreviousPairUnavailable, match="another pair or attempt"):
        _previous_gate_evidence(tmp_path, _previous_identity(pair))


def test_damaged_cumulative_history_cannot_fall_back_to_a_fresh_seed(tmp_path):
    from policyengine.provenance.qualification_ledger import write_json
    from policyengine.provenance.uk_candidate import (
        PreviousPairUnavailable,
        _previous_gate_evidence,
    )
    from tests.test_uk_candidate_gates import (
        _previous_identity,
        _write_previous_receipt,
    )

    pair = make_pair()
    _, evidence = _coverage(pair, supplied=True)
    _, attempt = _write_previous_receipt(
        tmp_path,
        pair,
        {
            "supported_years": {"supported_years": [2025, 2026]},
            "budget_inputs": evidence,
        },
    )
    write_json(attempt / "gates" / "supported_years.json", {"supported_years": [2025]})
    with pytest.raises(PreviousPairUnavailable, match="fresh registry decision"):
        _previous_gate_evidence(tmp_path, _previous_identity(pair))


@pytest.mark.parametrize("gate_name", ["supported_years", "budget_inputs"])
@pytest.mark.parametrize("damage", ["missing", "invalid_json"])
def test_unreadable_certified_history_artifacts_cannot_reset_the_chain(
    tmp_path, gate_name, damage
):
    from policyengine.provenance.uk_candidate import (
        PreviousPairUnavailable,
        _previous_gate_evidence,
    )
    from tests.test_uk_candidate_gates import (
        _previous_identity,
        _write_previous_receipt,
    )

    pair = make_pair()
    _, evidence = _coverage(pair, supplied=True)
    _, attempt = _write_previous_receipt(
        tmp_path,
        pair,
        {
            "supported_years": {"supported_years": [2025, 2026]},
            "budget_inputs": evidence,
        },
    )
    path = attempt / "gates" / f"{gate_name}.json"
    if damage == "missing":
        path.unlink()
    else:
        path.write_text("not-json")
    with pytest.raises(PreviousPairUnavailable, match="fresh registry decision"):
        _previous_gate_evidence(tmp_path, _previous_identity(pair))


def test_certified_history_without_a_matching_attempt_cannot_reset_the_chain(tmp_path):
    from policyengine.provenance.uk_candidate import (
        PreviousPairUnavailable,
        _previous_gate_evidence,
    )
    from tests.test_uk_candidate_gates import (
        _previous_identity,
        _write_previous_receipt,
    )

    pair = make_pair()
    _, evidence = _coverage(pair, supplied=True)
    _, attempt = _write_previous_receipt(
        tmp_path,
        pair,
        {
            "supported_years": {"supported_years": [2025, 2026]},
            "budget_inputs": evidence,
        },
    )
    (attempt / "qualification_receipt.json").unlink()
    with pytest.raises(PreviousPairUnavailable, match="no matching attempt"):
        _previous_gate_evidence(tmp_path, _previous_identity(pair))


@pytest.mark.parametrize("unavailable", ["no_ledger", "missing_receipt", "bad_receipt"])
def test_unknown_certified_receipt_cannot_be_treated_as_legacy(tmp_path, unavailable):
    from policyengine.provenance.uk_candidate import (
        PreviousPairUnavailable,
        _previous_gate_evidence,
    )
    from tests.test_uk_candidate_gates import _previous_identity

    pair = make_pair()
    ledger_root = None if unavailable == "no_ledger" else tmp_path
    if unavailable == "bad_receipt":
        path = tmp_path / "uk" / pair.pair_id / "qualification_receipt.json"
        path.parent.mkdir(parents=True)
        path.write_text("not-json")
    with pytest.raises(PreviousPairUnavailable, match="fresh registry decision"):
        _previous_gate_evidence(ledger_root, _previous_identity(pair))


def test_true_legacy_certificate_without_a_bound_pair_can_still_be_recomputed():
    from policyengine.provenance.uk_candidate import _previous_gate_evidence

    assert _previous_gate_evidence(None, {"bundle_version": "6.0.0"}) == {}


@pytest.mark.parametrize(
    "pin", ["model_version", "dataset_sha256", "core_wheel_sha256"]
)
def test_mismatched_certified_pins_cannot_reset_a_recorded_history(tmp_path, pin):
    from policyengine.provenance.uk_candidate import (
        PreviousPairUnavailable,
        _previous_gate_evidence,
    )
    from tests.test_uk_candidate_gates import (
        _previous_identity,
        _write_previous_receipt,
    )

    pair = make_pair()
    _, evidence = _coverage(pair, supplied=True)
    _write_previous_receipt(
        tmp_path,
        pair,
        {
            "supported_years": {"supported_years": [2025, 2026]},
            "budget_inputs": evidence,
        },
    )
    previous = _previous_identity(pair)
    previous[pin] = "999.0.0" if pin == "model_version" else "0" * 64
    with pytest.raises(PreviousPairUnavailable, match="fresh registry decision"):
        _previous_gate_evidence(tmp_path, previous)
