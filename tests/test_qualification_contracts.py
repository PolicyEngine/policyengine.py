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
  artifacts;
- the replay policy (d1344-replay-regressions-v1) fails exactly the
  regressions it names, sends every other flagged row to review, and is
  monotone: adding a flagged row never makes the verdict better.
"""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path

import jsonschema
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from policyengine.provenance.canonical import canonical_sha256
from policyengine.provenance.qualification import (
    REPLAY_POLICY_ID,
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
    ("missing commit", lambda r: r["requested_by"].pop("commit")),
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


REQUEST_MUTATIONS_V1_TIGHTENED = [
    ("parent segment", "../enhanced_frs_2024_25.h5"),
    ("nested parent", "a/../b.h5"),
    ("trailing parent", "a/.."),
]


@pytest.mark.parametrize(
    ("label", "path"),
    REQUEST_MUTATIONS_V1_TIGHTENED,
    ids=[m[0] for m in REQUEST_MUTATIONS_V1_TIGHTENED],
)
def test_request_mirror_and_schema_refuse_parent_segments(label, path):
    raw = copy.deepcopy(golden("qualification_request_golden"))
    raw["candidate"]["data"]["path"] = path
    assert not _validator("qualification_request.v1.json").is_valid(raw), label
    with pytest.raises(ValidationError):
        ReplayQualificationRequest.model_validate(raw)


def test_request_mirror_and_schema_accept_dotted_names():
    raw = copy.deepcopy(golden("qualification_request_golden"))
    raw["candidate"]["data"]["path"] = "releases/1.58.0/..hidden.h5"
    _validator("qualification_request.v1.json").validate(raw)
    ReplayQualificationRequest.model_validate(raw)


def _rejected_receipt():
    doc = copy.deepcopy(golden("replay_receipt_golden"))
    doc.update(
        status="rejected",
        rejection={"code": "artifact_hash_mismatch", "detail": "dataset bytes differ"},
        corpus=None,
        diff=None,
        variant_id=None,
        variant_identity_sha256=None,
        execution=None,
    )
    doc["integrity"] = {"status": "not_run", "failures": []}
    return _sealed(doc)


RECEIPT_MUTATIONS = [
    (
        "complete without manifest",
        "complete",
        lambda r: r["results"].pop("manifest_sha256"),
    ),
    (
        "complete without identity",
        "complete",
        lambda r: r.update(variant_identity_sha256=None),
    ),
    (
        "unanchored python",
        "complete",
        lambda r: r["execution"].update(python="3.12.14+local"),
    ),
    ("rejected with variant", "rejected", lambda r: r.update(variant_id="pe6.2.6")),
    (
        "rejected with identity",
        "rejected",
        lambda r: r.update(variant_identity_sha256="0" * 64),
    ),
    (
        "rejected with integrity",
        "rejected",
        lambda r: r.update(integrity={"status": "failed", "failures": []}),
    ),
    (
        "empty inert measure key",
        "complete",
        lambda r: r["corpus"]["events"]["spring_budget_2023"].update(
            inert_measure_years=[{"measure_key": "", "year": 2026}]
        ),
    ),
    (
        "inert measure-year twice",
        "complete",
        lambda r: r["corpus"]["events"]["spring_budget_2023"].update(
            inert_measure_years=[{"measure_key": "m", "year": 2026}] * 2
        ),
    ),
    (
        "supported year twice",
        "complete",
        lambda r: r["corpus"]["events"]["spring_budget_2023"].update(
            supported_years=[2024, 2024]
        ),
    ),
    (
        "missing measure-year twice",
        "complete",
        lambda r: r["corpus"]["events"]["spring_budget_2023"].update(
            missing_measure_years=[{"measure_key": "m", "year": 2026}] * 2
        ),
    ),
    (
        "base event without its unsupported list",
        "complete",
        lambda r: r["diff"].update(
            base_events={
                "spring_budget_2023": {
                    k: v
                    for k, v in _base_event().items()
                    if k != "unsupported_measure_years"
                }
            }
        ),
    ),
    (
        "base event with a short digest",
        "complete",
        lambda r: r["diff"].update(
            base_events={
                "spring_budget_2023": {
                    **_base_event(),
                    "staging_manifest_sha256": "abc",
                }
            }
        ),
    ),
    (
        "base event with an extra field",
        "complete",
        lambda r: r["diff"].update(
            base_events={"spring_budget_2023": {**_base_event(), "extra": 1}}
        ),
    ),
    # Round-1 review of #637: the schema allows these keys to be absent,
    # never null, and never coerces a string to an integer.
    (
        "null missing list",
        "complete",
        lambda r: r["corpus"]["events"]["spring_budget_2023"].update(
            missing_measure_years=None
        ),
    ),
    (
        "null unsupported list",
        "complete",
        lambda r: r["corpus"]["events"]["spring_budget_2023"].update(
            unsupported_measure_years=None
        ),
    ),
    (
        "null base events",
        "complete",
        lambda r: r["diff"].update(base_events=None),
    ),
    (
        "base measure-year as a string",
        "complete",
        lambda r: r["diff"].update(
            base_events={
                "spring_budget_2023": {
                    **_base_event(),
                    "inert_measure_years": [{"measure_key": "m", "year": "2026"}],
                }
            }
        ),
    ),
    (
        "supported year as a string",
        "complete",
        lambda r: r["corpus"]["events"]["spring_budget_2023"].update(
            supported_years=["2024", 2025]
        ),
    ),
]


def _base_event(inert=(), missing=(), unsupported=()):
    """A base-side grid record (scorecard#183) for one event."""

    def measure_years(items):
        return [{"measure_key": m, "year": y} for m, y in items]

    return {
        "staging_manifest_sha256": "a" * 64,
        "run_manifest_sha256": "b" * 64,
        "supported_years": [2024, 2025, 2026, 2027],
        "full_supported_grid_complete": not inert
        and not set(missing) - set(unsupported),
        "inert_measure_years": measure_years(inert),
        "missing_measure_years": measure_years(missing),
        "unsupported_measure_years": measure_years(unsupported),
    }


def test_a_receipt_with_base_events_and_grid_lists_is_accepted_by_both():
    """scorecard#183's additive fields, valid: the schema and the mirror both
    accept them, and the digest covers them as received."""

    raw = copy.deepcopy(golden("replay_receipt_golden"))
    raw["corpus"]["events"]["spring_budget_2023"].update(
        missing_measure_years=[{"measure_key": "m", "year": 2023}],
        unsupported_measure_years=[{"measure_key": "m", "year": 2023}],
    )
    raw["diff"]["base_events"] = {"spring_budget_2023": _base_event()}
    raw = _sealed(raw)
    _validator("replay_receipt.v1.json").validate(raw)
    receipt = ReplayReceipt.from_document(raw)
    assert receipt.computed_receipt_sha256 == raw["receipt_sha256"]
    assert receipt.diff.base_events["spring_budget_2023"].run_manifest_sha256 == (
        "b" * 64
    )


@pytest.mark.parametrize(
    ("label", "base", "mutate"),
    RECEIPT_MUTATIONS,
    ids=[m[0] for m in RECEIPT_MUTATIONS],
)
def test_receipt_mirror_and_schema_reject_the_same_receipts(label, base, mutate):
    """Differential against W6's tightened replay_receipt.v1.json (dc040de)."""

    raw = (
        copy.deepcopy(golden("replay_receipt_golden"))
        if base == "complete"
        else _rejected_receipt()
    )
    _validator("replay_receipt.v1.json").validate(raw)
    ReplayReceipt.from_document(raw)
    mutate(raw)
    raw = _sealed(raw)
    assert not _validator("replay_receipt.v1.json").is_valid(raw), label
    # A pydantic ValidationError is a ValueError, as is a schema refusal.
    with pytest.raises(ValueError):
        ReplayReceipt.from_document(raw)


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


def _with_requested_wheels(doc):
    """Add artifact evidence omitted by the scorecard's synthetic golden fixture."""

    requested = golden("qualification_request_golden")["candidate"]
    for package, request_key in (
        ("policyengine-uk", "policyengine_uk"),
        ("policyengine-core", "policyengine_core"),
    ):
        doc["execution"]["packages"][package]["wheel_sha256"] = requested[request_key][
            "wheel_sha256"
        ]
    return doc


def _with_counts(sealed=True, **counts):
    """The golden receipt with these flag counts and one flagged row per flag."""

    doc = _with_requested_wheels(copy.deepcopy(golden("replay_receipt_golden")))
    base = {key: 0 for key in doc["diff"]["flag_counts"]}
    base.update(counts)
    doc["diff"]["flag_counts"] = base
    template = doc["diff"]["flagged_rows"][0]
    doc["diff"]["flagged_rows"] = [
        {**template, "flags": [kind], "year": 2024 + index}
        for kind, count in counts.items()
        for index in range(count)
    ]
    return _sealed(doc) if sealed else doc


def test_golden_receipt_needs_review_for_its_sign_reversal():
    """Its structural row moves £0.0000001 to -£123m: a sign reversal, which a
    model fix can make legitimately, so a named reviewer decides."""

    doc = _with_requested_wheels(copy.deepcopy(golden("replay_receipt_golden")))
    gate = _gate(_sealed(doc))
    assert gate.status == "needs_review", gate.summary
    assert gate.details["regressions"] == []
    assert sorted(item["level"] for item in gate.details["review_items"]) == [
        "head",
        "measure_year",
        "source_row",
    ]


@pytest.mark.parametrize(
    ("counts", "status"),
    [
        ({}, "pass"),
        ({"numerical": 2}, "needs_review"),
        ({"support": 1}, "needs_review"),
        # The template row has values on both sides: not a lost result.
        ({"numerical": 2, "coverage": 1}, "needs_review"),
        ({"construction": 1}, "needs_review"),
        # Not in the candidate's inert list: inert in the base only.
        ({"inertness": 1}, "needs_review"),
        ({"structural": 1}, "needs_review"),
        ({"mapping": 3}, "fail"),
    ],
)
def test_flag_policy(counts, status):
    assert _gate(_with_counts(**counts)).status == status


def _clean_receipt():
    return _with_counts(sealed=False)


def _edit(receipt, edit):
    edit(receipt)
    return _sealed(receipt)


EVENT = "spring_budget_2023"

CONTRADICTIONS = {
    "a structural row with zero counts": lambda r: r["diff"].update(
        flagged_rows=[{**golden("replay_receipt_golden")["diff"]["flagged_rows"][1]}]
    ),
    "a failure under complete integrity": lambda r: r["integrity"].update(
        failures=[{"code": "construction", "detail": "measure failed"}]
    ),
    "supported years with no artifacts": lambda r: r["corpus"]["events"][EVENT].update(
        artifacts=0
    ),
    "nothing replayed": lambda r: r["corpus"]["events"][EVENT].update(
        artifacts=0, supported_years=[]
    ),
    "an event with no years": lambda r: r["corpus"]["events"][EVENT].update(
        supported_years=[], unsupported_years=[]
    ),
}


@pytest.mark.parametrize("name", sorted(CONTRADICTIONS))
def test_a_receipt_that_contradicts_itself_fails(name):
    """Interrupted review of #574: each of these was schema-valid, correctly
    digested, and passed the gate because the summary counters were zero."""

    receipt = _edit(_clean_receipt(), CONTRADICTIONS[name])
    _validator("replay_receipt.v1.json").validate(receipt)
    gate = _gate(receipt)
    assert gate.status == "fail", (name, gate.summary)
    assert "contradicts itself or the request" in gate.summary


def test_blocking_flags_count_wherever_the_receipt_states_them():
    """A row's flag blocks even when its counter is understated."""

    receipt = _with_counts(sealed=False, numerical=1)
    receipt["diff"]["flagged_rows"].append(
        {**receipt["diff"]["flagged_rows"][0], "flags": ["mapping"], "year": 2030}
    )
    receipt["diff"]["flag_counts"]["mapping"] = 1
    assert _gate(_sealed(receipt)).status == "fail"
    assert "mapping" in _gate(_sealed(receipt)).summary


def test_a_measure_year_the_candidate_lists_as_inert_fails():
    """No receipt yet records the base's inert measure-years, so no gap is
    known, and an inert measure-year is a lost response."""

    receipt = _edit(
        _clean_receipt(),
        lambda r: r["corpus"]["events"][EVENT].update(
            inert_measure_years=[{"measure_key": "uc_childcare", "year": 2026}],
            full_supported_grid_complete=False,
        ),
    )
    gate = _gate(receipt)
    assert gate.status == "fail" and "lost_response 1" in gate.summary
    assert gate.details["known_gaps"] == []


def test_a_complete_event_that_lists_a_gap_contradicts_itself():
    for edit in (
        {"inert_measure_years": [{"measure_key": "uc_childcare", "year": 2026}]},
        {
            "missing_measure_years": [{"measure_key": "uc_childcare", "year": 2026}],
            "unsupported_measure_years": [],
        },
    ):
        receipt = _edit(
            _clean_receipt(), lambda r, e=edit: r["corpus"]["events"][EVENT].update(e)
        )
        gate = _gate(receipt)
        assert gate.status == "fail"
        assert "complete but lists inert or missing" in gate.summary


MEASURE = "spring_budget_2023__uc_childcare_cap_increase"


def _receipt_with(
    rows=(),
    inert=(),
    complete=True,
    integrity="complete",
    counts=None,
    missing=None,
    unsupported=(),
    base_events=None,
    sealed=True,
):
    """The golden receipt with these flagged rows (measure-year totals unless
    a row says otherwise), counts that match them, and this event state.
    ``missing`` and ``unsupported`` are the event's grid lists (omitted when
    ``missing`` is None, as before scorecard#183); ``base_events`` is
    ``diff.base_events``."""

    doc = _with_requested_wheels(copy.deepcopy(golden("replay_receipt_golden")))
    template = {
        "event": EVENT,
        "measure_key": MEASURE,
        "year": 2026,
        "level": "measure_year",
        "key": "total",
    }
    doc["diff"]["flagged_rows"] = [{**template, **row} for row in rows]
    tally = {key: 0 for key in doc["diff"]["flag_counts"]}
    for row in doc["diff"]["flagged_rows"]:
        for kind in row["flags"]:
            tally[kind] += 1
    tally.update(counts or {})
    doc["diff"]["flag_counts"] = tally
    event = doc["corpus"]["events"][EVENT]
    event["inert_measure_years"] = [
        {"measure_key": measure, "year": year} for measure, year in inert
    ]
    event["full_supported_grid_complete"] = complete
    if missing is not None:
        event["missing_measure_years"] = [
            {"measure_key": measure, "year": year} for measure, year in missing
        ]
        event["unsupported_measure_years"] = [
            {"measure_key": measure, "year": year} for measure, year in unsupported
        ]
    if base_events is not None:
        doc["diff"]["base_events"] = base_events
    doc["integrity"]["status"] = integrity
    return _sealed(doc) if sealed else doc


# The regression table of the d1344 decision record (second review), plus the
# bound's edges. Each: rows, candidate inert, grid complete, integrity, then
# the expected status and the kinds the gate must record.
POLICY_CASES = {
    "sign reversal": (
        [{"flags": ["numerical", "structural"], "base_gbp": 1e8, "head_gbp": -1e8}],
        (),
        True,
        "complete",
        "needs_review",
        {"flagged_move"},
    ),
    "£0 against a material base, distinct worlds": (
        [{"flags": ["numerical", "structural"], "base_gbp": 1e8, "head_gbp": 0.0}],
        (),
        True,
        "complete",
        "fail",
        {"lost_response"},
    ),
    "exactly the bound to £0, no numerical flag": (
        [{"flags": ["structural"], "base_gbp": 1e6, "head_gbp": 0.0}],
        (),
        True,
        "complete",
        "fail",
        {"lost_response"},
    ),
    "negative material base to £0": (
        [{"flags": ["structural"], "base_gbp": -2.5e8, "head_gbp": 0.0}],
        (),
        True,
        "complete",
        "fail",
        {"lost_response"},
    ),
    "just below the bound to £0": (
        [{"flags": ["structural"], "base_gbp": 999_999.0, "head_gbp": 0.0}],
        (),
        True,
        "complete",
        "needs_review",
        {"flagged_move"},
    ),
    "£0 head (not a measure-year total)": (
        [
            {
                "flags": ["structural"],
                "level": "head",
                "key": "universal_credit",
                "base_gbp": 1e8,
                "head_gbp": 0.0,
            }
        ],
        (),
        True,
        "complete",
        "needs_review",
        {"flagged_move"},
    ),
    "£0 source row against a material base (not a measure-year total)": (
        [
            {
                "flags": ["structural"],
                "level": "source_row",
                "key": "obr-row-1",
                "base_gbp": 1e8,
                "head_gbp": 0.0,
            }
        ],
        (),
        True,
        "complete",
        "needs_review",
        {"flagged_move"},
    ),
    "numeric base result, missing candidate result": (
        [
            {
                "flags": ["coverage"],
                "level": "source_row",
                "key": "obr-row-1",
                "base_gbp": 5e8,
                "head_gbp": None,
            }
        ],
        (),
        True,
        "complete",
        "fail",
        {"lost_result"},
    ),
    "coverage gain": (
        [
            {
                "flags": ["coverage"],
                "level": "source_row",
                "key": "obr-row-1",
                "base_gbp": None,
                "head_gbp": 574_999_000.021347,
            }
        ],
        (),
        True,
        "complete",
        "needs_review",
        {"coverage_gain"},
    ),
    "null/null coverage, otherwise complete": (
        [
            {
                "flags": ["coverage"],
                "level": "source_row",
                "key": "obr-row-1",
                "base_gbp": None,
                "head_gbp": None,
            }
        ],
        (),
        True,
        "complete",
        "needs_review",
        {"coverage_without_values"},
    ),
    "absent base, candidate inert and incomplete": (
        [
            {
                "flags": ["coverage"],
                "level": "source_row",
                "key": "obr-row-1",
                "base_gbp": None,
                "head_gbp": None,
            }
        ],
        ((MEASURE, 2026),),
        False,
        "incomplete",
        "fail",
        {"lost_response", "incomplete", "coverage_without_values"},
    ),
    # As in the 6.4.1 receipt: a measure-year flag and a source-row flag
    # whose candidate value is null, for a measure-year the candidate lists.
    "candidate inert, flagged against the base": (
        [
            {"flags": ["inertness"], "base_gbp": 2.641127e8, "head_gbp": 0.0},
            {
                "flags": ["inertness"],
                "level": "source_row",
                "key": "obr-row-1",
                "base_gbp": 2.641127e8,
                "head_gbp": None,
            },
        ],
        ((MEASURE, 2026),),
        False,
        "incomplete",
        "fail",
        {"lost_response", "incomplete"},
    ),
    "inert in the base only": (
        [{"flags": ["inertness"], "base_gbp": 0.0, "head_gbp": 3e8}],
        (),
        True,
        "complete",
        "needs_review",
        {"base_only_inertness"},
    ),
    "same supported artifact missing on both sides": (
        [],
        (),
        False,
        "incomplete",
        "fail",
        {"incomplete"},
    ),
    "incomplete integrity with no incomplete event": (
        [],
        (),
        True,
        "incomplete",
        "fail",
        {"incomplete"},
    ),
    "candidate loses a supported year": (
        [
            {
                "flags": ["support"],
                "level": "source_row",
                "key": "obr-row-1",
                "base_gbp": 1e8,
                "head_gbp": None,
            }
        ],
        (),
        True,
        "complete",
        "needs_review",
        {"flagged_move"},
    ),
    "construction": (
        [{"flags": ["construction"], "base_gbp": 1e8, "head_gbp": 1.2e8}],
        (),
        True,
        "complete",
        "needs_review",
        {"flagged_move"},
    ),
    "mapping": (
        [{"flags": ["mapping"], "base_gbp": 1e8, "head_gbp": 1e8}],
        (),
        True,
        "complete",
        "fail",
        {"mapping"},
    ),
}


@pytest.mark.parametrize("name", sorted(POLICY_CASES))
def test_the_replay_policy_decides_each_case_of_the_decision_record(name):
    rows, inert, complete, integrity, status, kinds = POLICY_CASES[name]
    receipt = _receipt_with(rows, inert, complete, integrity)
    _validator("replay_receipt.v1.json").validate(receipt)
    gate = _gate(receipt)
    assert gate.status == status, (name, gate.summary)
    recorded = {
        item["kind"]
        for item in gate.details["regressions"] + gate.details["review_items"]
    }
    assert recorded == kinds, (name, recorded)


GAP = (MEASURE, 2026)
UNSUPPORTED = (MEASURE, 2023)


# Each: candidate inert, candidate missing, candidate unsupported, the base
# events, then the expected status and known-gap reasons.
KNOWN_GAP_CASES = {
    "inert in both": (
        [GAP],
        [],
        [],
        {EVENT: _base_event(inert=[GAP])},
        "pass",
        ["inert in the base"],
    ),
    "missing in both": (
        [],
        [GAP],
        [],
        {EVENT: _base_event(missing=[GAP])},
        "pass",
        ["missing in the base"],
    ),
    "inert here, missing in the base": (
        [GAP],
        [],
        [],
        {EVENT: _base_event(missing=[GAP])},
        "pass",
        ["missing in the base"],
    ),
    "the base computed it": (
        [GAP],
        [],
        [],
        {EVENT: _base_event()},
        "fail",
        [],
    ),
    "missing in the base, but unsupported there": (
        [GAP],
        [],
        [],
        {EVENT: _base_event(missing=[GAP], unsupported=[GAP])},
        "fail",
        [],
    ),
    "a legacy base": (
        [GAP],
        [],
        [],
        {},
        "fail",
        [],
    ),
    "a record for another event": (
        [GAP],
        [],
        [],
        {"autumn_budget_2025": _base_event(inert=[GAP])},
        "fail",
        [],
    ),
    "another year inert in the base": (
        [GAP],
        [],
        [],
        {EVENT: _base_event(inert=[(MEASURE, 2027)])},
        "fail",
        [],
    ),
    "incomplete with nothing listed": (
        [],
        [UNSUPPORTED],
        [UNSUPPORTED],
        {EVENT: _base_event()},
        "fail",
        [],
    ),
}


@pytest.mark.parametrize("name", sorted(KNOWN_GAP_CASES))
def test_a_gap_is_known_only_on_the_bases_own_record(name):
    """The decision record's exact test: a candidate measure-year that is
    inert, or missing and supported, is a known gap only if the base's record
    for that event lists it as inert, or missing and supported."""

    inert, missing, unsupported, base_events, status, reasons = KNOWN_GAP_CASES[name]
    receipt = _receipt_with(
        inert=inert,
        complete=False,
        integrity="incomplete",
        missing=missing,
        unsupported=unsupported,
        base_events=base_events,
    )
    _validator("replay_receipt.v1.json").validate(receipt)
    gate = _gate(receipt)
    assert gate.status == status, (name, gate.summary)
    assert [gap["why"] for gap in gate.details["known_gaps"]] == reasons
    for gap in gate.details["known_gaps"]:
        assert gap["base_staging_manifest_sha256"] == "a" * 64
        assert (gap["event"], gap["measure_key"], gap["year"]) == (EVENT, *GAP)
    if status == "fail":
        assert {r["kind"] for r in gate.details["regressions"]} & {
            "incomplete",
            "lost_response",
        }


OTHER = "spring_budget_2023__other_measure"

# Round-1 review of #637: eight probes that killed mutants the table missed.
# Each: receipt arguments, the expected status and number of known gaps.
GAP_PROBES = {
    "complete, missing only in unsupported years": (
        dict(
            complete=True,
            integrity="complete",
            missing=[UNSUPPORTED],
            unsupported=[UNSUPPORTED],
            base_events={EVENT: _base_event()},
        ),
        "pass",
        0,
    ),
    "missing here, inert in the base": (
        dict(missing=[GAP], base_events={EVENT: _base_event(inert=[GAP])}),
        "pass",
        1,
    ),
    "another measure inert in the base, same year": (
        dict(
            inert=[GAP],
            missing=[],
            base_events={EVENT: _base_event(inert=[(OTHER, 2026)])},
        ),
        "fail",
        0,
    ),
    "a known inert gap beside a new missing one": (
        dict(
            inert=[GAP],
            missing=[(MEASURE, 2027)],
            base_events={EVENT: _base_event(inert=[GAP])},
        ),
        "fail",
        1,
    ),
    "a known gap against a negative material base": (
        dict(
            rows=[{"flags": ["structural"], "base_gbp": -2.5e8, "head_gbp": 0.0}],
            inert=[GAP],
            missing=[],
            base_events={EVENT: _base_event(inert=[GAP])},
        ),
        "fail",
        1,
    ),
    "a known gap against exactly the bound": (
        dict(
            rows=[{"flags": ["structural"], "base_gbp": 1e6, "head_gbp": 0.0}],
            inert=[GAP],
            missing=[],
            base_events={EVENT: _base_event(inert=[GAP])},
        ),
        "fail",
        1,
    ),
    "unsupported-only missing here, missing in the base": (
        dict(
            missing=[UNSUPPORTED],
            unsupported=[UNSUPPORTED],
            base_events={EVENT: _base_event(missing=[UNSUPPORTED])},
        ),
        "fail",
        0,
    ),
    "another measure missing in the base, same year": (
        dict(missing=[GAP], base_events={EVENT: _base_event(missing=[(OTHER, 2026)])}),
        "fail",
        0,
    ),
}


@pytest.mark.parametrize("name", sorted(GAP_PROBES))
def test_the_known_gap_rule_on_the_review_probes(name):
    arguments, status, known = GAP_PROBES[name]
    arguments = {"complete": False, "integrity": "incomplete", **arguments}
    receipt = _receipt_with(**arguments)
    _validator("replay_receipt.v1.json").validate(receipt)
    gate = _gate(receipt)
    assert gate.status == status, (name, gate.summary)
    assert len(gate.details["known_gaps"]) == known, name


def test_a_known_inert_gap_excuses_only_its_inertness_flag():
    """Round 2 of #637: the row's other flags are still judged."""

    def gate(flags):
        receipt = _receipt_with(
            rows=[{"flags": flags, "base_gbp": 0.0, "head_gbp": 0.0}],
            inert=[GAP],
            complete=False,
            integrity="incomplete",
            missing=[],
            base_events={EVENT: _base_event(inert=[GAP])},
        )
        _validator("replay_receipt.v1.json").validate(receipt)
        return _gate(receipt)

    assert gate(["inertness"]).status == "pass"
    mixed = gate(["inertness", "construction"])
    assert mixed.status == "needs_review"
    assert [item["kind"] for item in mixed.details["review_items"]] == ["flagged_move"]


#: The rows scorecard writes for each kind of known gap, from its own
#: compare_artifacts and compare_source_rows (round 3 of #637, executed at
#: scorecard 4d44449): an inert artifact has identical worlds (£0); a missing
#: one has no artifact. (candidate, base) -> rows.
PRODUCER_GAP_ROWS = {
    ("inert", "inert"): [],
    ("missing", "missing"): [],
    ("inert", "missing"): [
        {"flags": ["coverage"], "base_gbp": None, "head_gbp": 0.0},
        {
            "flags": ["inertness"],
            "base_gbp": None,
            "head_gbp": None,
            "level": "source_row",
            "key": "obr_row_1",
        },
    ],
    ("missing", "inert"): [
        {"flags": ["coverage"], "base_gbp": 0.0, "head_gbp": None},
        {
            "flags": ["inertness"],
            "base_gbp": None,
            "head_gbp": None,
            "level": "source_row",
            "key": "obr_row_1",
        },
    ],
}


def _known_gap(rows, candidate="inert", base="inert", second_event=False):
    """The gate on a schema-valid, sealed receipt whose one measure-year is a
    known gap of this kind, with these flagged rows."""

    doc = _receipt_with(
        rows=rows,
        inert=[GAP] if candidate == "inert" else [],
        missing=[] if candidate == "inert" else [GAP],
        complete=False,
        integrity="incomplete",
        base_events={EVENT: _base_event(**{base: [GAP]})},
        sealed=False,
    )
    if second_event:
        other = copy.deepcopy(doc["corpus"]["events"][EVENT])
        other.update(
            inert_measure_years=[],
            missing_measure_years=[],
            full_supported_grid_complete=True,
        )
        doc["corpus"]["events"]["autumn_budget_2025"] = other
    doc = _sealed(doc)
    _validator("replay_receipt.v1.json").validate(doc)
    return _gate(doc)


@pytest.mark.parametrize(
    ("candidate", "base"), sorted(PRODUCER_GAP_ROWS), ids=lambda side: side
)
def test_every_kind_of_known_gap_passes_as_scorecard_writes_it(candidate, base):
    """Round 3 of #637: a known gap does not block (d1344), including the
    rows by which scorecard records a mixed one. Before, missing/inert
    failed as a lost result and inert/missing went to review."""

    gate = _known_gap(PRODUCER_GAP_ROWS[candidate, base], candidate, base)
    assert gate.status == "pass", gate.summary
    (gap,) = gate.details["known_gaps"]
    assert (gap["candidate"], gap["why"]) == (candidate, f"{base} in the base")
    mixed = candidate != base
    assert [row["level"] for row in gate.details["known_gap_rows"]] == (
        ["measure_year", "source_row"] if mixed else []
    )


@pytest.mark.parametrize(
    ("candidate", "base", "row", "kind"),
    [
        # £0 on the wrong side for the gap's kind: judged as usual.
        ("inert", "missing", {"base_gbp": 0.0, "head_gbp": None}, "lost_result"),
        ("missing", "inert", {"base_gbp": None, "head_gbp": 0.0}, "coverage_gain"),
        # A material base value is still a lost result.
        ("missing", "inert", {"base_gbp": 5e8, "head_gbp": None}, "lost_result"),
        # A candidate value contradicts the candidate's own record.
        ("inert", "missing", {"base_gbp": None, "head_gbp": 5e8}, "contradiction"),
        ("missing", "missing", {"base_gbp": None, "head_gbp": 1.0}, "contradiction"),
        # inert/inert and missing/missing write no coverage row at all.
        ("inert", "inert", {"base_gbp": 0.0, "head_gbp": None}, "lost_result"),
        (
            "missing",
            "missing",
            {"base_gbp": None, "head_gbp": None},
            "coverage_without_values",
        ),
    ],
)
def test_other_coverage_rows_at_a_known_gap_are_judged_as_usual(
    candidate, base, row, kind
):
    gate = _known_gap([{"flags": ["coverage"], **row}], candidate, base)
    recorded = [r["kind"] for r in gate.details["regressions"]] + [
        r["kind"] for r in gate.details["review_items"]
    ]
    assert kind in recorded, gate.summary
    assert gate.status == ("needs_review" if kind.startswith("coverage") else "fail")
    assert gate.details["known_gap_rows"] == []


def test_a_known_gap_row_still_carries_its_other_flags():
    rows = copy.deepcopy(PRODUCER_GAP_ROWS["missing", "inert"])
    rows[0]["flags"].append("construction")
    gate = _known_gap(rows, "missing", "inert")
    assert gate.status == "needs_review"
    assert [r["kind"] for r in gate.details["review_items"]] == ["flagged_move"]


# Round 3 of #637: the reach of the inertness exemption. The reviewer's
# probes, kept; one changed with the policy (base-only inertness at a
# missing/inert gap is now the gap itself).
_FLAGS = [
    "numerical",
    "structural",
    "coverage",
    "support",
    "inertness",
    "construction",
    "mapping",
]


@pytest.mark.parametrize("n", range(1, len(_FLAGS) + 1))
def test_a_known_inert_gap_strips_only_inertness_for_every_flag_set(n):
    for combo in itertools.combinations(_FLAGS, n):
        gate = _known_gap([{"flags": list(combo), "base_gbp": None, "head_gbp": None}])
        rest = set(combo) - {"inertness"}
        expected = "fail" if "mapping" in rest else ("needs_review" if rest else "pass")
        assert gate.status == expected, combo
        assert len(gate.details["known_gaps"]) == 1


@pytest.mark.parametrize(
    "where",
    [
        {"year": 2027},
        {"measure_key": MEASURE + "_other"},
        {"event": "autumn_budget_2025"},
    ],
    ids=["another year", "another measure", "another event"],
)
def test_inertness_beside_a_known_inert_gap_still_needs_review(where):
    gate = _known_gap(
        [{"flags": ["inertness"], "base_gbp": 0.0, "head_gbp": 3e8, **where}],
        second_event=True,
    )
    assert gate.status == "needs_review", gate.summary
    assert [i["kind"] for i in gate.details["review_items"]] == ["base_only_inertness"]


def test_inertness_alone_off_the_inert_list_needs_review():
    gate = _gate(
        _receipt_with(rows=[{"flags": ["inertness"], "base_gbp": 0.0, "head_gbp": 3e8}])
    )
    assert gate.status == "needs_review"
    assert [i["kind"] for i in gate.details["review_items"]] == ["base_only_inertness"]


@pytest.mark.parametrize(
    ("base", "status"), [("inert", "pass"), ("missing", "needs_review")]
)
def test_inertness_on_a_known_missing_gap(base, status):
    """Where the base is inert, the base-only inertness is the gap itself.
    Where both are missing, an inertness flag contradicts both records and
    goes to review."""

    gate = _known_gap(
        [
            {
                "flags": ["inertness"],
                "base_gbp": None,
                "head_gbp": None,
                "level": "source_row",
                "key": "obr-row-1",
            }
        ],
        candidate="missing",
        base=base,
    )
    assert gate.status == status, gate.summary
    if status == "needs_review":
        assert [i["kind"] for i in gate.details["review_items"]] == [
            "base_only_inertness"
        ]


@pytest.mark.parametrize("level", ["source_row", "measure_year", "head"])
def test_a_known_inert_gap_strips_inertness_at_every_level(level):
    gate = _known_gap(
        [
            {
                "flags": ["inertness"],
                "base_gbp": None,
                "head_gbp": None,
                "level": level,
                "key": "k",
            }
        ]
    )
    assert gate.status == "pass", gate.summary


def test_a_mixed_inertness_row_off_the_inert_list_is_a_flagged_move():
    gate = _gate(
        _receipt_with(
            rows=[
                {"flags": ["inertness", "numerical"], "base_gbp": 1e8, "head_gbp": 3e8}
            ]
        )
    )
    assert [i["kind"] for i in gate.details["review_items"]] == ["flagged_move"]


def test_an_unknown_inert_zero_total_is_one_lost_response_and_no_review():
    gate = _gate(
        _receipt_with(
            rows=[{"flags": ["structural"], "base_gbp": 5e8, "head_gbp": 0.0}],
            inert=[GAP],
            missing=[],
            complete=False,
            integrity="incomplete",
        )
    )
    assert gate.status == "fail"
    assert [r["kind"] for r in gate.details["regressions"]] == [
        "lost_response",
        "incomplete",
    ]
    assert gate.details["review_items"] == []


def test_the_real_6_5_0_receipt():
    """W6's 6.5.0 qualification (request d83eaf59, replay-state 19a9ccdc):
    the first real receipt with diff.base_events. Eight flagged rows, all
    Autumn Budget 2024's capital gains measure (#186's fiscal-year blend):
    review, no regressions, no known gaps."""

    import json

    path = Path(__file__).parent / "fixtures/uk_replay/receipt_6.5.0"
    request = ReplayQualificationRequest.model_validate(
        json.loads((path / "REQUEST.json").read_text())
    )
    status = ReplayStatus.model_validate(json.loads((path / "STATUS.json").read_text()))
    receipt = ReplayReceipt.from_document(
        json.loads((path / "REPLAY_RECEIPT.json").read_text())
    )
    assert (
        receipt.computed_receipt_sha256
        == status.receipt_sha256
        == ("a7a67c268c21b983ed47930ea5816a23dcd6b37f75373b1a5fc59883b08f5551")
    )
    assert receipt.diff is not None and len(receipt.diff.base_events or {}) == 6
    gate = evaluate_replay_receipt(request, status, receipt)
    assert gate.status == "needs_review", gate.summary
    assert gate.details["regressions"] == gate.details["known_gaps"] == []
    items = gate.details["review_items"]
    assert [item["kind"] for item in items] == ["flagged_move"] * 8
    assert {item["measure_key"] for item in items} == {
        "autumn_budget_2024__capital_gains_main_rates_and_reliefs"
    }
    assert sorted(item["year"] for item in items) == [
        2024,
        2024,
        2024,
        2025,
        2026,
        2027,
        2028,
        2029,
    ]
    assert (
        gate.details["base_variant_id"]
        == "pe6.4.1_uk2.130.1_policyengine-uk-data-1.58.1"
    )


# Round 4 of #637: where the known-gap rules reach. The reviewer's probes.
_BESIDE = [
    {"year": 2027},
    {"measure_key": MEASURE + "_other"},
    {"event": "autumn_budget_2025"},
]
_BESIDE_IDS = ["another year", "another measure", "another event"]


def _kinds(gate):
    return (
        [r["kind"] for r in gate.details["regressions"]],
        [r["kind"] for r in gate.details["review_items"]],
    )


@pytest.mark.parametrize("where", _BESIDE, ids=_BESIDE_IDS)
def test_a_zero_base_coverage_row_beside_a_missing_inert_gap_is_a_lost_result(where):
    gate = _known_gap(
        [{"flags": ["coverage"], "base_gbp": 0.0, "head_gbp": None, **where}],
        "missing",
        "inert",
        second_event=True,
    )
    assert gate.status == "fail" and _kinds(gate)[0] == ["lost_result"], gate.summary
    assert gate.details["known_gap_rows"] == []


@pytest.mark.parametrize("where", _BESIDE, ids=_BESIDE_IDS)
def test_a_zero_head_coverage_row_beside_an_inert_missing_gap_is_a_gain(where):
    gate = _known_gap(
        [{"flags": ["coverage"], "base_gbp": None, "head_gbp": 0.0, **where}],
        "inert",
        "missing",
        second_event=True,
    )
    assert gate.status == "needs_review" and _kinds(gate)[1] == ["coverage_gain"]
    assert gate.details["known_gap_rows"] == []


@pytest.mark.parametrize("where", _BESIDE, ids=_BESIDE_IDS)
def test_inertness_beside_a_missing_inert_gap_still_needs_review(where):
    row = {
        "flags": ["inertness"],
        "base_gbp": None,
        "head_gbp": None,
        "level": "source_row",
        "key": "obr-row-1",
        **where,
    }
    gate = _known_gap([row], "missing", "inert", second_event=True)
    assert gate.status == "needs_review"
    assert _kinds(gate)[1] == ["base_only_inertness"], gate.summary


@pytest.mark.parametrize("where", _BESIDE, ids=_BESIDE_IDS)
def test_a_candidate_value_beside_a_gap_is_a_gain_not_a_contradiction(where):
    gate = _known_gap(
        [{"flags": ["coverage"], "base_gbp": None, "head_gbp": 5e8, **where}],
        "missing",
        "missing",
        second_event=True,
    )
    assert gate.status == "needs_review" and _kinds(gate)[1] == ["coverage_gain"]


@pytest.mark.parametrize(
    ("candidate", "base", "row", "status", "kind"),
    [
        # exactly £0, not merely immaterial
        (
            "inert",
            "missing",
            {"base_gbp": None, "head_gbp": 0.4},
            "fail",
            "contradiction",
        ),
        (
            "missing",
            "inert",
            {"base_gbp": 0.4, "head_gbp": None},
            "fail",
            "lost_result",
        ),
        # £0 on both sides is not the gap's shape
        (
            "inert",
            "missing",
            {"base_gbp": 0.0, "head_gbp": 0.0},
            "needs_review",
            "flagged_move",
        ),
        (
            "missing",
            "inert",
            {"base_gbp": 0.0, "head_gbp": 0.0},
            "needs_review",
            "flagged_move",
        ),
    ],
)
def test_only_exactly_the_gaps_shape_is_excused(candidate, base, row, status, kind):
    gate = _known_gap([{"flags": ["coverage"], **row}], candidate, base)
    assert gate.status == status, gate.summary
    assert kind in _kinds(gate)[0] + _kinds(gate)[1]
    assert gate.details["known_gap_rows"] == []


@pytest.mark.parametrize(
    ("candidate", "base", "row"),
    [
        ("inert", "inert", {"flags": ["numerical"], "base_gbp": 1e8, "head_gbp": 3e8}),
        ("missing", "inert", {"flags": ["coverage"], "base_gbp": 0.0, "head_gbp": 5e8}),
        (
            "missing",
            "missing",
            {
                "flags": ["construction"],
                "base_gbp": None,
                "head_gbp": 5e8,
                "level": "head",
                "key": "income_tax",
            },
        ),
        (
            "inert",
            "missing",
            {"flags": ["inertness"], "base_gbp": None, "head_gbp": 5e8},
        ),
        (
            "missing",
            "inert",
            {
                "flags": ["inertness"],
                "base_gbp": None,
                "head_gbp": 5e8,
                "level": "source_row",
                "key": "obr-row-1",
            },
        ),
        ("inert", "inert", {"flags": ["inertness"], "base_gbp": 0.0, "head_gbp": 5e8}),
    ],
)
def test_any_candidate_value_at_a_known_gap_is_a_contradiction(candidate, base, row):
    """Round 4 of #637: the policy says so for every row, not only coverage
    rows; before, a missing/inert inertness row with a candidate value passed."""

    gate = _known_gap([row], candidate, base)
    assert gate.status == "fail", gate.summary
    assert "contradiction" in _kinds(gate)[0]
    assert _kinds(gate)[1] == []


def test_a_candidate_value_contradiction_is_never_also_reviewed():
    gate = _known_gap(
        [{"flags": ["coverage"], "base_gbp": None, "head_gbp": 5e8}], "inert", "missing"
    )
    assert _kinds(gate) == (["contradiction"], [])


def test_a_counter_above_a_non_gap_row_is_a_contradiction():
    doc = _receipt_with(
        rows=[{"flags": ["numerical"], "base_gbp": 1e8, "head_gbp": 3e8}],
        counts={"numerical": 2},
    )
    _validator("replay_receipt.v1.json").validate(doc)
    gate = _gate(doc)
    assert gate.status == "fail" and _kinds(gate)[0] == ["contradiction"], gate.summary


def test_three_producer_shaped_gaps_at_once_pass():
    """Gaps of three kinds in one event, with rows as scorecard writes them."""

    gaps = {
        2025: ("missing", "inert"),
        2026: ("inert", "missing"),
        2027: ("inert", "inert"),
    }
    rows = []
    for year, kind in gaps.items():
        rows += [
            {**row, "year": year} for row in copy.deepcopy(PRODUCER_GAP_ROWS[kind])
        ]
    doc = _receipt_with(
        rows=rows,
        inert=[(MEASURE, y) for y, (c, _) in gaps.items() if c == "inert"],
        missing=[(MEASURE, y) for y, (c, _) in gaps.items() if c == "missing"],
        complete=False,
        integrity="incomplete",
        base_events={
            EVENT: _base_event(
                inert=[(MEASURE, y) for y, (_, b) in gaps.items() if b == "inert"],
                missing=[(MEASURE, y) for y, (_, b) in gaps.items() if b == "missing"],
            )
        },
    )
    _validator("replay_receipt.v1.json").validate(doc)
    gate = _gate(doc)
    assert gate.status == "pass", gate.summary
    assert len(gate.details["known_gaps"]) == 3
    assert len(gate.details["known_gap_rows"]) == 4


# Round 2 of #637: combinations of a known gap with other rules, and
# evidence that must stay within its own event.
def test_a_known_gap_never_excuses_a_complete_event_listing_a_gap():
    for inert, missing in (([GAP], []), ([], [GAP])):
        gate = _gate(
            _receipt_with(
                inert=inert,
                missing=missing,
                base_events={EVENT: _base_event(inert=[GAP])},
            )
        )
        assert gate.status == "fail"
        assert [r["kind"] for r in gate.details["regressions"]] == ["contradiction"]
        assert gate.details["policy"] == REPLAY_POLICY_ID


def test_a_known_gap_never_excuses_a_mapping_flag_or_a_material_lost_result():
    mapping = _gate(
        _receipt_with(
            rows=[{"flags": ["mapping"], "base_gbp": None, "head_gbp": None}],
            inert=[GAP],
            missing=[],
            complete=False,
            integrity="incomplete",
            base_events={EVENT: _base_event(inert=[GAP])},
        )
    )
    assert mapping.status == "fail" and len(mapping.details["known_gaps"]) == 1
    assert [r["kind"] for r in mapping.details["regressions"]] == ["mapping"]
    # A base inert by its own record cannot hold £500m: scorecard cannot
    # write this row, and the gate still fails it as a lost result.
    lost = _gate(
        _receipt_with(
            rows=[{"flags": ["coverage"], "base_gbp": 5e8, "head_gbp": None}],
            missing=[GAP],
            complete=False,
            integrity="incomplete",
            base_events={EVENT: _base_event(inert=[GAP])},
        )
    )
    assert lost.status == "fail"
    assert [r["kind"] for r in lost.details["regressions"]] == ["lost_result"]


@pytest.mark.parametrize("candidate", ["inert", "missing"])
def test_base_evidence_never_crosses_into_another_event(candidate):
    """The same measure-year in a second event, which the base did not
    replay, is not excused by the first event's record."""

    receipt = _receipt_with(
        inert=[GAP] if candidate == "inert" else [],
        missing=[] if candidate == "inert" else [GAP],
        complete=False,
        integrity="incomplete",
        base_events={EVENT: _base_event(inert=[GAP])},
        sealed=False,
    )
    receipt["corpus"]["events"]["autumn_budget_2025"] = copy.deepcopy(
        receipt["corpus"]["events"][EVENT]
    )
    gate = _gate(_sealed(receipt))
    assert gate.status == "fail"
    assert [(gap["event"], gap["candidate"]) for gap in gate.details["known_gaps"]] == [
        (EVENT, candidate)
    ]
    assert {r["event"] for r in gate.details["regressions"]} == {"autumn_budget_2025"}
    expected = (
        ["lost_response", "incomplete"] if candidate == "inert" else ["incomplete"]
    )
    assert [r["kind"] for r in gate.details["regressions"]] == expected


def test_a_known_missing_gap_never_hides_another_missing_measure_year():
    gate = _gate(
        _receipt_with(
            missing=[GAP, (MEASURE, 2027)],
            complete=False,
            integrity="incomplete",
            base_events={EVENT: _base_event(missing=[GAP])},
        )
    )
    assert gate.status == "fail" and len(gate.details["known_gaps"]) == 1
    assert gate.details["regressions"][0]["measure_years"] == [[MEASURE, 2027]]


def test_an_incomplete_event_without_its_missing_list_fails_even_with_base_evidence():
    """A receipt from before scorecard#183 cannot show what is missing."""

    receipt = _receipt_with(
        inert=[GAP],
        complete=False,
        integrity="incomplete",
        base_events={EVENT: _base_event(inert=[GAP])},
    )
    gate = _gate(receipt)
    assert gate.status == "fail"
    assert gate.details["known_gaps"][0]["why"] == "inert in the base"
    assert [r["kind"] for r in gate.details["regressions"]] == ["incomplete"]
    assert "does not list its missing" in gate.details["regressions"][0]["why"]


def test_a_known_gap_never_excuses_a_material_base_value():
    """A base whose record lists the measure-year as inert cannot also hold a
    material value for it, so a £0 against that value still fails."""

    def receipt(base_gbp):
        rows = (
            []
            if base_gbp is None
            else [{"flags": ["structural"], "base_gbp": base_gbp, "head_gbp": 0.0}]
        )
        return _receipt_with(
            rows=rows,
            inert=[GAP],
            complete=False,
            integrity="incomplete",
            missing=[],
            base_events={EVENT: _base_event(inert=[GAP])},
        )

    known = _gate(receipt(None))
    assert known.status == "pass" and known.details["regressions"] == []
    contradicted = _gate(receipt(2.5e8))
    assert contradicted.status == "fail"
    assert [r["kind"] for r in contradicted.details["regressions"]] == ["lost_response"]
    assert "though the base's record" in contradicted.details["regressions"][0]["why"]


@pytest.mark.parametrize("kind", ["numerical", "mapping", "inertness"])
def test_a_counter_with_no_row_is_a_contradiction(kind):
    """Scorecard's counters tally its rows' flags (equal on every real
    receipt), so a flag only the counters state contradicts the rows: it
    fails, whether or not its kind blocks."""

    receipt = _receipt_with(counts={kind: 1})
    _validator("replay_receipt.v1.json").validate(receipt)
    gate = _gate(receipt)
    assert gate.status == "fail"
    assert [r["kind"] for r in gate.details["regressions"]] == ["contradiction"]
    assert f"0 flagged row(s) carry {kind} but flag_counts says 1" in gate.summary


def test_a_counter_above_its_rows_cannot_hide_behind_a_known_gap():
    """Round 3 of #637: one exempt row with flag_counts.inertness=5 passed;
    the excess is a contradiction."""

    receipt = _receipt_with(
        rows=[{"flags": ["inertness"], "base_gbp": 0.0, "head_gbp": 0.0}],
        inert=[GAP],
        missing=[],
        complete=False,
        integrity="incomplete",
        counts={"inertness": 5},
        base_events={EVENT: _base_event(inert=[GAP])},
    )
    gate = _gate(receipt)
    assert gate.status == "fail"
    assert "1 flagged row(s) carry inertness but flag_counts says 5" in gate.summary


@pytest.mark.parametrize(
    "path",
    [
        Path(__file__).parent / "fixtures/uk_replay/receipt_6.4.1_attempt1",
        Path(__file__).parent / "fixtures/uk_replay/receipt_6.5.0",
    ],
    ids=["6.4.1 attempt 1", "6.5.0"],
)
def test_real_receipts_count_exactly_the_flags_their_rows_carry(path):
    import json

    receipt = json.loads((path / "REPLAY_RECEIPT.json").read_text())
    tally: dict[str, int] = {}
    for row in receipt["diff"]["flagged_rows"]:
        for kind in row["flags"]:
            tally[kind] = tally.get(kind, 0) + 1
    assert {k: n for k, n in receipt["diff"]["flag_counts"].items() if n} == tally


def test_every_early_failure_carries_the_policy_record():
    import hashlib
    from importlib.resources import files

    text = (files("policyengine.data.qualification") / "replay_policy.md").read_bytes()
    clean = _receipt_with()
    rejected = _rejected_receipt()
    contradictory = _edit(
        _clean_receipt(),
        lambda r: r["corpus"]["events"][EVENT].update(artifacts=0),
    )
    failed = copy.deepcopy(_with_requested_wheels(golden("replay_receipt_golden")))
    failed["status"] = "failed"
    failed["integrity"] = {
        "status": "failed",
        "failures": [{"code": "construction_inert", "detail": "x"}],
    }
    unbound = copy.deepcopy(clean)
    unbound["execution"]["dataset_sha256"] = "0" * 64
    cases = {
        "rejected": _gate(rejected),
        "contradiction": _gate(contradictory),
        "failed": _gate(_sealed(failed)),
        "unbound": _gate(_sealed(unbound)),
    }
    for kind, gate in cases.items():
        assert gate.status == "fail", kind
        assert gate.details["policy"] == REPLAY_POLICY_ID
        assert gate.details["policy_sha256"] == hashlib.sha256(text).hexdigest()
        assert [r["kind"] for r in gate.details["regressions"]] == [kind], kind
        assert gate.details["review_items"] == [] and gate.details["known_gaps"] == []


def test_the_gate_records_the_policy_it_applied():
    import hashlib
    from importlib.resources import files

    gate = _gate(_receipt_with())
    assert gate.status == "pass"
    text = (files("policyengine.data.qualification") / "replay_policy.md").read_bytes()
    assert gate.details["policy"] == REPLAY_POLICY_ID
    assert gate.details["policy_sha256"] == hashlib.sha256(text).hexdigest()
    assert REPLAY_POLICY_ID.encode() in text
    assert gate.details["known_gaps"] == []


def test_the_first_real_receipt_fails_on_its_inert_uc_measure_years():
    """policyengine 6.4.1 + policyengine-uk 2.130.1 + uk-data 1.58.1, receipt
    e3cc6521…: scorecard's construction of spring_statement_2025's UC health
    element change was inert in 2026-29, where the base computed £264.1m to
    £626.6m. Those four lost responses and the incomplete grid fail it; its
    other 346 flagged rows are review items."""

    from collections import Counter

    folder = FIXTURES / "receipt_6.4.1_attempt1"
    request = ReplayQualificationRequest.model_validate(
        json.loads((folder / "REQUEST.json").read_text())
    )
    document = json.loads((folder / "REPLAY_RECEIPT.json").read_text())
    receipt = ReplayReceipt.from_document(document)
    assert receipt.computed_receipt_sha256 == receipt.receipt_sha256
    gate = evaluate_replay_receipt(
        request, _status(request.request_id, document), receipt
    )
    assert gate.status == "fail"
    lost = sorted(
        (item["measure_key"], item["year"])
        for item in gate.details["regressions"]
        if item["kind"] == "lost_response"
    )
    measure = "spring_statement_2025__uc_health_element_freeze_and_new_claimant_cut"
    assert lost == [(measure, year) for year in (2026, 2027, 2028, 2029)]
    assert [
        item["event"]
        for item in gate.details["regressions"]
        if item["kind"] == "incomplete"
    ] == ["spring_statement_2025"]
    assert Counter(item["kind"] for item in gate.details["review_items"]) == {
        "flagged_move": 345,
        "coverage_gain": 1,
    }


_ROW = st.fixed_dictionaries(
    {
        "flags": st.lists(
            st.sampled_from(
                [
                    "numerical",
                    "structural",
                    "coverage",
                    "mapping",
                    "support",
                    "inertness",
                    "construction",
                ]
            ),
            min_size=1,
            max_size=3,
            unique=True,
        ),
        "level": st.sampled_from(["source_row", "measure_year", "head"]),
        "year": st.sampled_from([2025, 2026]),
        "base_gbp": st.one_of(
            st.none(),
            st.just(0.0),
            st.sampled_from([999_999.0, 1e6, -1e6, 2.5e8, -2.5e8]),
            st.floats(-1e10, 1e10, allow_nan=False),
        ),
        "head_gbp": st.one_of(
            st.none(),
            st.just(0.0),
            st.floats(-1e10, 1e10, allow_nan=False),
        ),
    }
)
_RANK = {"pass": 0, "needs_review": 1, "fail": 2}


@settings(max_examples=150, deadline=None)
@given(
    rows=st.lists(_ROW, max_size=4),
    extra=_ROW,
    inert=st.lists(st.sampled_from([2025, 2026]), max_size=2, unique=True),
)
def test_the_replay_policy_is_monotone_and_never_passes_a_flag(rows, extra, inert):
    """For every receipt: a flagged row never passes; mapping and lost results
    always fail; fail is exactly "a regression was recorded"; and adding a
    flagged row never makes the verdict better."""

    listed = tuple((MEASURE, year) for year in inert)
    complete = not listed

    def judge(these):
        receipt = _receipt_with(
            these, listed, complete, "complete" if complete else "incomplete"
        )
        return _gate(receipt)

    def oracle(these):
        """The decision record's outcome, restated independently: a
        regression fails; any other flagged row needs review."""

        for row in these:
            base, head = row["base_gbp"], row["head_gbp"]
            if (
                "mapping" in row["flags"]
                or ("coverage" in row["flags"] and base is not None and head is None)
                or (
                    row["level"] == "measure_year"
                    and head == 0
                    and base is not None
                    and abs(base) >= 1_000_000
                )
            ):
                return "fail"
        if listed:
            return "fail"
        return "needs_review" if these else "pass"

    before = judge(rows)
    after = judge([*rows, extra])
    assert before.status == oracle(rows), (rows, before.summary)
    assert after.status == oracle([*rows, extra]), (extra, after.summary)
    assert _RANK[after.status] >= _RANK[before.status]
    for gate, these in ((before, rows), (after, [*rows, extra])):
        assert (gate.status == "fail") == bool(gate.details["regressions"])
        if these or listed:
            assert gate.status != "pass"
        if any(
            "mapping" in row["flags"]
            or (
                "coverage" in row["flags"]
                and row["base_gbp"] is not None
                and row["head_gbp"] is None
            )
            for row in these
        ):
            assert gate.status == "fail"


@settings(max_examples=300, deadline=None)
@given(
    rows=st.lists(_ROW, max_size=4),
    candidate=st.sampled_from(["inert", "missing"]),
    base=st.sampled_from(["inert", "missing", None]),
)
def test_the_replay_policy_with_known_gaps_against_a_reference(rows, candidate, base):
    """Round 3 of #637: the policy restated independently, with the
    measure-year 2026 inert or missing in the candidate and, unless ``base``
    is None, recorded inert or missing in the base (a known gap). Rows fall
    on the gap (2026) or beside it (2025)."""

    kwargs = dict(
        inert=[GAP] if candidate == "inert" else [],
        missing=[] if candidate == "inert" else [GAP],
        complete=False,
        integrity="incomplete",
    )
    if base is not None:
        kwargs["base_events"] = {EVENT: _base_event(**{base: [GAP]})}
    gate = _gate(_receipt_with(rows, **kwargs))

    known = base is not None
    fail = not known  # an unknown inert or missing measure-year fails
    review = False
    for row in rows:
        flags = set(row["flags"])
        b, h = row["base_gbp"], row["head_gbp"]
        at_gap = known and row["year"] == 2026
        if at_gap and "coverage" in flags:
            if (candidate, base) == ("inert", "missing") and b is None and h == 0:
                flags.discard("coverage")
            if (candidate, base) == ("missing", "inert") and h is None and b == 0:
                flags.discard("coverage")
        if "mapping" in flags:
            fail = True
        if "coverage" in flags and b is not None and h is None:
            fail = True
        # Any candidate value at a known gap contradicts the candidate's
        # record (round 4 of #637).
        if at_gap and h not in (None, 0):
            fail = True
        if (
            row["level"] == "measure_year"
            and h == 0
            and b is not None
            and abs(b) >= max(1e6, 0.01 * abs(b))
        ):
            fail = True
        if (row["year"] == 2026 and candidate == "inert") or (
            at_gap and (candidate, base) == ("missing", "inert") and b in (None, 0)
        ):
            flags.discard("inertness")
        if flags - {"mapping"}:
            review = True
    expected = "fail" if fail else ("needs_review" if review else "pass")
    assert gate.status == expected, (candidate, base, rows, gate.summary)
    assert (gate.status == "fail") == bool(gate.details["regressions"])
    assert len(gate.details["known_gaps"]) == (1 if known else 0)


def test_the_comparison_base_must_be_the_one_requested():
    raw = copy.deepcopy(golden("qualification_request_golden"))
    base_variant = _clean_receipt()["diff"]["base_variant_id"]
    raw["compare_to"] = base_variant
    explicit = ReplayQualificationRequest.model_validate(raw)
    receipt = _clean_receipt()
    receipt["request_id"] = explicit.request_id
    assert _gate(_sealed(receipt), request=explicit).status == "pass"
    raw["compare_to"] = "pe6.2.6_uk2.125.1_policyengine-uk-data-1.58.0"
    other = ReplayQualificationRequest.model_validate(raw)
    receipt = _clean_receipt()
    receipt["request_id"] = other.request_id
    gate = _gate(_sealed(receipt), request=other)
    assert gate.status == "fail" and "asked for a comparison" in gate.summary


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


@pytest.mark.parametrize("package", ["policyengine-uk", "policyengine-core"])
@pytest.mark.parametrize("wheel_sha256", [None, "0" * 64])
def test_replay_requires_exact_country_and_core_wheels(package, wheel_sha256):
    doc = _clean_receipt()
    installed = doc["execution"]["packages"][package]
    if wheel_sha256 is None:
        installed.pop("wheel_sha256")
    else:
        installed["wheel_sha256"] = wheel_sha256
    gate = _gate(_sealed(doc))
    assert gate.status == "fail"
    assert f"{package} wheel hash" in gate.summary


@pytest.mark.parametrize("wheel_sha256", [None, "0" * 64])
def test_released_bundle_replay_requires_requested_wrapper_wheel(wheel_sha256):
    raw = copy.deepcopy(golden("qualification_request_golden"))
    raw["kind"] = "released_bundle"
    raw["candidate"]["policyengine"]["source"] = {"pypi": {"wheel_sha256": "a" * 64}}
    request = ReplayQualificationRequest.model_validate(raw)
    doc = _clean_receipt()
    doc["request_id"] = request.request_id
    if wheel_sha256 is not None:
        doc["execution"]["packages"]["policyengine"]["wheel_sha256"] = wheel_sha256
    gate = _gate(_sealed(doc), request=request)
    assert gate.status == "fail"
    assert "policyengine wheel hash" in gate.summary


def test_released_bundle_replay_accepts_exact_requested_wrapper_wheel():
    raw = copy.deepcopy(golden("qualification_request_golden"))
    raw["kind"] = "released_bundle"
    raw["candidate"]["policyengine"]["source"] = {"pypi": {"wheel_sha256": "a" * 64}}
    request = ReplayQualificationRequest.model_validate(raw)
    doc = _clean_receipt()
    doc["request_id"] = request.request_id
    doc["execution"]["packages"]["policyengine"]["wheel_sha256"] = "a" * 64
    assert _gate(_sealed(doc), request=request).status == "pass"


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
        variant_id=None,
        variant_identity_sha256=None,
        execution=None,
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


def test_requests_without_a_run_id_are_valid_as_in_the_schema():
    raw = copy.deepcopy(golden("qualification_request_golden"))
    raw["requested_by"].pop("workflow_run_id")
    _validator("qualification_request.v1.json").validate(raw)
    assert ReplayQualificationRequest.model_validate(raw).document() == raw


def test_early_failure_receipt_fails_the_gate():
    doc = copy.deepcopy(golden("replay_receipt_golden"))
    doc.update(
        status="failed",
        variant_id=None,
        variant_identity_sha256=None,
        execution=None,
        corpus=None,
        diff=None,
    )
    doc["integrity"] = {
        "status": "failed",
        "failures": [
            {"code": "wheel_download_failed", "detail": "pip download failed"}
        ],
    }
    sealed = _sealed(doc)
    _validator("replay_receipt.v1.json").validate(sealed)
    gate = _gate(sealed)
    assert gate.status == "fail" and "wheel_download_failed" in gate.summary
