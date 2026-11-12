"""Receipt identities preserve native UK Scenario data-load phases.

These tests construct Scenarios and canonical identities only. They run no
formulas, household calculations, dataset loads or microsimulations.
"""

from copy import deepcopy
from types import SimpleNamespace

import jsonschema
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from policyengine_uk.utils.scenario import Scenario

from policyengine.provenance.canonical import canonical_sha256
from policyengine.provenance.receipt import (
    PHASED_SCENARIO_APPLICATION,
    PHASED_SCENARIO_REPRESENTATION,
    ExecutionReceipt,
    ReceiptError,
    ReformIdentity,
    composed_reform_identity,
    phased_scenario_reform_identity,
    reform_identity,
    scenario_reform_identity,
)
from tests import receipt_modifiers as modifiers

REVISION = {"repository": "PolicyEngine/test", "git_sha": "a" * 40}
CHANGES = {"gov.example.rate": {"2027-04-06.2028-04-05": 0.21}}


def _mixed(before_modifier=None, after_modifier=modifiers.raise_basic_rate_to):
    return Scenario(
        parameter_changes=deepcopy(CHANGES),
        simulation_modifier=before_modifier,
        applied_before_data_load=True,
    ) + Scenario(simulation_modifier=after_modifier)


def _member(identity):
    return {
        "representation": identity.representation,
        "reform_sha256": identity.reform_sha256,
        "binding": identity.binding,
    }


@pytest.mark.parametrize("early", [False, True])
@pytest.mark.parametrize("changes", [None, CHANGES])
@pytest.mark.parametrize("modifier", [None, modifiers.raise_basic_rate_to])
def test_single_phase_keeps_its_existing_v1_identity(early, changes, modifier):
    scenario = Scenario(
        parameter_changes=changes,
        simulation_modifier=modifier,
        applied_before_data_load=early,
    )
    assert phased_scenario_reform_identity(scenario, code_revision=REVISION) == (
        scenario_reform_identity(scenario, code_revision=REVISION)
    )


@given(rate=st.floats(min_value=0, max_value=1, allow_nan=False), early=st.booleans())
@settings(max_examples=25, deadline=None)
def test_old_content_digest_is_unchanged(rate, early):
    changes = {"gov.example.rate": {"2027": rate}}
    identity = phased_scenario_reform_identity(
        Scenario(parameter_changes=changes, applied_before_data_load=early)
    )
    assert identity.reform_sha256 == canonical_sha256(
        {
            "representation": "policyengine-uk.scenario/v1",
            "payload": {
                "applied_before_data_load": early,
                "parameter_changes": changes,
                "simulation_modifier": None,
            },
        }
    )


def test_two_phases_bind_the_actual_split_and_common_parameters_once():
    scenario = _mixed(modifiers.raise_higher_rate)
    before, after = scenario.parts_by_data_load()
    assert before.parameter_changes == CHANGES
    assert not after.parameter_changes
    assert before.simulation_modifier is modifiers.raise_higher_rate
    assert after.simulation_modifier is modifiers.raise_basic_rate_to
    expected = {
        "representation": PHASED_SCENARIO_REPRESENTATION,
        "payload": {
            "application": PHASED_SCENARIO_APPLICATION,
            "before": _member(scenario_reform_identity(before, code_revision=REVISION)),
            "after": _member(scenario_reform_identity(after, code_revision=REVISION)),
        },
    }
    identity = phased_scenario_reform_identity(scenario, code_revision=REVISION)
    assert identity.representation == PHASED_SCENARIO_REPRESENTATION
    assert identity.reform_sha256 == canonical_sha256(expected)
    assert identity.binding == "code_revision"
    assert ReformIdentity.model_validate_json(identity.model_dump_json()) == identity


def test_phase_order_changes_digest_even_when_aggregate_modifiers_match():
    early_basic = _mixed(modifiers.raise_basic_rate, modifiers.raise_higher_rate)
    early_higher = _mixed(modifiers.raise_higher_rate, modifiers.raise_basic_rate)
    assert (
        phased_scenario_reform_identity(
            early_basic, code_revision=REVISION
        ).reform_sha256
        != phased_scenario_reform_identity(
            early_higher, code_revision=REVISION
        ).reform_sha256
    )


def test_old_v1_refuses_to_mislabel_a_mixed_scenario():
    scenario = _mixed()
    # Aggregate False is not permission to move the common parameters after load.
    assert scenario.applied_before_data_load is False
    with pytest.raises(ReceiptError, match="phased_scenario_reform_identity"):
        scenario_reform_identity(scenario, code_revision=REVISION)


@pytest.mark.parametrize("modifier", [None, modifiers.raise_basic_rate_to])
def test_single_effective_part_uses_its_true_phase_not_aggregate_flag(modifier):
    scenario = Scenario(
        parameter_changes=deepcopy(CHANGES),
        simulation_modifier=modifier,
        applied_before_data_load=True,
    ) + Scenario(parameter_changes={"gov.example.second": {"2027": 0.3}})
    assert scenario.applied_before_data_load is False
    before, after = scenario.parts_by_data_load()
    assert before is not None and after is None
    assert before.applied_before_data_load is True
    with pytest.raises(ReceiptError, match="effective data-load phase"):
        scenario_reform_identity(scenario, code_revision=REVISION)
    identity = phased_scenario_reform_identity(scenario, code_revision=REVISION)
    assert identity == scenario_reform_identity(before, code_revision=REVISION)
    assert identity.representation == "policyengine-uk.scenario/v1"
    assert identity._recheck() == identity
    # The bound effective part is a detached copy; the handle must still
    # notice a mutation to the original sum.
    scenario.parameter_changes["gov.example.second"]["2027"] = 0.4
    with pytest.raises(ReceiptError, match="changed after"):
        identity._recheck()


