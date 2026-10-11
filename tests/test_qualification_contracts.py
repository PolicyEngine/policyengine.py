"""Candidate qualification contracts, promotion order and the replay interface.

Invariants:

- the verdict is a pure, monotone function of the gate results: making any
  gate worse never makes the verdict better, and a missing gate is never
  qualified;
- a review acceptance is bound to the exact receipt it accepts;
- promotion picks the newest promotable pair that strictly advances the
  certified pair, whatever order receipts arrive in, and never moves
  backwards;
- the replay request, status and receipt mirrors agree with the scorecard's
  vendored JSON Schemas and reproduce its golden digests (differential);
- a replay receipt counts only when bound to this request and these
  artifacts; blocking flags fail, review flags need review.
"""

from __future__ import annotations

import copy
import json

import jsonschema
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from policyengine.provenance.canonical import canonical_sha256
from policyengine.provenance.qualification import (
    REQUIRED_GATES,
    GateResult,
    ReplayQualificationRequest,
    ReplayReceipt,
    ReplayStatus,
    ReviewAcceptance,
    dominates,
    evaluate_replay_receipt,
    qualification_verdict,
    select_promotion_target,
)
from tests.qualification_fixtures import (
    FIXTURES,
    VENDORED_SCHEMAS,
    gates,
    golden,
    make_pair,
    make_receipt,
    sha,
)

STATUSES = ["pass", "needs_review", "unavailable", "fail", "error"]
SEVERITY = {"pass": 0, "needs_review": 1, "unavailable": 2, "fail": 3, "error": 3}
VERDICT_RANK = {"qualified": 0, "needs_review": 1, "incomplete": 2, "rejected": 3}


# --- Verdict ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "verdict"),
    [
        ({}, "qualified"),
        ({"replay": "needs_review"}, "needs_review"),
        ({"reform_contract": "unavailable"}, "incomplete"),
        ({"metrics_review": "unavailable", "replay": "needs_review"}, "incomplete"),
        ({"wheel_hashes": "fail", "replay": "unavailable"}, "rejected"),
        ({"budget_inputs": "error"}, "rejected"),
    ],
)
def test_verdict_examples(overrides, verdict):
    assert qualification_verdict(gates(**overrides)) == verdict


def test_a_missing_required_gate_is_never_qualified():
    for gate_id in REQUIRED_GATES:
        partial = [gate for gate in gates() if gate.gate_id != gate_id]
        assert qualification_verdict(partial) == "incomplete"


@settings(max_examples=300, deadline=None)
@given(
    statuses=st.lists(
        st.sampled_from(STATUSES),
        min_size=len(REQUIRED_GATES),
        max_size=len(REQUIRED_GATES),
    ),
    index=st.integers(0, len(REQUIRED_GATES) - 1),
    worse=st.sampled_from(STATUSES),
)
def test_worsening_a_gate_never_improves_the_verdict(statuses, index, worse):
    before = [
        GateResult(gate_id=gate_id, status=status, summary="x")
        for gate_id, status in zip(REQUIRED_GATES, statuses)
    ]
    if SEVERITY[worse] < SEVERITY[statuses[index]]:
        return
    after = list(before)
    after[index] = GateResult(gate_id=REQUIRED_GATES[index], status=worse, summary="x")
    assert (
        VERDICT_RANK[qualification_verdict(after)]
        >= VERDICT_RANK[qualification_verdict(before)]
    )


def test_receipt_verdict_must_follow_from_gates():
    receipt = make_receipt(gate_results=gates(replay="needs_review"))
    payload = receipt.model_dump(mode="json")
    payload["verdict"] = "qualified"
    with pytest.raises(ValidationError):
        type(receipt).model_validate(payload)


def test_pair_id_must_be_the_pair_digest():
    payload = make_receipt().model_dump(mode="json")
    payload["pair_id"] = sha("0")
    with pytest.raises(ValidationError):
        type(make_receipt()).model_validate(payload)


