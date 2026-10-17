"""Independent adversarial review probes for replay exception finalization.

The independent review's contradiction and stale-evidence reproducers now
assert fail-closed behavior for coherence, lineage and positive-input probes.
"""

from __future__ import annotations

import copy

import pandas as pd
import pytest

from policyengine.provenance import uk_candidate, uk_qualification
from policyengine.provenance.qualification import GateResult
from policyengine.provenance.qualification_ledger import read_json, write_json
from policyengine.provenance.receipt import content_sha256
from tests.qualification_fixtures import HARNESS, ISSUED, gates, make_pair
from tests.test_qualification_contracts import _sealed, _status
from tests.test_replay_exceptions import (
    EVENT,
    INPUT,
    _failed_receipt,
    _judge,
    _legacy_result,
    _probe,
    _real_budget,
    _real_receipt,
)


@pytest.mark.parametrize("head_gbp", [1_000_000_000, -1_000_000_000])
@pytest.mark.parametrize("lists_inert", [False, True])
def test_review_probe_nonzero_effect_with_construction_inert_failure(
    head_gbp, lists_inert
):
    """Identical construction worlds cannot produce a nonzero candidate effect."""

    document = _failed_receipt(
        rows=[
            {
                "flags": ["structural", "inertness"],
                "base_gbp": 2_500_000_000,
                "head_gbp": head_gbp,
            }
        ]
    )
    if not lists_inert:
        document["corpus"]["events"][EVENT]["inert_measure_years"] = []
        document["corpus"]["events"][EVENT]["full_supported_grid_complete"] = True
        document = _sealed(document)
    before = _legacy_result(document)
    after = _judge(document)
    assert before.status == "fail"
    assert after.status == "fail"
    assert after.details["regressions"]
    assert after.details["applied_exceptions"] == []


@pytest.mark.parametrize("level", ["measure_year", "source_row"])
def test_review_probe_production_registry_rejects_nonzero_inert_effect(level):
    request, document = _real_receipt()
    row = next(
        row
        for row in document["diff"]["flagged_rows"]
        if row["level"] == level
        and row["measure_key"]
        == "autumn_budget_2024__sdlt_additional_dwelling_surcharge_2pp"
    )
    row["head_gbp"] = 1_000_000_000
    document = _sealed(document)
    budget_result, budget_evidence = _real_budget()
    probe_result, probe_evidence = _probe(request=request)
    actual = uk_qualification.evaluate_replay_receipt(
        request,
        _status(request.request_id, document),
        uk_qualification.ReplayReceipt.from_document(document),
        budget_inputs_result=budget_result,
        budget_inputs_evidence=budget_evidence,
        probe_result=probe_result,
        probe_evidence=probe_evidence,
        attempt_id="test-attempt",
    )
    assert _legacy_result(document, request).status == "fail"
    assert actual.status == "fail"
    assert actual.details["regressions"]


@pytest.mark.parametrize("values", [[0, 0], [1, 1], [None, None]])
@pytest.mark.parametrize("critical", [False, True])
def test_present_degenerate_input_expires_exception_using_real_budget_gate(
    tmp_path, values, critical
):
    result, evidence = uk_candidate.budget_inputs(
        make_pair(),
        tmp_path / "unused.h5",
        model_input_variables=[INPUT],
        critical_inputs=[INPUT] if critical else [],
        accepted_gaps={},
        previous_missing_inputs=[INPUT],
        previous_unusable_critical=[],
        tables={"household": pd.DataFrame({INPUT: values})},
    )
    assert evidence["missing_inputs"] == []
    assert _judge(_failed_receipt(), budget=(result, evidence)).status == "fail"


def _stage_real_failed_attempt(tmp_path):
    attempt = tmp_path / "attempt"
    uk_qualification.stage_attempt(
        attempt,
        {"pair": make_pair().canonical_payload(), "previous_certificate": None},
        HARNESS,
    )
    uk_qualification.write_gate_results(attempt, gates(), {})
    budget_result, budget_evidence = _real_budget()
    uk_qualification.write_gate_results(
        attempt, [budget_result], {"budget_inputs": budget_evidence}
    )
    request, document = _real_receipt()
    probe_result, probe_evidence = _probe(
        request=request, attempt_id=uk_qualification.attempt_evidence_id(attempt)
    )
    uk_qualification.write_gate_results(
        attempt, [probe_result], {"replay_probe": probe_evidence}
    )
    write_json(attempt / "replay/request.json", request.document())
    write_json(
        attempt / "replay/status.json", _status(request.request_id, document).document()
    )
    write_json(attempt / "replay/receipt.json", document)
    # Use a real production-registry evaluation rather than the synthetic
    # registry _judge normally supplies.
    cached = uk_qualification.evaluate_replay_receipt(
        request,
        _status(request.request_id, document),
        uk_qualification.ReplayReceipt.from_document(document),
        budget_inputs_result=budget_result,
        budget_inputs_evidence=budget_evidence,
        probe_result=probe_result,
        probe_evidence=probe_evidence,
        attempt_id=uk_qualification.attempt_evidence_id(attempt),
    )
    assert cached.status == "needs_review"
    write_json(attempt / "replay/replay.result.json", cached.canonical_payload())
    return attempt, budget_result, budget_evidence


