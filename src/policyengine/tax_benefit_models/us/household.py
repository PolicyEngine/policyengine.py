"""Single-household calculation for the US model.

``calculate_household`` is the one-call entry point for the household
calculator journey: pass the people plus any per-entity overrides plus
an optional reform, get back a dot-accessible result.

.. code-block:: python

    import policyengine as pe

    # Single parent with one child in New York, $45k wages.
    result = pe.us.calculate_household(
        people=[
            {"age": 32, "employment_income": 45000, "is_tax_unit_head": True},
            {"age": 6, "is_tax_unit_dependent": True},
        ],
        tax_unit={"filing_status": "HEAD_OF_HOUSEHOLD"},
        household={"state_code": "NY"},
        year=2026,
        extra_variables=["adjusted_gross_income"],
    )
    print(result.tax_unit.income_tax)
    print(result.tax_unit.ctc, result.tax_unit.eitc)
    print(result.household.household_net_income)
    # Reform: zero out SNAP.
    reformed = pe.us.calculate_household(
        people=[
            {"age": 32, "employment_income": 45000, "is_tax_unit_head": True},
            {"age": 6, "is_tax_unit_dependent": True},
        ],
        tax_unit={"filing_status": "HEAD_OF_HOUSEHOLD"},
        household={"state_code": "NY"},
        year=2026,
        reform={"gov.usda.snap.income.deductions.earned_income": 0},
    )
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from policyengine.tax_benefit_models.common import (
    EntityResult,
    HouseholdResult,
    compile_reform,
    dispatch_extra_variables,
    validate_annual_household_inputs,
)
from policyengine.utils.household_validation import validate_household_input

from .model import us_latest

_GROUP_ENTITIES = ("marital_unit", "family", "spm_unit", "tax_unit", "household")


def _raise_unexpected_kwargs(unexpected: Mapping[str, Any]) -> None:
    from difflib import get_close_matches

    lines = ["calculate_household received unsupported keyword arguments:"]
    for name in unexpected:
        suggestions = get_close_matches(name, _ALLOWED_KWARGS, n=1, cutoff=0.5)
        hint = f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
        if name == "benunit":
            hint = " — `benunit` is UK-only; the US uses `tax_unit`, `marital_unit`, `family`, or `spm_unit`"
        lines.append(f"  - '{name}'{hint}")
    lines.append(
        "Valid kwargs: people, marital_unit, family, spm_unit, tax_unit, "
        "household, year, reform, extra_variables."
    )
    raise TypeError("\n".join(lines))


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


_ALLOWED_KWARGS = frozenset(
    {
        "people",
        "marital_unit",
        "family",
        "spm_unit",
        "tax_unit",
        "household",
        "year",
        "reform",
        "extra_variables",
    }
)


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
    **unexpected: Any,
) -> HouseholdResult:
    """Compute tax and benefit variables for a single US household.

    Args:
        people: One dict per person with US variable names as keys
            (``age``, ``employment_income``, ``is_tax_unit_head``,
            ``is_tax_unit_dependent`` ...). Must be non-empty.
        marital_unit, family, spm_unit, tax_unit, household: Optional
            per-entity overrides, each keyed by variable name (e.g.
            ``tax_unit={"filing_status": "SINGLE"}``,
            ``household={"state_code": "NY"}``).
        year: Calendar year to compute for. Defaults to 2026.
        reform: Optional reform as ``{parameter_path: value}`` or
            ``{parameter_path: {effective_date: value}}``. Scalar
            values default to ``{year}-01-01``; invalid parameter
            paths raise with a close-match suggestion.
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
            if a variable is placed on the wrong entity (e.g.
            ``filing_status`` on ``people``), or if ``extra_variables``
            / ``reform`` names a variable or parameter path not defined
            on the US model. Raises if ``year`` is not an annual calendar
            year or if household input values are already periodized.
    """
    if unexpected:
        _raise_unexpected_kwargs(unexpected)

    people = list(people)
    entities = {
        "marital_unit": dict(marital_unit or {}),
        "family": dict(family or {}),
        "spm_unit": dict(spm_unit or {}),
        "tax_unit": dict(tax_unit or {}),
        "household": dict(household or {}),
    }
    year = validate_annual_household_inputs(
        year=year,
        entities={
            "people": people,
            **{name: [value] for name, value in entities.items()},
        },
    )

    from policyengine_us import Simulation

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
    reform_dict = compile_reform(reform, year=year, model_version=us_latest)

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
