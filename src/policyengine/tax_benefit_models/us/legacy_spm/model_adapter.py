"""Let a policyengine-us release that cannot read SPM scope honour it.

#############################################################################
# BACKWARD COMPATIBILITY — MODEL OVERRIDE, REMOVE WHEN THE MODEL READS SCOPE. #
#                                                                            #
# policyengine-us 2.2.1 has no measurement-scope input, so it asks the       #
# canonical SPM provider for every SPM unit. ``prepare_microsimulation``     #
# decides per simulation:                                                    #
#                                                                            #
# - "native": the model defines ``spm_unit_spm_universe_status`` itself      #
#   (PolicyEngine/policyengine-us#9462). The derived declaration is just     #
#   an input, and nothing here changes the model.                            #
# - "override": it does not. A variable-only reform adds the declaration     #
#   input and wraps the SPM chain so that units OUTSIDE the measurement      #
#   never reach the provider and every SPM outcome for them is NaN ("not     #
#   measured"). Measured units keep the canonical values.                    #
#                                                                            #
# The override never copies a model formula: it wraps the installed ones.   #
# Before wrapping, it checks that the SPM chain still has the shape it was   #
# verified against, and refuses to run otherwise.                            #
#############################################################################

The override must be applied after the simulation is constructed (so policy
and structural reforms are in place) and before populations are built (so the
stored declaration loads as an input). Applying it again changes nothing.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal, Protocol

import numpy as np

from policyengine.tax_benefit_models.us.legacy_inputs import (
    _simulation_and_branches,
)

from .independence import INDEPENDENCE_ROLE
from .record import ADAPTER_REVISION
from .universe import SPMUniverseStatus

#: The measurement-scope input newer sources carry
#: (PolicyEngine/microcosm#977, PolicyEngine/policyengine-us#9462).
UNIVERSE_VARIABLE = "spm_unit_spm_universe_status"

#: Override mode only: whether an SPM unit is outside the measurement.
OUTSIDE_VARIABLE = "policyengine_legacy_spm_outside"

#: ``Variable.metadata`` key marking the variables the override adds.
ADAPTER_MARKER = "policyengine_legacy_spm_adapter"

ModelMode = Literal["native", "override"]

#: Canonical amount variables built by spm-calculator, and the
#: ``masked_policyengine_amount`` field each one returns.
THRESHOLD_FIELDS = {
    "spm_unit_reference_spm_threshold": "reference_threshold",
    "spm_unit_unadjusted_spm_threshold": "unadjusted_threshold",
    "spm_unit_geographic_adjustment": "geographic_factor",
    "spm_unit_spm_threshold": "threshold",
    "spm_unit_spm_threshold_housing_portion": "housing_portion",
}

#: Formula variables in the SPM measurement whose results become NaN for
#: outside units. The housing allocation comes first: with it NaN, the
#: installed capped-subsidy formula treats an outside unit as unassisted, so
#: it never asks the provider about one.
MASKED_FORMULA_VARIABLES = (
    "spm_unit_allocated_housing_subsidy",
    "spm_unit_allocated_tenant_payment",
    "spm_unit_capped_housing_subsidy",
    "spm_unit_benefits",
    "poverty_gap",
    "deep_poverty_line",
    "deep_poverty_gap",
    "spm_unit_is_in_spm_poverty",
    "spm_unit_is_in_deep_spm_poverty",
    "in_poverty",
    "in_deep_poverty",
    "person_in_poverty",
    "spm_unit_oecd_equiv_net_income",
)

#: Indicators that become floats (1.0, 0.0, or NaN when not measured).
FLOAT_INDICATORS = frozenset(
    {
        "spm_unit_is_in_spm_poverty",
        "spm_unit_is_in_deep_spm_poverty",
        "in_poverty",
        "in_deep_poverty",
        "person_in_poverty",
    }
)

#: ``adds``/``subtracts`` variables that carry NaN from a masked component.
NAN_PROPAGATING_VARIABLES = ("spm_unit_net_income", "poverty_line")

#: Ranks units, so it is recalculated over measured units only.
DECILE_VARIABLE = "spm_unit_income_decile"

#: Every SPM measurement variable that is NaN for an outside unit.
SPM_MEASUREMENT_VARIABLES = (
    *THRESHOLD_FIELDS,
    *MASKED_FORMULA_VARIABLES,
    *NAN_PROPAGATING_VARIABLES,
    DECILE_VARIABLE,
)


class CountrySimulation(Protocol):
    """The parts of a policyengine-us simulation the adapter uses."""

    tax_benefit_system: Any
    branches: Mapping[str, Any]

    def apply_reform(self, reform: Any) -> None: ...


class Population(Protocol):
    """A policyengine-core population, as a formula receives it."""

    entity: Any

    def __call__(self, variable_name: str, period: Any) -> Any: ...


def prepare_microsimulation(microsimulation: CountrySimulation) -> ModelMode:
    """Make a simulation and its branches read the legacy declarations.

    Returns the mode every simulation runs in.

    Raises:
        ValueError: if the model defines the scope input with members the
            declaration cannot use, if its SPM chain no longer has the shape
            the override was verified against, or if branches disagree.
    """
    modes: set[ModelMode] = set()
    for simulation in _simulation_and_branches(microsimulation):
        variable = simulation.tax_benefit_system.variables.get(UNIVERSE_VARIABLE)
        if variable is None:
            simulation.apply_reform(_override_reform())
            modes.add("override")
        elif ADAPTER_MARKER in (variable.metadata or {}):
            modes.add("override")
        else:
            _check_native_universe(variable)
            modes.add("native")
    if len(modes) != 1:
        raise ValueError(
            "A simulation and its branches disagree on whether policyengine-us "
            "reads SPM measurement scope natively."
        )
    return modes.pop()


def _check_native_universe(variable: Any) -> None:
    members = {item.name for item in getattr(variable, "possible_values", ()) or ()}
    needed = {SPMUniverseStatus.INCLUDED.value, SPMUniverseStatus.OUTSIDE.value}
    if not needed <= members:
        raise ValueError(
            f"policyengine-us defines {UNIVERSE_VARIABLE!r} with members "
            f"{sorted(members)}; the legacy SPM declarations need {sorted(needed)}."
        )


def _check_spm_chain(variables: Mapping[str, Any]) -> None:
    """Refuse a model whose SPM chain differs from the one verified."""
    problems = []
    for name in (*THRESHOLD_FIELDS, *MASKED_FORMULA_VARIABLES, DECILE_VARIABLE):
        if name not in variables:
            problems.append(f"{name} is not defined")
        elif not variables[name].formulas:
            problems.append(f"{name} has no formula")
    for name in NAN_PROPAGATING_VARIABLES:
        if name not in variables:
            problems.append(f"{name} is not defined")
        elif variables[name].formulas or not variables[name].adds:
            problems.append(f"{name} no longer adds up its components")
    if INDEPENDENCE_ROLE not in variables:
        problems.append(f"{INDEPENDENCE_ROLE} is not defined")
    if problems:
        raise ValueError(
            "The legacy SPM model override was verified against a different "
            "policyengine-us SPM chain: " + "; ".join(problems) + ". Re-verify it "
            "(docs/engineering/runbooks/us-legacy-spm-sources.md) before using "
            "legacy sources with this release."
        )


def _override_reform() -> type:
    from policyengine_core.enums import Enum as CoreEnum
    from policyengine_core.periods import YEAR
    from policyengine_core.reforms import Reform
    from policyengine_core.variables import Variable
    from policyengine_us.entities import SPMUnit
    from spm_calculator.errors import SPMInputError

    marker = {ADAPTER_MARKER: ADAPTER_REVISION}

    class SPMUniverseStatusInput(CoreEnum):
        INCLUDED = "Inside the SPM measurement population"
        OUTSIDE = "Outside the SPM measurement population"
        UNRESOLVED = "No SPM measurement-scope declaration"

    class spm_unit_spm_universe_status(Variable):
        value_type = CoreEnum
        possible_values = SPMUniverseStatusInput
        default_value = SPMUniverseStatusInput.UNRESOLVED
        entity = SPMUnit
        definition_period = YEAR
        label = "SPM measurement scope"
        documentation = (
            "BACKWARD COMPATIBILITY: added by policyengine.py for a "
            "policyengine-us release without a native SPM measurement-scope "
            "input, to carry the declaration derived for a legacy source."
        )
        metadata = marker

    class policyengine_legacy_spm_outside(Variable):
        value_type = bool
        entity = SPMUnit
        definition_period = YEAR
        label = "Outside the SPM measurement population"
        metadata = marker

        def formula(spm_unit, period, parameters):
            status = spm_unit(UNIVERSE_VARIABLE, period)
            unresolved = status == SPMUniverseStatusInput.UNRESOLVED
            if np.any(unresolved):
                raise SPMInputError(
                    "SPM_UNIVERSE_REQUIRED",
                    f"{int(np.sum(unresolved))} SPM units have no SPM "
                    f"measurement-scope declaration for {period}",
                )
            return status == SPMUniverseStatusInput.OUTSIDE

    class legacy_spm_declarations(Reform):
        def apply(self):
            _check_spm_chain(self.variables)
            self.add_variable(spm_unit_spm_universe_status)
            self.add_variable(policyengine_legacy_spm_outside)
            for name, field in THRESHOLD_FIELDS.items():
                self.update_variable(_threshold_variable(name, field))
            for name in MASKED_FORMULA_VARIABLES:
                self.update_variable(_masked_variable(self.variables[name]))
            self.update_variable(_income_decile_variable())

    return legacy_spm_declarations


def _outside(population: Population, period: Any) -> np.ndarray:
    if population.entity.key == "spm_unit":
        values = population(OUTSIDE_VARIABLE, period)
    else:
        values = population.spm_unit(OUTSIDE_VARIABLE, period)  # type: ignore[attr-defined]
    return np.asarray(values, dtype=bool)


def _threshold_variable(name: str, field: str) -> type:
    from policyengine_core.variables import Variable
    from policyengine_us.spm import masked_policyengine_amount

    def formula(spm_unit: Population, period: Any, parameters: Any) -> np.ndarray:
        outside = _outside(spm_unit, period)
        amounts = masked_policyengine_amount(spm_unit, period, field, ~outside)
        return np.where(outside, np.nan, amounts)

    return type(name, (Variable,), {"formula": formula, "__module__": __name__})


def _masked_variable(original: Any) -> type:
    """Wrap an installed formula variable so that outside units are NaN."""
    from policyengine_core.variables import Variable

    def formula(population: Population, period: Any, parameters: Any) -> np.ndarray:
        original_formula: Callable[..., Any] = original.get_formula(period)
        if original_formula.__code__.co_argcount == 2:
            values = original_formula(population, period)
        else:
            values = original_formula(population, period, parameters)
        return np.where(
            _outside(population, period),
            np.nan,
            np.asarray(values, dtype=np.float64),
        )

    attributes: dict[str, Any] = {"formula": formula, "__module__": __name__}
    if original.name in FLOAT_INDICATORS:
        attributes["value_type"] = float
        attributes["default_value"] = 0.0
    return type(original.name, (Variable,), attributes)


def _income_decile_variable() -> type:
    """Rank measured SPM units only; outside units have no decile.

    The installed formula ranks every unit by OECD-equivalised SPM income,
    weighted by people. With outside units' income NaN, it would place them
    in the top decile and count their weight, so the ranking is recalculated
    over measured units, with the same weights and the same ranking method.
    """
    from microdf import MicroSeries
    from policyengine_core.variables import Variable

    def formula(spm_unit: Population, period: Any, parameters: Any) -> np.ndarray:
        outside = _outside(spm_unit, period)
        income = np.asarray(spm_unit("spm_unit_oecd_equiv_net_income", period))
        weights = np.asarray(spm_unit("spm_unit_weight", period)) * np.asarray(
            spm_unit.nb_persons()  # type: ignore[attr-defined]
        )
        deciles = np.full(len(income), np.nan)
        measured = ~outside
        if measured.any():
            deciles[measured] = np.asarray(
                MicroSeries(income[measured], weights=weights[measured]).decile_rank()
            )
        return deciles

    return type(
        DECILE_VARIABLE,
        (Variable,),
        {
            "value_type": float,
            "default_value": 0.0,
            "formula": formula,
            "__module__": __name__,
        },
    )
