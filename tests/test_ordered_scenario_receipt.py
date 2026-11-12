"""The public ordered plan binds exactly the native phases it executes."""

import importlib
import multiprocessing
import pickle
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from policyengine_uk.utils.scenario import Scenario

from policyengine.provenance.ordered_scenario import (
    BoundOrderedScenario,
    OrderedScenarioPlan,
    bind_ordered_scenario_plan,
    build_ordered_scenario,
    ordered_scenario_reform_identity,
)
from policyengine.provenance.receipt import (
    ExecutionReceipt,
    ReceiptError,
    ReformIdentity,
    composed_reform_identity,
    reform_identity,
    scenario_reform_identity,
)
from tests import ordered_receipt_modifiers as modifiers

REVISION = {"repository": "PolicyEngine/test", "git_sha": "a" * 40}


def leaf(function):
    return function, dict(REVISION)


def test_two_leaves_in_each_phase_preserve_noncommutative_order_and_repetition():
    bound = build_ordered_scenario(
        before_modifiers=[leaf(modifiers.add_one), leaf(modifiers.double)],
        after_modifiers=[leaf(modifiers.double), leaf(modifiers.add_one)],
    )
    before, after = bound.scenario.parts_by_data_load()
    simulation = SimpleNamespace(ordered_value=1, ordered_trace=[])
    before.simulation_modifier(simulation)
    assert simulation.ordered_value == 4
    simulation.ordered_trace.append("load")
    after.simulation_modifier(simulation)
    assert simulation.ordered_value == 9
    assert simulation.ordered_trace == ["add", "double", "load", "double", "add"]
    assert ordered_scenario_reform_identity(bound.plan) == bound.identity


def test_parameters_occur_once_before_data_load():
    bound = build_ordered_scenario(
        {"gov.example.rate": {"2027": 0.2}},
        after_modifiers=[leaf(modifiers.add_one)],
    )
    before, after = bound.scenario.parts_by_data_load()
    assert before.parameter_changes == {"gov.example.rate": {"2027": 0.2}}
    assert not after.parameter_changes


def test_original_parameter_mutation_is_refused():
    parameters = {"gov.example.rate": {"2027": 0.2}}
    bound = build_ordered_scenario(parameters)
    identity = bound.identity
    parameters["gov.example.rate"]["2027"] = 0.3
    with pytest.raises(ValueError, match="changed after"):
        identity._recheck()


def execute_bound(bound):
    """A trusted worker definition; callable locators never come from plan data."""
    before, after = bound.scenario.parts_by_data_load()
    simulation = SimpleNamespace(ordered_value=1, ordered_trace=[])
    if before and before.simulation_modifier:
        before.simulation_modifier(simulation)
    simulation.ordered_trace.append("load")
    if after and after.simulation_modifier:
        after.simulation_modifier(simulation)
    return (
        simulation.ordered_value,
        simulation.ordered_trace,
        bound.identity.model_dump(),
    )


@settings(max_examples=8, deadline=None)
@given(
    before=st.lists(st.booleans(), max_size=4),
    after=st.lists(st.booleans(), max_size=4),
)
def test_arbitrary_order_and_repetition_match_the_executed_plan(before, after):
    functions = {True: modifiers.add_one, False: modifiers.double}
    bound = build_ordered_scenario(
        before_modifiers=[leaf(functions[x]) for x in before],
        after_modifiers=[leaf(functions[x]) for x in after],
    )
    value = 1
    for operation in before + after:
        value = value + 1 if operation else value * 2
    assert execute_bound(bound)[0] == value
    assert len(bound.plan.before.modifier_leaves) == len(before)
    assert len(bound.plan.after.modifier_leaves) == len(after)


def test_order_and_phase_change_both_identity_and_actual_effect():
    first = build_ordered_scenario(
        before_modifiers=[leaf(modifiers.add_one), leaf(modifiers.double)]
    )
    reverse = build_ordered_scenario(
        before_modifiers=[leaf(modifiers.double), leaf(modifiers.add_one)]
    )
    shifted = build_ordered_scenario(
        after_modifiers=[leaf(modifiers.add_one), leaf(modifiers.double)]
    )
    assert execute_bound(first)[0] == 4
    assert execute_bound(reverse)[0] == 3
    assert execute_bound(first)[1] != execute_bound(shifted)[1]
    assert len({x.identity.reform_sha256 for x in (first, reverse, shifted)}) == 3


