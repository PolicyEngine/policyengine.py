"""Keep the legacy SPM model override aligned with the installed model.

The override in ``legacy_spm.model_adapter`` must cover every policyengine-us
variable that depends on the canonical SPM provider; otherwise an upgrade
could add a consumer that sends units outside the measurement to the
provider. These checks rebuild that dependency set from the installed model
and from its formula sources, so a pin bump that changes the SPM chain fails
here first.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from types import SimpleNamespace

import pytest

pytest.importorskip("policyengine_us")
pytest.importorskip("spm_calculator.policyengine_adapter")

from policyengine.tax_benefit_models.us.legacy_spm import (  # noqa: E402
    model_adapter,
    prepare_microsimulation,
)
from policyengine.tax_benefit_models.us.legacy_spm.model_adapter import (  # noqa: E402
    ADAPTER_MARKER,
    MASKED_FORMULA_VARIABLES,
    NAN_PROPAGATING_VARIABLES,
    SPM_MEASUREMENT_VARIABLES,
    THRESHOLD_FIELDS,
    UNIVERSE_VARIABLE,
    _check_spm_chain,
)

#: Names whose call in a formula reaches the canonical SPM provider.
_PROVIDER_CALLS = {"policyengine_amount", "masked_policyengine_amount"}


def _formula_references(variable) -> tuple[set[str], set[str]]:
    """Return the string literals and called names in a variable's formulas."""
    strings: set[str] = set()
    calls: set[str] = set()
    for formula in variable.formulas.values():
        try:
            source = textwrap.dedent(inspect.getsource(formula))
        except (OSError, TypeError):
            continue
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.add(node.value)
            elif isinstance(node, ast.Call):
                function = node.func
                name = getattr(function, "id", None) or getattr(function, "attr", None)
                if name:
                    calls.add(name)
    return strings, calls


def _component_names(variable, system) -> set[str]:
    names: set[str] = set()
    for components in (variable.adds, variable.subtracts):
        if isinstance(components, str):
            parameter = system.parameters.get_child(components)
            components = parameter("2026-01-01")
        names.update(components or [])
    return names


def _provider_dependents(system) -> set[str]:
    consumers: dict[str, set[str]] = {}
    roots: set[str] = set()
    for name, variable in system.variables.items():
        strings, calls = _formula_references(variable)
        if calls & _PROVIDER_CALLS:
            roots.add(name)
        for reference in (strings | _component_names(variable, system)) & set(
            system.variables
        ):
            consumers.setdefault(reference, set()).add(name)
    dependents, frontier = set(roots), list(roots)
    while frontier:
        for consumer in consumers.get(frontier.pop(), ()):
            if consumer not in dependents:
                dependents.add(consumer)
                frontier.append(consumer)
    return dependents


def test_the_override_covers_every_variable_that_depends_on_the_provider():
    from policyengine_us.system import system

    dependents = _provider_dependents(system)
    assert set(THRESHOLD_FIELDS) <= dependents
    assert dependents <= set(SPM_MEASUREMENT_VARIABLES), sorted(
        dependents - set(SPM_MEASUREMENT_VARIABLES)
    )


def test_the_installed_chain_has_the_verified_shape():
    from policyengine_us.system import system

    _check_spm_chain(system.variables)


def test_the_installed_model_does_not_read_scope_natively_yet():
    """When this fails, policyengine-us reads scope (#9462): see the runbook."""
    from policyengine_us.system import system

    assert UNIVERSE_VARIABLE not in system.variables


# --- Chain-shape guard -------------------------------------------------------


def _variable(*, formulas=True, adds=None):
    return SimpleNamespace(
        formulas={"0001-01-01": object()} if formulas else {}, adds=adds
    )


def _verified_chain() -> dict:
    chain = {
        name: _variable()
        for name in (
            *THRESHOLD_FIELDS,
            *MASKED_FORMULA_VARIABLES,
            model_adapter.DECILE_VARIABLE,
        )
    }
    for name in NAN_PROPAGATING_VARIABLES:
        chain[name] = _variable(formulas=False, adds=["component"])
    chain[model_adapter.INDEPENDENCE_ROLE] = _variable()
    return chain


def test_a_verified_chain_passes():
    _check_spm_chain(_verified_chain())


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda chain: chain.pop("spm_unit_spm_threshold"), "is not defined"),
        (
            lambda chain: chain.__setitem__("poverty_gap", _variable(formulas=False)),
            "poverty_gap has no formula",
        ),
        (
            lambda chain: chain.__setitem__("spm_unit_net_income", _variable()),
            "spm_unit_net_income no longer adds up",
        ),
        (
            lambda chain: chain.pop(model_adapter.INDEPENDENCE_ROLE),
            "is_spm_independent_minor_role is not defined",
        ),
    ],
)
def test_a_changed_chain_is_refused(change, message):
    chain = _verified_chain()
    change(chain)
    with pytest.raises(ValueError, match=message):
        _check_spm_chain(chain)


# --- Mode selection ----------------------------------------------------------


class _FakeSimulation:
    def __init__(self, variables, branches=None):
        self.tax_benefit_system = SimpleNamespace(variables=variables)
        self.branches = branches or {}
        self.reforms = []

    def apply_reform(self, reform):
        self.reforms.append(reform)
        self.tax_benefit_system.variables[UNIVERSE_VARIABLE] = SimpleNamespace(
            metadata={ADAPTER_MARKER: 1}
        )


def _native_universe(members=("INCLUDED", "OUTSIDE", "UNRESOLVED")):
    return SimpleNamespace(
        metadata={},
        possible_values=[SimpleNamespace(name=member) for member in members],
    )


def test_a_model_without_native_scope_is_overridden_once_per_simulation():
    baseline = _FakeSimulation({})
    simulation = _FakeSimulation({}, {"baseline": baseline})
    assert prepare_microsimulation(simulation) == "override"
    assert prepare_microsimulation(simulation) == "override"
    assert len(simulation.reforms) == len(baseline.reforms) == 1


def test_a_model_with_native_scope_is_left_alone():
    simulation = _FakeSimulation({UNIVERSE_VARIABLE: _native_universe()})
    assert prepare_microsimulation(simulation) == "native"
    assert simulation.reforms == []


def test_a_native_scope_without_the_declared_members_is_refused():
    simulation = _FakeSimulation({UNIVERSE_VARIABLE: _native_universe(("IN", "OUT"))})
    with pytest.raises(ValueError, match="declarations need"):
        prepare_microsimulation(simulation)


def test_branches_must_agree_on_the_mode():
    native = _FakeSimulation({UNIVERSE_VARIABLE: _native_universe()})
    simulation = _FakeSimulation({}, {"baseline": native})
    with pytest.raises(ValueError, match="disagree"):
        prepare_microsimulation(simulation)
