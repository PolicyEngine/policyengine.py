"""Round-two reproductions and round-three probe evidence hardening."""

from __future__ import annotations

import copy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from policyengine.provenance import uk_qualification
from policyengine.provenance.qualification import (
    GateResult,
    ReplayQualificationRequest,
    _replay_probe_passes,
    qualification_verdict,
)
from policyengine.provenance.qualification_ledger import write_json
from policyengine.provenance.receipt import content_sha256
from tests.qualification_fixtures import gates, golden, make_pair
from tests.test_qualification_contracts import _receipt_with
from tests.test_replay_exceptions import (
    TEST_ATTEMPT_ID,
    _entry,
    _failed_receipt,
    _judge,
    _probe,
    _registry,
)


@pytest.mark.parametrize(
    "change",
    [
        "positive_bool",
        "positive_nan",
        "positive_inf",
        "positive_string",
        "zero_bool",
        "zero_nan",
        "duplicate",
    ],
)
def test_incoherent_probe_values_never_authorize_exception(change):
    registry = _registry(_entry())
    result, evidence = _probe(registry)
    probe = evidence["probes"][0]
    if change == "positive_bool":
        probe["positive_change_gbp"] = True
    elif change == "positive_nan":
        probe["positive_change_gbp"] = float("nan")
    elif change == "positive_inf":
        probe["positive_change_gbp"] = float("inf")
    elif change == "positive_string":
        probe["positive_change_gbp"] = "6000"
    elif change == "zero_bool":
        probe["zero_change_gbp"] = False
    elif change == "zero_nan":
        probe["zero_change_gbp"] = float("nan")
    else:
        evidence["probes"].append(copy.deepcopy(probe))
    # Non-finite JSON cannot be sealed by the receipt's canonical encoder.
    try:
        evidence_digest = content_sha256(evidence)
    except ValueError:
        assert change in {"positive_nan", "positive_inf", "zero_nan"}
        return
    result = result.model_copy(update={"evidence_sha256": evidence_digest})
    actual = _judge(_failed_receipt(), registry=registry, probe=(result, evidence))
    assert actual.status == "fail"
    assert actual.details["applied_exceptions"] == []


@pytest.mark.parametrize(
    "status", ["pass", "needs_review", "fail", "error", "unavailable"]
)
def test_probe_status_is_irrelevant_to_a_clean_candidate(status):
    registry = _registry(_entry())
    result, evidence = _probe(registry)
    result = result.model_copy(update={"status": status})
    clean = _receipt_with()
    baseline = _judge(clean, registry=registry, probe=(None, None))
    actual = _judge(clean, registry=registry, probe=(result, evidence))
    assert actual.canonical_payload() == baseline.canonical_payload()
    assert actual.status == "pass"


@pytest.mark.parametrize("damage", ["failed", "malformed", "wrong_gate", "missing"])
def test_failed_or_unreadable_probe_is_not_an_unconditional_gate(tmp_path, damage):
    uk_qualification.write_gate_results(tmp_path, gates(), {})
    path = tmp_path / "gates/replay_probe.result.json"
    if damage == "failed":
        write_json(
            path,
            GateResult(
                gate_id="replay_probe", status="fail", summary="failed"
            ).canonical_payload(),
        )
    elif damage == "malformed":
        path.write_text("bad json")
    elif damage == "wrong_gate":
        write_json(
            path,
            GateResult(
                gate_id="foreign", status="error", summary="failed"
            ).canonical_payload(),
        )
    loaded = uk_qualification.load_gate_results(tmp_path)
    assert sorted(loaded, key=lambda gate: gate.gate_id) == sorted(
        gates(), key=lambda gate: gate.gate_id
    )
    assert qualification_verdict(loaded) == "qualified"


@pytest.mark.parametrize(
    "target_pair",
    [
        make_pair(data="1.58.1"),
        make_pair(dataset_sha="e" * 64),
        make_pair(core="3.33.1"),
    ],
)
def test_probe_cannot_cross_pairs_with_identical_model_and_attempt_name(
    tmp_path, target_pair
):
    source = tmp_path / "source/attempts/same-commit"
    target = tmp_path / "target/attempts/same-commit"
    write_json(source / "candidate.json", {"pair": make_pair().canonical_payload()})
    write_json(target / "candidate.json", {"pair": target_pair.canonical_payload()})
    result, evidence = _probe(attempt_id=uk_qualification.attempt_evidence_id(source))
    uk_qualification.write_gate_results(target, [result], {"replay_probe": evidence})
    assert uk_qualification.attempt_evidence_id(
        source
    ) != uk_qualification.attempt_evidence_id(target)
    assert uk_qualification.load_attempt_replay_probe(target) == (None, None)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("installed_model_version", "2.134.0"),
        ("installed_model_version", None),
        ("positive_baseline_gbp", 1),
        ("positive_reform_gbp", 1),
        ("positive_change_gbp", 6000.5),
        ("zero_baseline_gbp", 1),
        ("zero_reform_gbp", 1),
    ],
)
def test_probe_rejects_contradictory_recorded_version_or_outputs(field, value):
    registry = _registry(_entry())
    result, evidence = _probe(registry)
    evidence["probes"][0][field] = value
    result = result.model_copy(update={"evidence_sha256": content_sha256(evidence)})
    replay = _judge(_failed_receipt(), registry=registry, probe=(result, evidence))
    assert replay.status == "fail"
    assert replay.details["applied_exceptions"] == []
    assert qualification_verdict(gates(replay=replay.status)) == "rejected"


@pytest.mark.parametrize(
    "field",
    [
        "positive_baseline_gbp",
        "positive_reform_gbp",
        "positive_change_gbp",
        "zero_baseline_gbp",
        "zero_reform_gbp",
        "zero_change_gbp",
    ],
)
@pytest.mark.parametrize("value", [None, False, "0", float("nan"), float("inf")])
def test_probe_consumer_fails_closed_on_invalid_recorded_numbers(field, value):
    registry = _registry(_entry())
    result, evidence = _probe(registry)
    request = ReplayQualificationRequest.model_validate(
        golden("qualification_request_golden")
    )
    assert _replay_probe_passes(
        registry.exceptions[0], request, result, evidence, TEST_ATTEMPT_ID
    )
    evidence["probes"][0][field] = value
    # Invalid JSON numbers cannot have a digest; the consumer must reject them
    # as evidence rather than raising while attempting to rehash the document.
    try:
        digest = content_sha256(evidence)
    except ValueError:
        digest = "0" * 64
    result = result.model_copy(update={"evidence_sha256": digest})
    assert not _replay_probe_passes(
        registry.exceptions[0], request, result, evidence, TEST_ATTEMPT_ID
    )


@given(
    field=st.sampled_from(
        [
            "positive_baseline_gbp",
            "positive_reform_gbp",
            "zero_baseline_gbp",
            "zero_reform_gbp",
        ]
    ),
    discrepancy=st.integers(min_value=1, max_value=10**9),
)
def test_any_raw_output_discrepancy_cannot_authorize_an_exception(field, discrepancy):
    registry = _registry(_entry())
    result, evidence = _probe(registry)
    evidence["probes"][0][field] += discrepancy
    result = result.model_copy(update={"evidence_sha256": content_sha256(evidence)})
    replay = _judge(_failed_receipt(), registry=registry, probe=(result, evidence))
    assert replay.status == "fail"
    assert replay.details["applied_exceptions"] == []
    assert qualification_verdict(gates(replay=replay.status)) != "qualified"