def test_native_simulation_runs_the_same_two_before_and_two_after_leaves(monkeypatch):
    from policyengine_uk import Simulation

    observed = []
    original = Simulation.build_from_situation

    def record_load(simulation, situation):
        observed.append(simulation.max_spiral_loops)
        return original(simulation, situation)

    monkeypatch.setattr(Simulation, "build_from_situation", record_load)
    bound = build_ordered_scenario(
        before_modifiers=[leaf(modifiers.bump_limit), leaf(modifiers.scale_limit)],
        after_modifiers=[leaf(modifiers.scale_limit), leaf(modifiers.bump_limit)],
    )
    simulation = Simulation(
        scenario=bound.scenario,
        situation={
            "people": {"p": {"age": {2027: 40}}},
            "benunits": {"b": {"members": ["p"]}},
            "households": {"h": {"members": ["p"]}},
        },
    )
    assert observed == [22, 10]  # Reform loads after early leaves; baseline is native.
    assert simulation.max_spiral_loops == 45
    assert bound.identity._recheck() == bound.identity


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"gov.example.rate": {"2027": 0.2}},
        {"gov.example.cap": {"2027": float("inf")}},
    ],
)
def test_parameter_only_plans_keep_the_exact_existing_scenario_digest(changes):
    bound = build_ordered_scenario(changes)
    expected = scenario_reform_identity(
        Scenario(parameter_changes=changes, applied_before_data_load=True)
    )
    assert bound.identity == expected
    loaded = OrderedScenarioPlan.model_validate_json(bound.plan.model_dump_json())
    assert ordered_scenario_reform_identity(loaded) == expected


def test_plan_is_deeply_immutable_and_json_round_trips():
    bound = build_ordered_scenario(
        {"gov.example.rate": {"2027": 0.2}},
        before_modifiers=[leaf(modifiers.add_default)],
    )
    with pytest.raises(TypeError):
        bound.plan.before.parameter_changes["gov.example.rate"]["2027"] = 0.3
    with pytest.raises(ValueError):
        bound.plan.before.modifier_leaves = ()
    encoded = bound.model_dump_json()
    loaded = BoundOrderedScenario.model_validate_json(encoded)
    assert loaded.model_dump_json() == encoded
    with pytest.raises(ReceiptError, match="data-only"):
        loaded.scenario
    rebound = bind_ordered_scenario_plan(
        loaded.plan, before_modifiers=[leaf(modifiers.add_default)]
    )
    assert rebound.identity == bound.identity


@pytest.mark.parametrize("target", ["before", "after"])
def test_original_leaf_list_and_revision_mutations_fail_live_recheck(target):
    leaves = [leaf(modifiers.add_one)]
    bound = build_ordered_scenario(**{target + "_modifiers": leaves})
    identity = bound.identity
    leaves.append(leaf(modifiers.double))
    with pytest.raises(ReceiptError, match="changed after"):
        identity._recheck()
    leaves.pop()
    leaves[0][1]["git_sha"] = "b" * 40
    with pytest.raises(ReceiptError, match="changed after"):
        identity._recheck()


@pytest.mark.parametrize("target", ["phase", "parameters", "modifier", "adapter"])
def test_mutated_actual_native_execution_is_refused(target):
    bound = build_ordered_scenario(
        {"gov.example.rate": {"2027": 0.2}},
        before_modifiers=[leaf(modifiers.add_one)],
        after_modifiers=[leaf(modifiers.double)],
    )
    identity = bound.identity
    native = bound.scenario
    if target == "phase":
        native.applied_before_data_load = True
    elif target == "parameters":
        native.parameter_changes["gov.example.rate"]["2027"] = 0.3
    elif target == "modifier":
        native.simulation_modifier = modifiers.add_one
    else:
        bound._adapters[0].phase = "after"
    with pytest.raises(ReceiptError):
        identity._recheck()


def test_modified_leaf_defaults_code_and_module_state_are_refused(monkeypatch):
    bound = build_ordered_scenario(before_modifiers=[leaf(modifiers.add_default)])
    identity = bound.identity
    with monkeypatch.context() as patch:
        patch.setattr(modifiers.add_default, "__defaults__", (4,))
        with pytest.raises(ReceiptError):
            identity._recheck()
    with monkeypatch.context() as patch:
        patch.setattr(modifiers.add_one, "__code__", modifiers.double.__code__)
        with pytest.raises(ReceiptError):
            identity._recheck()
    with monkeypatch.context() as patch:
        patch.setattr(modifiers, "unexpected_state", 3, raising=False)
        with pytest.raises(ReceiptError):
            identity._recheck()


