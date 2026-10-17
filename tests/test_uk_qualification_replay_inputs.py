"""Replay exceptions use digest-bound input evidence from their own attempt."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from policyengine.provenance import uk_qualification
from policyengine.provenance.qualification import (
    GateResult,
    ReplayQualificationRequest,
    ReplayReceipt,
    ReplayStatus,
)
from policyengine.provenance.qualification_ledger import read_json, write_json
from policyengine.provenance.receipt import content_sha256
from tests.qualification_fixtures import HARNESS, ISSUED, gates, golden, make_pair


def _input_evidence(attempt):
    evidence = {
        "missing_inputs": ["additional_residential_property_purchased"],
        "newly_missing_inputs": ["additional_residential_property_purchased"],
    }
    result = GateResult(
        gate_id="budget_inputs",
        status="needs_review",
        summary="Purchase input is missing",
        evidence_sha256=content_sha256(evidence),
        details={
            "missing_inputs": len(evidence["missing_inputs"]),
            "newly_missing_inputs": evidence["newly_missing_inputs"],
        },
    )
    uk_qualification.write_gate_results(attempt, [result], {"budget_inputs": evidence})
    return result, evidence


def _replay_documents():
    request = ReplayQualificationRequest.model_validate(
        golden("qualification_request_golden")
    )
    receipt = ReplayReceipt.from_document(golden("replay_receipt_golden"))
    status = ReplayStatus.model_validate(
        {
            "schema": "policyengine.uk-replay-status/v1",
            "request_id": request.request_id,
            "status": "complete",
            "history": [
                {
                    "status": "complete",
                    "at": "2026-10-17T10:00:00Z",
                    "run_url": "https://github.com/PolicyEngine/policyengine-scorecard/actions/runs/1",
                }
            ],
            "receipt_sha256": receipt.receipt_sha256,
            "receipt_commit": "c" * 40,
        }
    )
    return request, status, receipt


@pytest.mark.parametrize(
    "damage",
    ["none", "no_result", "no_evidence", "changed_evidence", "wrong_gate", "no_digest"],
)
def test_attempt_input_evidence_is_bound_to_its_result(tmp_path, damage):
    result, evidence = _input_evidence(tmp_path)
    result_path = tmp_path / "gates/budget_inputs.result.json"
    evidence_path = tmp_path / "gates/budget_inputs.json"
    if damage == "no_result":
        result_path.unlink()
    elif damage == "no_evidence":
        evidence_path.unlink()
    elif damage == "changed_evidence":
        write_json(evidence_path, {**evidence, "missing_inputs": []})
    elif damage in {"wrong_gate", "no_digest"}:
        write_json(
            result_path,
            {
                **result.canonical_payload(),
                **(
                    {"gate_id": "another_gate"}
                    if damage == "wrong_gate"
                    else {"evidence_sha256": None}
                ),
            },
        )
    actual = uk_qualification.load_attempt_budget_inputs(tmp_path)
    assert actual == ((result, evidence) if damage == "none" else (None, None))


def test_input_evidence_does_not_fall_back_to_another_attempt(tmp_path):
    _input_evidence(tmp_path / "older_attempt")
    assert uk_qualification.load_attempt_budget_inputs(tmp_path / "this_attempt") == (
        None,
        None,
    )


def test_read_replay_threads_budget_input_evidence(tmp_path, monkeypatch):
    request, status, receipt = _replay_documents()
    result, evidence = _input_evidence(tmp_path)
    expected = GateResult(gate_id="replay", status="needs_review", summary="review")
    calls = []

    def evaluate(*args, **kwargs):
        calls.append((args, kwargs))
        return expected

    monkeypatch.setattr(uk_qualification, "evaluate_replay_receipt", evaluate)
    actual, _, _ = uk_qualification.read_replay(
        request,
        fetch=lambda ref, path: json.dumps(
            status.document() if path.endswith("STATUS.json") else receipt.document()
        ).encode(),
        state_ref="replay-state",
        budget_inputs_result=result,
        budget_inputs_evidence=evidence,
    )
    assert actual == expected
    assert calls[0][1] == {
        "budget_inputs_result": result,
        "budget_inputs_evidence": evidence,
    }


@pytest.mark.parametrize("alter_evidence", [False, True])
def test_finalize_reevaluates_replay_with_current_attempt_inputs(
    tmp_path, monkeypatch, alter_evidence
):
    attempt = tmp_path / "attempt"
    pair = make_pair()
    uk_qualification.stage_attempt(
        attempt,
        {"pair": pair.canonical_payload(), "previous_certificate": None},
        HARNESS,
    )
    uk_qualification.write_gate_results(attempt, gates(), {})
    result, evidence = _input_evidence(attempt)
    request, status, replay_receipt = _replay_documents()
    write_json(attempt / "replay/request.json", request.document())
    write_json(attempt / "replay/status.json", status.document())
    write_json(attempt / "replay/receipt.json", replay_receipt.document())
    write_json(
        attempt / "replay/replay.result.json",
        GateResult(
            gate_id="replay", status="pass", summary="stale"
        ).canonical_payload(),
    )
    if alter_evidence:
        write_json(attempt / "gates/budget_inputs.json", {"missing_inputs": []})
    calls = []

    def evaluate(*args, budget_inputs_result, budget_inputs_evidence):
        calls.append((budget_inputs_result, budget_inputs_evidence))
        return GateResult(
            gate_id="replay",
            status="needs_review" if budget_inputs_result else "fail",
            summary="Reevaluated with current evidence",
            details={
                "budget_inputs_result_sha256": (
                    content_sha256(budget_inputs_result.canonical_payload())
                    if budget_inputs_result
                    else None
                )
            },
        )

    monkeypatch.setattr(uk_qualification, "evaluate_replay_receipt", evaluate)
    receipt = uk_qualification.finalize_attempt(
        attempt,
        tmp_path / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-17T10:00:00Z",
    )
    assert calls == [((None, None) if alter_evidence else (result, evidence))]
    assert receipt.verdict == ("rejected" if alter_evidence else "needs_review")
    replay_gate = next(gate for gate in receipt.gates if gate.gate_id == "replay")
    assert (
        read_json(attempt / "replay/replay.result.json")
        == replay_gate.canonical_payload()
    )


def test_poll_replay_reads_same_attempt_inputs(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "check_uk_replay_inputs",
        Path(__file__).resolve().parents[1] / "scripts/check_uk_candidate.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    request, status, receipt = _replay_documents()
    result, evidence = _input_evidence(tmp_path)
    write_json(tmp_path / "replay/request.json", request.document())
    monkeypatch.setattr(
        cli,
        "config",
        lambda: {"replay": {"repository": "owner/scorecard", "state_ref": "state"}},
    )
    monkeypatch.setattr(cli, "scorecard_file", lambda _: "fetch")
    monkeypatch.setattr(cli, "set_output", lambda **_: None)
    calls = []

    def read(*args, **kwargs):
        calls.append(kwargs)
        return (
            GateResult(gate_id="replay", status="needs_review", summary="review"),
            status,
            receipt,
        )

    monkeypatch.setattr(cli, "read_replay", read)
    assert (
        cli.cmd_poll_replay(
            SimpleNamespace(attempt=str(tmp_path), wait_minutes=0, interval_seconds=1)
        )
        == 0
    )
    assert calls == [
        {
            "fetch": "fetch",
            "state_ref": "state",
            "budget_inputs_result": result,
            "budget_inputs_evidence": evidence,
        }
    ]


@pytest.mark.parametrize("raw_change", ["request", "status", "receipt", "running"])
@pytest.mark.parametrize("input_change", ["missing", "changed"])
def test_finalize_rejects_cached_exception_without_replay_bytes(
    tmp_path, raw_change, input_change
):
    attempt = tmp_path / "attempt"
    pair = make_pair()
    uk_qualification.stage_attempt(
        attempt,
        {"pair": pair.canonical_payload(), "previous_certificate": None},
        HARNESS,
    )
    uk_qualification.write_gate_results(attempt, gates(), {})
    _input_evidence(attempt)
    request, status, receipt = _replay_documents()
    write_json(attempt / "replay/request.json", request.document())
    write_json(attempt / "replay/status.json", status.document())
    write_json(attempt / "replay/receipt.json", receipt.document())
    write_json(
        attempt / "replay/replay.result.json",
        GateResult(
            gate_id="replay",
            status="needs_review",
            summary="Cached exception",
            details={"applied_exceptions": [{"id": "purchase-input", "year": 2026}]},
        ).canonical_payload(),
    )
    if raw_change == "running":
        write_json(
            attempt / "replay/status.json",
            {
                **status.document(),
                "status": "running",
                "receipt_sha256": None,
                "receipt_commit": None,
            },
        )
    else:
        (attempt / "replay" / f"{raw_change}.json").unlink()
    evidence_path = attempt / "gates/budget_inputs.json"
    if input_change == "missing":
        evidence_path.unlink()
    else:
        write_json(evidence_path, {"missing_inputs": []})
    finalized = uk_qualification.finalize_attempt(
        attempt,
        tmp_path / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-17T10:00:00Z",
    )
    replay_gate = next(gate for gate in finalized.gates if gate.gate_id == "replay")
    assert finalized.verdict == "rejected"
    assert replay_gate.status == "fail"
    assert replay_gate.details["regressions"] == [{"kind": "unverifiable_exception"}]
    assert (
        read_json(attempt / "replay/replay.result.json")
        == replay_gate.canonical_payload()
    )


@pytest.mark.parametrize("raw_change", ["request", "status", "receipt", "running"])
def test_finalize_preserves_legacy_cache_without_exceptions(tmp_path, raw_change):
    attempt = tmp_path / "attempt"
    pair = make_pair()
    uk_qualification.stage_attempt(
        attempt,
        {"pair": pair.canonical_payload(), "previous_certificate": None},
        HARNESS,
    )
    uk_qualification.write_gate_results(attempt, gates(), {})
    request, status, receipt = _replay_documents()
    write_json(attempt / "replay/request.json", request.document())
    write_json(attempt / "replay/status.json", status.document())
    write_json(attempt / "replay/receipt.json", receipt.document())
    cached = GateResult(gate_id="replay", status="pass", summary="Legacy cached replay")
    write_json(attempt / "replay/replay.result.json", cached.canonical_payload())
    if raw_change == "running":
        write_json(
            attempt / "replay/status.json",
            {**status.document(), "status": "running"},
        )
    else:
        (attempt / "replay" / f"{raw_change}.json").unlink()
    finalized = uk_qualification.finalize_attempt(
        attempt,
        tmp_path / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-17T10:00:00Z",
    )
    assert finalized.verdict == "qualified"
    assert next(gate for gate in finalized.gates if gate.gate_id == "replay") == cached


def test_finalize_real_failed_receipt_uses_same_attempt_input_evidence(tmp_path):
    from tests.test_qualification_contracts import _status
    from tests.test_replay_exceptions import _real_budget, _real_receipt

    attempt = tmp_path / "attempt"
    pair = make_pair()
    uk_qualification.stage_attempt(
        attempt,
        {"pair": pair.canonical_payload(), "previous_certificate": None},
        HARNESS,
    )
    uk_qualification.write_gate_results(attempt, gates(), {})
    budget_result, budget_evidence = _real_budget()
    uk_qualification.write_gate_results(
        attempt, [budget_result], {"budget_inputs": budget_evidence}
    )
    request, receipt = _real_receipt()
    write_json(attempt / "replay/request.json", request.document())
    write_json(
        attempt / "replay/status.json", _status(request.request_id, receipt).document()
    )
    write_json(attempt / "replay/receipt.json", receipt)
    finalized = uk_qualification.finalize_attempt(
        attempt,
        tmp_path / "ledger",
        issued_by=ISSUED,
        completed_at="2026-10-17T10:00:00Z",
    )
    replay_gate = next(gate for gate in finalized.gates if gate.gate_id == "replay")
    assert finalized.verdict == "needs_review", replay_gate.summary
    assert replay_gate.status == "needs_review"
    assert len(replay_gate.details["applied_exceptions"]) == 5
    assert sorted(
        item["year"] for item in replay_gate.details["applied_exceptions"]
    ) == list(range(2025, 2030))
    assert replay_gate.details["budget_inputs_result_sha256"] == content_sha256(
        budget_result.canonical_payload()
    )