# --- Review acceptance -----------------------------------------------------------


def _accepted(receipt, digest=None):
    return receipt.model_copy(
        update={
            "review": ReviewAcceptance(
                reviewer="vahid",
                accepted_at="2026-10-16T10:00:00Z",
                accepted_receipt_sha256=digest or receipt.unreviewed_sha256,
                explanation="UC moves follow the documented #2242 uplift.",
            )
        }
    )


def test_only_the_accepted_receipt_is_promotable():
    receipt = make_receipt(gate_results=gates(replay="needs_review"))
    assert not receipt.promotable
    assert _accepted(receipt).promotable
    assert not _accepted(receipt, digest=sha("1")).promotable
    changed = receipt.model_copy(update={"completed_at": "2026-10-17T00:00:00Z"})
    stale_acceptance = _accepted(changed, digest=receipt.unreviewed_sha256)
    assert not stale_acceptance.promotable


def test_review_cannot_attach_to_a_rejected_receipt():
    receipt = make_receipt(gate_results=gates(wheel_hashes="fail"))
    with pytest.raises(ValidationError):
        type(receipt).model_validate(
            {
                **receipt.model_dump(mode="json"),
                "review": _accepted(
                    make_receipt(gate_results=gates(replay="needs_review"))
                ).review.model_dump(),
            }
        )


# --- Promotion order --------------------------------------------------------------

VERSIONS = st.tuples(
    st.sampled_from(["2.125.1", "2.126.6", "2.126.8", "2.127.0"]),
    st.sampled_from(["1.58.0", "1.59.0", "1.60.0"]),
    st.sampled_from(["3.33.0", "3.33.1"]),
)


@settings(max_examples=200, deadline=None)
@given(a=VERSIONS, b=VERSIONS, c=VERSIONS)
def test_dominance_is_a_strict_partial_order(a, b, c):
    assert not dominates(a, a)
    assert not (dominates(a, b) and dominates(b, a))
    if dominates(a, b) and dominates(b, c):
        assert dominates(a, c)


RECEIPT_SPECS = st.lists(
    st.tuples(
        VERSIONS, st.sampled_from(["pass", "needs_review", "fail", "unavailable"])
    ),
    min_size=0,
    max_size=6,
)


def _receipts(specs):
    receipts = []
    for index, ((model, data, core), status) in enumerate(specs):
        receipts.append(
            make_receipt(
                pair=make_pair(model=model, data=data, core=core),
                gate_results=gates(replay=status),
                completed_at=f"2026-10-15T09:00:{index:02d}Z",
            )
        )
    return receipts


@settings(max_examples=200, deadline=None)
@given(specs=RECEIPT_SPECS, current=VERSIONS, data=st.data())
def test_promotion_target_is_order_independent_and_never_backwards(
    specs, current, data
):
    receipts = _receipts(specs)
    shuffled = data.draw(st.permutations(receipts))
    target = select_promotion_target(receipts, current)
    assert select_promotion_target(shuffled, current) == target
    if target is None:
        return
    assert target.promotable
    assert dominates(target.pair.order_key, current)
    for other in receipts:
        if other.promotable and dominates(other.pair.order_key, current):
            key = other.pair.order_key
            assert key == target.pair.order_key or dominates(target.pair.order_key, key)


def test_a_stale_completion_cannot_displace_a_newer_accepted_candidate():
    newer = make_receipt(
        pair=make_pair(model="2.126.8"), completed_at="2026-10-15T09:00:00Z"
    )
    stale = make_receipt(
        pair=make_pair(model="2.126.6"), completed_at="2026-10-15T12:00:00Z"
    )
    current = ("2.125.1", "1.58.0", "3.33.0")
    assert select_promotion_target([newer, stale], current) == newer
    assert select_promotion_target([stale, newer], current) == newer