def test_adapter_implementation_replacement_is_refused(monkeypatch):
    from policyengine.provenance import ordered_scenario as api

    bound = build_ordered_scenario(before_modifiers=[leaf(modifiers.add_one)])
    identity = bound.identity
    monkeypatch.setattr(api._OrderedModifier, "__call__", lambda self, simulation: None)
    with pytest.raises(ReceiptError, match="adapter"):
        identity._recheck()


def test_pickle_and_real_spawn_worker_rebind_the_actual_trusted_leaves():
    bound = build_ordered_scenario(
        before_modifiers=[leaf(modifiers.add_one), leaf(modifiers.double)],
        after_modifiers=[leaf(modifiers.double), leaf(modifiers.add_one)],
    )
    restored = pickle.loads(pickle.dumps(bound))
    assert execute_bound(restored) == execute_bound(bound)
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        assert pool.submit(execute_bound, bound).result(timeout=60) == execute_bound(
            bound
        )


def test_tampered_portable_proofs_cannot_rebind_to_trusted_jobs():
    bound = build_ordered_scenario(before_modifiers=[leaf(modifiers.add_one)])
    portable = bound.plan.model_dump(mode="json")
    portable["before"]["modifier_leaves"][0]["source_sha256"] = "b" * 64
    assert ordered_scenario_reform_identity(portable) != bound.identity
    with pytest.raises(ReceiptError, match="do not match"):
        bind_ordered_scenario_plan(portable, before_modifiers=[leaf(modifiers.add_one)])


def test_data_only_recomposer_never_imports_receipt_locators(monkeypatch):
    bound = build_ordered_scenario(before_modifiers=[leaf(modifiers.add_one)])
    portable = bound.plan.model_dump(mode="json")
    portable["before"]["modifier_leaves"][0]["module"] = (
        "nonexistent_receipt_locator_never_import"
    )

    def refuse_import(*args, **kwargs):
        raise AssertionError("Receipt locators must remain data")

    monkeypatch.setattr(importlib, "import_module", refuse_import)
    assert ordered_scenario_reform_identity(portable).binding == "code_revision"


@pytest.mark.parametrize(
    "mutation", ["extra", "phase", "after_parameters", "leaf_extra", "defaults"]
)
def test_unknown_or_unsupported_plan_fields_fail_closed(mutation):
    portable = build_ordered_scenario(
        before_modifiers=[leaf(modifiers.add_one)]
    ).plan.model_dump(mode="json")
    if mutation == "extra":
        portable["invented"] = True
    elif mutation == "phase":
        portable["application"] = "after_then_before"
    elif mutation == "after_parameters":
        portable["after"]["parameter_changes"] = {"gov.example.rate": 1}
    elif mutation == "leaf_extra":
        portable["before"]["modifier_leaves"][0]["leaf_count"] = 1
    else:
        portable["before"]["modifier_leaves"][0]["module_defaults"] = {
            "x": {"type": "object"}
        }
    with pytest.raises(ValueError):
        ordered_scenario_reform_identity(portable)


def test_arbitrary_closures_dated_reforms_and_old_composition_remain_refused():
    with pytest.raises(ReceiptError):
        build_ordered_scenario(before_modifiers=[leaf(lambda simulation: None)])
    dated = Scenario.from_reform({"gov.example.rate": {"2027": 0.2}})
    with pytest.raises(ReceiptError):
        build_ordered_scenario(before_modifiers=[leaf(dated.simulation_modifier)])
    bound = build_ordered_scenario(before_modifiers=[leaf(modifiers.add_one)])
    with pytest.raises(ReceiptError, match="cannot flatten or override"):
        composed_reform_identity([bound.identity], applied_before_data_load=True)
    with pytest.raises(ReceiptError, match="ordered_scenario_reform_identity"):
        reform_identity(
            bound.plan.model_dump(mode="json"), bound.identity.representation
        )