def test_single_effective_part_handle_notices_a_later_after_load_modifier():
    scenario = Scenario(
        parameter_changes=deepcopy(CHANGES), applied_before_data_load=True
    ) + Scenario(parameter_changes={"gov.example.second": {"2027": 0.3}})
    identity = phased_scenario_reform_identity(scenario, code_revision=REVISION)
    # Replacing the modifier invalidates the stored mixed-timing split.
    # The aggregate False now means parameters and modifier after load.
    scenario.simulation_modifier = modifiers.raise_higher_rate
    with pytest.raises(ReceiptError, match="changed after"):
        identity._recheck()


@pytest.mark.parametrize("phase", ["before", "after"])
def test_unsafe_modifier_in_either_phase_is_refused(phase):
    unsafe = lambda simulation: None  # noqa: E731
    scenario = _mixed(
        unsafe if phase == "before" else None,
        unsafe if phase == "after" else modifiers.raise_basic_rate_to,
    )
    with pytest.raises(ReceiptError):
        phased_scenario_reform_identity(scenario, code_revision=REVISION)


def test_live_handle_rechecks_original_parameter_changes():
    scenario = _mixed()
    identity = phased_scenario_reform_identity(scenario, code_revision=REVISION)
    scenario.parameter_changes["gov.example.rate"]["2027-04-06.2028-04-05"] = 0.25
    with pytest.raises(ReceiptError, match="changed after"):
        identity._recheck()


def test_live_handle_rechecks_original_timing():
    scenario = _mixed()
    identity = phased_scenario_reform_identity(scenario, code_revision=REVISION)
    # Native Scenario treats a post-construction field edit as one phase.
    scenario.applied_before_data_load = True
    with pytest.raises(ReceiptError, match="changed after"):
        identity._recheck()


def test_live_handle_rechecks_original_modifier():
    scenario = _mixed()
    identity = phased_scenario_reform_identity(scenario, code_revision=REVISION)
    scenario.simulation_modifier = modifiers.raise_higher_rate
    with pytest.raises(ReceiptError, match="changed after"):
        identity._recheck()


def test_live_handle_rechecks_modifier_defaults(monkeypatch):
    scenario = _mixed()
    identity = phased_scenario_reform_identity(scenario, code_revision=REVISION)
    monkeypatch.setattr(modifiers.raise_basic_rate_to, "__defaults__", (0.25,))
    with pytest.raises(ReceiptError, match="changed after"):
        identity._recheck()


def test_unchanged_live_handle_and_labels_keep_digest():
    scenario = _mixed()
    first = phased_scenario_reform_identity(scenario, code_revision=REVISION, name="A")
    second = phased_scenario_reform_identity(scenario, code_revision=REVISION, name="B")
    assert first._recheck() == first
    assert first.reform_sha256 == second.reform_sha256


@pytest.mark.parametrize("loaded", [False, True])
def test_v1_composition_cannot_override_or_flatten_phase_timing(loaded):
    identity = phased_scenario_reform_identity(_mixed(), code_revision=REVISION)
    if loaded:
        identity = ReformIdentity.model_validate_json(identity.model_dump_json())
    for early in (False, True):
        with pytest.raises(ReceiptError, match="cannot flatten or override"):
            composed_reform_identity([identity], applied_before_data_load=early)


def test_raw_payload_cannot_claim_a_phased_identity():
    with pytest.raises(ReceiptError, match="phased_scenario_reform_identity"):
        reform_identity({"before": {}, "after": {}}, PHASED_SCENARIO_REPRESENTATION)


def test_phase_api_requires_actual_scenario():
    with pytest.raises(ReceiptError, match="native policyengine-uk Scenario"):
        phased_scenario_reform_identity(
            SimpleNamespace(
                parameter_changes=CHANGES,
                simulation_modifier=None,
                applied_before_data_load=True,
            )
        )


@pytest.mark.parametrize(
    "binder", [scenario_reform_identity, phased_scenario_reform_identity]
)
def test_dated_reforms_cannot_disappear_from_either_representation(binder):
    scenario = Scenario.from_reform({"gov.example.rate": {"2027": 0.21}})
    with pytest.raises(ReceiptError, match="reform dictionary"):
        binder(scenario, code_revision=REVISION)


def test_published_identity_schema_accepts_the_added_representation():
    identity = phased_scenario_reform_identity(_mixed(), code_revision=REVISION)
    schema = ExecutionReceipt.json_schema()
    identity_schema = {
        "$defs": schema["$defs"],
        "$ref": "#/$defs/ReformIdentity",
    }
    jsonschema.validate(identity.model_dump(mode="json"), identity_schema)