def test_incomparable_newest_pairs_promote_nothing_automatically():
    newer_model = make_receipt(pair=make_pair(model="2.127.0", data="1.58.0"))
    newer_data = make_receipt(pair=make_pair(model="2.126.8", data="1.59.0"))
    assert (
        select_promotion_target(
            [newer_model, newer_data], ("2.125.1", "1.58.0", "3.33.0")
        )
        is None
    )


# --- Replay interface: mirrors agree with the vendored schemas ---------------


def _validator(name):
    schema = json.loads((VENDORED_SCHEMAS / name).read_text())
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )


def test_golden_request_round_trips_with_its_digest():
    raw = golden("qualification_request_golden")
    request = ReplayQualificationRequest.model_validate(raw)
    assert request.document() == raw
    digests = json.loads((FIXTURES / "DIGESTS.json").read_text())
    assert request.request_id == canonical_sha256(raw)
    assert (
        request.request_id == digests["qualification_request_golden.json"]["request_id"]
    )
    _validator("qualification_request.v1.json").validate(request.document())


def test_golden_receipt_digest_matches_received_bytes():
    raw = golden("replay_receipt_golden")
    receipt = ReplayReceipt.from_document(raw)
    assert receipt.computed_receipt_sha256 == raw["receipt_sha256"]
    _validator("replay_receipt.v1.json").validate(raw)


REQUEST_MUTATIONS = [
    ("extra member", lambda r: r.update(unexpected=True)),
    ("bad kind", lambda r: r.update(kind="other")),
    ("attempt zero", lambda r: r.update(attempt=0)),
    ("bad dataset digest", lambda r: r["candidate"]["data"].update(sha256="xyz")),
    ("bad repo type", lambda r: r["candidate"]["data"].update(repo_type="space")),
    (
        "wrapper with both sources",
        lambda r: r["candidate"]["policyengine"]["source"].update(
            pypi={"wheel_sha256": "a" * 64}
        ),
    ),
    ("released bundle from git", lambda r: r.update(kind="released_bundle")),
    (
        "missing bundle field",
        lambda r: r["candidate"]["expected_release_bundle"].pop("model_version"),
    ),
    ("bad commit", lambda r: r["requested_by"].update(commit="abc")),
]


@pytest.mark.parametrize(
    ("label", "mutate"), REQUEST_MUTATIONS, ids=[m[0] for m in REQUEST_MUTATIONS]
)
def test_request_mirror_and_schema_reject_the_same_requests(label, mutate):
    raw = copy.deepcopy(golden("qualification_request_golden"))
    mutate(raw)
    assert not _validator("qualification_request.v1.json").is_valid(raw), label
    with pytest.raises(ValidationError):
        ReplayQualificationRequest.model_validate(raw)


def test_requested_by_is_open_as_in_the_schema():
    raw = copy.deepcopy(golden("qualification_request_golden"))
    raw["requested_by"]["pair_id"] = sha("a")
    request = ReplayQualificationRequest.model_validate(raw)
    assert request.document()["requested_by"]["pair_id"] == sha("a")
    _validator("qualification_request.v1.json").validate(request.document())


# --- Replay gate ------------------------------------------------------------------


def _sealed(receipt_doc):
    doc = {key: value for key, value in receipt_doc.items() if key != "receipt_sha256"}
    doc["receipt_sha256"] = canonical_sha256(doc)
    return doc


def _status(request_id, receipt_doc, status=None):
    return ReplayStatus.model_validate(
        {
            "schema": "policyengine.uk-replay-status/v1",
            "request_id": request_id,
            "status": status or receipt_doc["status"],
            "history": [
                {
                    "status": status or receipt_doc["status"],
                    "at": "2026-10-15T10:00:00Z",
                    "run_url": "https://github.com/PolicyEngine/policyengine-scorecard/actions/runs/7",
                }
            ],
            "receipt_sha256": receipt_doc["receipt_sha256"],
            "receipt_commit": "c" * 40,
        }
    )