@pytest.mark.parametrize(
    "change", ["digest_mismatch", "present_with_new_digest", "missing_files"]
)
def test_finalize_rejects_stale_real_exception_when_input_evidence_changes(
    tmp_path, change
):
    attempt, result, evidence = _stage_real_failed_attempt(tmp_path)
    if change == "missing_files":
        (attempt / "gates/budget_inputs.json").unlink()
    else:
        evidence = copy.deepcopy(evidence)
        evidence["missing_inputs"].remove(INPUT)
        evidence["newly_missing_inputs"].remove(INPUT)
        write_json(attempt / "gates/budget_inputs.json", evidence)
        if change == "present_with_new_digest":
            details = copy.deepcopy(result.details)
            details["missing_inputs"] -= 1
            details["newly_missing_inputs"].remove(INPUT)
            replacement = GateResult(
                **{
                    **result.canonical_payload(),
                    "evidence_sha256": content_sha256(evidence),
                    "details": details,
                }
            )
            write_json(
                attempt / "gates/budget_inputs.result.json",
                replacement.canonical_payload(),
            )
    finalized = uk_qualification.finalize_attempt(
        attempt,
        tmp_path / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-17T10:00:00Z",
    )
    actual = next(gate for gate in finalized.gates if gate.gate_id == "replay")
    assert finalized.verdict == "rejected"
    assert actual.status == "fail"
    assert actual.details["applied_exceptions"] == []
    assert (
        read_json(attempt / "replay/replay.result.json") == actual.canonical_payload()
    )


@pytest.mark.parametrize("changed", ["receipt", "status"])
def test_finalize_rejects_cached_exception_after_raw_binding_changes(tmp_path, changed):
    attempt, _, _ = _stage_real_failed_attempt(tmp_path)
    if changed == "receipt":
        path = attempt / "replay/receipt.json"
        document = read_json(path)
        document["integrity"]["failures"][0]["detail"] += " changed after polling"
        write_json(path, _sealed(document))
    else:
        path = attempt / "replay/status.json"
        document = read_json(path)
        document["request_id"] = "0" * 64
        write_json(path, document)
    finalized = uk_qualification.finalize_attempt(
        attempt,
        tmp_path / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-17T10:00:00Z",
    )
    actual = next(gate for gate in finalized.gates if gate.gate_id == "replay")
    assert finalized.verdict == "rejected"
    assert actual.details["regressions"][0]["kind"] == "unbound"


@pytest.mark.parametrize(
    "change",
    ["digest_mismatch", "failed_with_new_digest", "wrong_attempt", "missing_files"],
)
def test_finalize_rechecks_probe_evidence_for_the_same_attempt(tmp_path, change):
    attempt, _, _ = _stage_real_failed_attempt(tmp_path)
    evidence_path = attempt / "gates/replay_probe.json"
    result_path = attempt / "gates/replay_probe.result.json"
    if change == "missing_files":
        evidence_path.unlink()
    else:
        evidence = read_json(evidence_path)
        if change == "wrong_attempt":
            evidence["attempt_id"] = "previous-attempt"
        else:
            evidence["probes"][0]["status"] = "fail"
        write_json(evidence_path, evidence)
        if change != "digest_mismatch":
            result = GateResult.model_validate(read_json(result_path))
            result = result.model_copy(
                update={"evidence_sha256": content_sha256(evidence)}
            )
            write_json(result_path, result.canonical_payload())
    finalized = uk_qualification.finalize_attempt(
        attempt,
        tmp_path / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-17T10:00:00Z",
    )
    actual = next(gate for gate in finalized.gates if gate.gate_id == "replay")
    assert finalized.verdict == "rejected"
    assert actual.status == "fail"
    assert actual.details["applied_exceptions"] == []
    assert (
        read_json(attempt / "replay/replay.result.json") == actual.canonical_payload()
    )


def test_finalize_rejects_a_newly_usable_previous_lineage(tmp_path):
    attempt, result, evidence = _stage_real_failed_attempt(tmp_path)
    evidence["previous_input_status"][INPUT] = {
        "in_model": True,
        "in_data": True,
        "usable": True,
    }
    write_json(attempt / "gates/budget_inputs.json", evidence)
    result = result.model_copy(update={"evidence_sha256": content_sha256(evidence)})
    write_json(attempt / "gates/budget_inputs.result.json", result.canonical_payload())
    finalized = uk_qualification.finalize_attempt(
        attempt,
        tmp_path / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-17T10:00:00Z",
    )
    actual = next(gate for gate in finalized.gates if gate.gate_id == "replay")
    assert finalized.verdict == "rejected"
    assert actual.status == "fail"
    assert "fresh registry decision" in str(actual.model_dump()).lower()