def test_execution_receipt_schema_accepts_new_identity():
    identity = build_ordered_scenario(
        before_modifiers=[leaf(modifiers.add_one)]
    ).identity
    schema = ExecutionReceipt.json_schema()
    jsonschema.validate(
        identity.model_dump(mode="json"),
        {"$defs": schema["$defs"], "$ref": "#/$defs/ReformIdentity"},
    )


def test_published_schema_and_vectors_reproduce_the_official_api():
    import json

    from scripts.generate_ordered_scenario_vectors import build_vectors

    directory = Path(__file__).resolve().parents[1] / "src/policyengine/data/schemas"
    schema = json.loads(
        (directory / "ordered_scenario_plan.v1.schema.json").read_text()
    )
    assert schema == OrderedScenarioPlan.json_schema()
    vectors = json.loads(
        (directory / "ordered_scenario_plan.v1.vectors.json").read_text()
    )
    assert vectors == build_vectors()
    for vector in vectors["valid"]:
        jsonschema.validate(vector["plan"], schema)
        identity = ordered_scenario_reform_identity(vector["plan"])
        assert identity.model_dump(mode="json") == vector["identity"]
    for vector in vectors["invalid"]:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(vector["plan"], schema)
        with pytest.raises(ValueError):
            ordered_scenario_reform_identity(vector["plan"])


def test_worker_rebinding_refuses_source_defaults_changed_after_planning(monkeypatch):
    bound = build_ordered_scenario(before_modifiers=[leaf(modifiers.add_default)])
    packet = pickle.dumps(bound)
    monkeypatch.setattr(modifiers.add_default, "__defaults__", (9,))
    with pytest.raises(ReceiptError):
        pickle.loads(packet)


def test_leaf_source_file_edits_after_planning_fail_recheck(tmp_path):
    import importlib.util
    import sys

    path = tmp_path / "ordered_temporary_leaf.py"
    path.write_text("def change(simulation):\n    simulation.ordered_value += 1\n")
    spec = importlib.util.spec_from_file_location("ordered_temporary_leaf", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module.__name__] = module
    try:
        spec.loader.exec_module(module)
        bound = build_ordered_scenario(before_modifiers=[leaf(module.change)])
        identity = bound.identity
        path.write_text(path.read_text() + "\n# Changed source bytes.\n")
        with pytest.raises(ReceiptError):
            identity._recheck()
    finally:
        sys.modules.pop(module.__name__, None)


def test_bypassing_frozen_plan_fields_cannot_rewrite_a_bound_execution():
    bound = build_ordered_scenario(before_modifiers=[leaf(modifiers.add_one)])
    identity = bound.identity
    object.__setattr__(bound.plan.before, "modifier_leaves", ())
    with pytest.raises(ReceiptError):
        identity._recheck()


def test_ordered_modifier_identity_cannot_downgrade_to_content_binding():
    identity = build_ordered_scenario(before_modifiers=[leaf(modifiers.add_one)])
    payload = identity.identity.model_dump(mode="json")
    payload["binding"] = "content"
    with pytest.raises(ValueError, match="code_revision"):
        ReformIdentity.model_validate(payload)
    schema = ExecutionReceipt.json_schema()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            payload, {"$defs": schema["$defs"], "$ref": "#/$defs/ReformIdentity"}
        )


def test_a_lookalike_callable_cannot_replace_the_package_phase_adapter():
    bound = build_ordered_scenario(
        before_modifiers=[leaf(modifiers.add_one)],
        after_modifiers=[leaf(modifiers.double)],
    )
    native = bound.scenario
    identity = bound.identity

    class Lookalike:
        owner = bound
        phase = "before"

        def __call__(self, simulation):
            raise AssertionError("A substituted adapter must never execute")

    fake = Lookalike()
    bound._adapters = (fake, bound._adapters[1])
    native._timed_modifiers = (fake, native._timed_modifiers[1])
    with pytest.raises(ReceiptError, match="adapter changed"):
        identity._recheck()


def test_compiler_annotation_helpers_do_not_claim_native_runtime_callables():
    from policyengine.provenance.ordered_scenario import _codes

    code = compile(
        "from __future__ import annotations\n"
        "class Example:\n"
        " value: int\n"
        " def method(self, other: int) -> str: return str(other)\n",
        "synthetic_annotations.py",
        "exec",
        dont_inherit=True,
    )
    found = _codes(code)
    assert "Example.method" in found
    assert not any(name.rsplit(".", 1)[-1] == "__annotate__" for name in found)