def _gate(receipt_doc, request=None, status=None):
    request = request or ReplayQualificationRequest.model_validate(
        golden("qualification_request_golden")
    )
    receipt = ReplayReceipt.from_document(receipt_doc)
    return evaluate_replay_receipt(
        request, status or _status(request.request_id, receipt_doc), receipt
    )


def _with_counts(**counts):
    doc = copy.deepcopy(golden("replay_receipt_golden"))
    base = {key: 0 for key in doc["diff"]["flag_counts"]}
    base.update(counts)
    doc["diff"]["flag_counts"] = base
    return _sealed(doc)


def test_golden_receipt_fails_on_its_structural_flag():
    gate = _gate(golden("replay_receipt_golden"))
    assert gate.status == "fail"
    assert "structural" in gate.summary


@pytest.mark.parametrize(
    ("counts", "status"),
    [
        ({}, "pass"),
        ({"numerical": 2}, "needs_review"),
        ({"support": 1}, "needs_review"),
        ({"numerical": 2, "coverage": 1}, "fail"),
        ({"construction": 1}, "fail"),
        ({"inertness": 1}, "fail"),
        ({"mapping": 3}, "fail"),
    ],
)
def test_flag_policy(counts, status):
    assert _gate(_with_counts(**counts)).status == status


def test_incomplete_or_failed_integrity_fails():
    doc = copy.deepcopy(golden("replay_receipt_golden"))
    doc["diff"]["flag_counts"] = {key: 0 for key in doc["diff"]["flag_counts"]}
    doc["integrity"]["status"] = "incomplete"
    assert _gate(_sealed(doc)).status == "fail"
    doc["integrity"] = {
        "status": "failed",
        "failures": [{"code": "non_finite", "detail": "NaN in VAT"}],
    }
    doc["status"] = "failed"
    assert _gate(_sealed(doc)).status == "fail"


def test_execution_of_other_artifacts_fails():
    for mutate in (
        lambda d: d["execution"].update(dataset_sha256="0" * 64),
        lambda d: d["execution"].update(packaged_bundle_manifest_sha256="0" * 64),
        lambda d: d["execution"]["packages"]["policyengine-uk"].update(version="9.9.9"),
        lambda d: d["execution"]["release_bundle"].update(model_version="9.9.9"),
    ):
        doc = copy.deepcopy(_with_counts())
        mutate(doc)
        assert _gate(_sealed(doc)).status == "fail"


def test_unbound_receipts_fail():
    sealed = _with_counts()
    tampered = copy.deepcopy(sealed)
    tampered["diff"]["flag_counts"]["numerical"] = 0
    tampered["corpus"]["corpus_version"] = "tampered"
    assert _gate(tampered).status == "fail"  # digest no longer matches the bytes
    request = ReplayQualificationRequest.model_validate(
        golden("qualification_request_golden")
    )
    other = _status("0" * 64, sealed)
    assert _gate(sealed, request=request, status=other).status == "fail"


def test_rejected_receipt_fails_with_its_code():
    doc = copy.deepcopy(golden("replay_receipt_golden"))
    doc.update(
        status="rejected",
        rejection={"code": "artifact_hash_mismatch", "detail": "dataset bytes differ"},
        corpus=None,
        diff=None,
    )
    doc["integrity"] = {"status": "not_run", "failures": []}
    gate = _gate(_sealed(doc))
    assert gate.status == "fail"
    assert "artifact_hash_mismatch" in gate.summary


def test_status_must_name_terminal_receipt():
    with pytest.raises(ValidationError):
        ReplayStatus.model_validate(
            {
                "schema": "policyengine.uk-replay-status/v1",
                "request_id": "a" * 64,
                "status": "complete",
                "history": [
                    {
                        "status": "complete",
                        "at": "2026-10-15T10:00:00Z",
                        "run_url": "https://github.com/PolicyEngine/policyengine-scorecard/actions/runs/7",
                    }
                ],
            }
        )
