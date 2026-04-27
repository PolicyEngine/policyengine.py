"""Single-household calculation for the UK model.

.. code-block:: python

    import policyengine as pe

    # Lone parent + one child, £30k wages.
    result = pe.uk.calculate_household(
        people=[
            {"age": 32, "employment_income": 30000},
            {"age": 6},
        ],
        benunit={"would_claim_child_benefit": True},
        year=2026,
    )
    print(result.person[0].income_tax)
    print(result.benunit.child_benefit)
    print(result.household.hbai_household_net_income)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from policyengine.tax_benefit_models.common import (
    EntityResult,
    HouseholdResult,
    compile_reform,
    dispatch_extra_variables,
    normalize_axes,
    values_for_entity,
)
from policyengine.utils.household_validation import validate_household_input

from .model import uk_latest


def _default_output_columns(
    extra_by_entity: Mapping[str, list[str]],
) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for entity, defaults in uk_latest.entity_variables.items():
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
    benunit: Mapping[str, Any],
    household: Mapping[str, Any],
    year: int,
    axes: Optional[list[Any]] = None,
) -> dict[str, Any]:
    year_str = str(year)

    def _periodise(spec: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        return {key: {year_str: value} for key, value in spec.items() if key != "id"}

    person_ids = [f"person_{i}" for i in range(len(people))]
    persons = {pid: _periodise(person) for pid, person in zip(person_ids, people)}

    def _group(spec: Mapping[str, Any]) -> dict[str, Any]:
        return {"members": list(person_ids), **_periodise(spec)}

    situation = {
        "people": persons,
        "benunits": {"benunit_0": _group(benunit)},
        "households": {"household_0": _group(household)},
    }
    if axes is not None:
        situation["axes"] = axes
    return situation


_ALLOWED_KWARGS = frozenset(
    {"people", "benunit", "household", "year", "reform", "extra_variables", "axes"}
)


def _raise_unexpected_kwargs(unexpected: Mapping[str, Any]) -> None:
    from difflib import get_close_matches

    lines = ["calculate_household received unsupported keyword arguments:"]
    for name in unexpected:
        suggestions = get_close_matches(name, _ALLOWED_KWARGS, n=1, cutoff=0.5)
        hint = f" (did you mean '{suggestions[0]}'?)" if suggestions else ""
        if name in {"tax_unit", "marital_unit", "family", "spm_unit"}:
            hint = (
                f" — `{name}` is US-only; the UK groups persons into a single `benunit`"
            )
        lines.append(f"  - '{name}'{hint}")
    lines.append(
        "Valid kwargs: people, benunit, household, year, reform, extra_variables, axes."
    )
    raise TypeError("\n".join(lines))


def calculate_household(
    *,
    people: list[Mapping[str, Any]],
    benunit: Optional[Mapping[str, Any]] = None,
    household: Optional[Mapping[str, Any]] = None,
    year: int = 2026,
    reform: Optional[Mapping[str, Any]] = None,
    extra_variables: Optional[list[str]] = None,
    axes: Optional[list[Any]] = None,
    **unexpected: Any,
) -> HouseholdResult:
    """Compute tax and benefit variables for a single UK household.

    Args:
        people: One dict per person (keys are UK variable names).
            Must be non-empty.
        benunit, household: Optional per-entity overrides.
        year: Calendar year. Defaults to 2026.
        reform: Optional reform dict. Scalar values default to
            ``{year}-01-01``; invalid parameter paths raise with a
            close-match suggestion.
        extra_variables: Flat list of extra UK variables to compute;
            the library dispatches each to its entity.
        axes: Optional household-calculator axes. Pass either the lower-level
            ``[[{"name": ..., "min": ..., "max": ..., "count": ...}]]``
            shape or a flat list of axis dictionaries. Missing ``period``
            values default to ``year``. When axes are present, result values
            are lists ordered by the axis grid instead of scalars.

    Returns:
        :class:`HouseholdResult` with dot-accessible entity results.

    Raises:
        ValueError: on unknown or mis-placed variable names, or
            unknown reform parameter paths.
        TypeError: on US-only kwargs (``tax_unit``, etc.) or other
            unsupported keyword arguments.
    """
    if unexpected:
        _raise_unexpected_kwargs(unexpected)

    from policyengine_uk import Simulation

    people = list(people)
    benunit_dict = dict(benunit or {})
    household_dict = dict(household or {})

    validate_household_input(
        model_version=uk_latest,
        entities={
            "person": people,
            "benunit": [benunit_dict],
            "household": [household_dict],
        },
    )

    extra_by_entity = dispatch_extra_variables(
        model_version=uk_latest,
        names=extra_variables or [],
    )
    output_columns = _default_output_columns(extra_by_entity)
    reform_dict = compile_reform(reform, year=year, model_version=uk_latest)
    normalized_axes = normalize_axes(axes=axes, year=year, model_version=uk_latest)
    axes_active = normalized_axes is not None

    simulation = Simulation(
        situation=_build_situation(
            people=people,
            benunit=benunit_dict,
            household=household_dict,
            year=year,
            axes=normalized_axes,
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
                    {
                        variable: values_for_entity(
                            [_safe_convert(value) for value in raw[variable]],
                            entity_index=i,
                            entity_count=len(people),
                            axes_active=axes_active,
                        )
                        for variable in columns
                    }
                )
                for i in range(len(people))
            ]
        else:
            result[entity] = EntityResult(
                {
                    variable: (
                        [_safe_convert(value) for value in raw[variable]]
                        if axes_active
                        else _safe_convert(raw[variable][0])
                    )
                    for variable in columns
                }
            )
    return result
