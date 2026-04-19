"""Single-household calculation for the US model.

``calculate_household`` is the one-call entry point for the household
calculator journey: pass the people plus any per-entity overrides plus
an optional reform, get back a dot-accessible result.

.. code-block:: python

    import policyengine as pe

    result = pe.us.calculate_household(
        people=[{"age": 35, "employment_income": 60000}],
        tax_unit={"filing_status": "SINGLE"},
        year=2026,
        reform={"gov.irs.credits.ctc.amount.adult_dependent": 1000},
        extra_variables=["adjusted_gross_income"],
    )
    print(result.tax_unit.income_tax)
    print(result.tax_unit.adjusted_gross_income)
    print(result.household.household_net_income)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from policyengine.tax_benefit_models.common import (
    EntityResult,
    HouseholdResult,
    compile_reform,
    dispatch_extra_variables,
)
from policyengine.utils.household_validation import validate_household_input

from .model import us_latest

_GROUP_ENTITIES = ("marital_unit", "family", "spm_unit", "tax_unit", "household")


def _default_output_columns(
    extra_by_entity: Mapping[str, list[str]],
) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for entity, defaults in us_latest.entity_variables.items():
        columns = list(defaults)
        for extra in extra_by_entity.get(entity, []):
            if extra not in columns:
                columns.append(extra)
        merged[entity] = columns
    for entity, extras in extra_by_entity.items():
        merged.setdefault(entity, list(extras))
    return merged


def _safe_convert(value: Any) -> Any:
    try:
        return float(value)
    except (ValueError, TypeError):
        return str(value) if value is not None else None


def _build_situation(
    *,
    people: list[Mapping[str, Any]],
    marital_unit: Mapping[str, Any],
    family: Mapping[str, Any],
    spm_unit: Mapping[str, Any],
    tax_unit: Mapping[str, Any],
    household: Mapping[str, Any],
    year: int,
) -> dict[str, Any]:
    year_str = str(year)

    def _periodise(spec: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        return {key: {year_str: value} for key, value in spec.items() if key != "id"}

    person_ids = [f"person_{i}" for i in range(len(people))]
    persons = {pid: _periodise(person) for pid, person in zip(person_ids, people)}

    def _group(spec: Mapping[str, Any]) -> dict[str, Any]:
        return {"members": list(person_ids), **_periodise(spec)}

    return {
        "people": persons,
        "marital_units": {"marital_unit_0": _group(marital_unit)},
        "families": {"family_0": _group(family)},
        "spm_units": {"spm_unit_0": _group(spm_unit)},
        "tax_units": {"tax_unit_0": _group(tax_unit)},
        "households": {"household_0": _group(household)},
    }


def calculate_household(
    *,
    people: list[Mapping[str, Any]],
    marital_unit: Optional[Mapping[str, Any]] = None,
    family: Optional[Mapping[str, Any]] = None,
    spm_unit: Optional[Mapping[str, Any]] = None,
    tax_unit: Optional[Mapping[str, Any]] = None,
    household: Optional[Mapping[str, Any]] = None,
    year: int = 2026,
    reform: Optional[Mapping[str, Any]] = None,
    extra_variables: Optional[list[str]] = None,
) -> HouseholdResult:
    """Compute tax and benefit variables for a single US household.

    Args:
        people: One dict per person with US variable names as keys
            (``age``, ``employment_income``, ``is_tax_unit_head`` ...).
        marital_unit, family, spm_unit, tax_unit, household: Optional
            per-entity overrides, each keyed by variable name (e.g.
            ``tax_unit={"filing_status": "SINGLE"}``).
        year: Calendar year to compute for. Defaults to 2026.
        reform: Optional reform as ``{parameter_path: value}`` or
            ``{parameter_path: {effective_date: value}}``. See
            :func:`policyengine.tax_benefit_models.common.compile_reform`.
        extra_variables: Flat list of variable names to compute beyond
            the default output columns; the library dispatches each
            name to its entity. Unknown names raise ``ValueError``
            with a close-match suggestion.

    Returns:
        :class:`HouseholdResult` with dot-accessible per-entity
        variables. Singleton entities (``tax_unit``, ``household``, ...)
        return :class:`EntityResult`; ``person`` returns a list of them.

    Raises:
        ValueError: if any input dict uses an unknown variable name,
            or if ``extra_variables`` names a variable not defined on
            the US model.
    """
    from policyengine_us import Simulation

    people = list(people)
    entities = {
        "marital_unit": dict(marital_unit or {}),
        "family": dict(family or {}),
        "spm_unit": dict(spm_unit or {}),
        "tax_unit": dict(tax_unit or {}),
        "household": dict(household or {}),
    }

    validate_household_input(
        model_version=us_latest,
        entities={
            "person": people,
            **{name: [value] for name, value in entities.items()},
        },
    )

    extra_by_entity = dispatch_extra_variables(
        model_version=us_latest,
        names=extra_variables or [],
    )
    output_columns = _default_output_columns(extra_by_entity)
    reform_dict = compile_reform(reform)

    simulation = Simulation(
        situation=_build_situation(
            people=people,
            marital_unit=entities["marital_unit"],
            family=entities["family"],
            spm_unit=entities["spm_unit"],
            tax_unit=entities["tax_unit"],
            household=entities["household"],
            year=year,
        ),
        reform=reform_dict,
    )

    result = HouseholdResult()
    for entity, columns in output_columns.items():
        raw = {
            variable: list(simulation.calculate(variable, period=year, map_to=entity))
            for variable in columns
        }
        if entity == "person":
            result["person"] = [
                EntityResult(
                    {variable: _safe_convert(raw[variable][i]) for variable in columns}
                )
                for i in range(len(people))
            ]
        else:
            result[entity] = EntityResult(
                {variable: _safe_convert(raw[variable][0]) for variable in columns}
            )
    return result
