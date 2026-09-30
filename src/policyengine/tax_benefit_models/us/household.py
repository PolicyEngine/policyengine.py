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
        household={"state_code": "NY", "county_fips": "36061"},
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
        household={"state_code": "NY", "county_fips": "36061"},
        year=2026,
        reform={"gov.usda.snap.income.deductions.earned_income": 0},
    )
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Mapping
from typing import Any, Optional

from policyengine.tax_benefit_models.common import (
    EntityResult,
    HouseholdResult,
    compile_reform,
    dispatch_extra_variables,
    normalize_axes,
    validate_annual_household_inputs,
    values_for_entity,
)
from policyengine.utils.household_validation import validate_household_input

from .model import us_latest
from .spm import (
    SPMSelection,
    calculation_provenance,
    resolve_household_spm_selection,
)

_GROUP_ENTITIES = ("marital_unit", "family", "spm_unit", "tax_unit", "household")

# Household inputs that name a county. SPM county measurement reads only
# ``county_fips``, but a household that names its county another way still
# asked for a county measurement, so it keeps the county selection and gets the
# error that asks for ``county_fips`` instead of a national result.
_COUNTY_INPUTS = ("county_fips", "county", "county_str")


def _is_absent(name: str, value: Any) -> bool:
    """Whether a county input's value means that no county was given.

    Missing values (``None``, empty text, NaN or the text ``"nan"``,
    ``pd.NA``) are absent, as the country model's county check also treats
    them, and so is ``"UNKNOWN"``, the ``county`` enum's default, for
    ``county`` and ``county_str`` only. Anything else, including a malformed
    code such as ``6037``, names a county and so reaches the county
    selection's typed error. This decides only the SPM selection: the country
    model itself rejects some of these as inputs (``pd.NA`` and bytes fail to
    serialize whatever the geography).
    """
    if value is None:
        return True
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    if isinstance(value, str):
        if value == "" or value.lower() == "nan":
            return True
        return name != "county_fips" and value == "UNKNOWN"
    if isinstance(value, numbers.Number) and not isinstance(value, bool):
        try:
            return math.isnan(value)
        except TypeError:
            return False
    import pandas as pd

    return value is pd.NA


def _names_county(
    household: Mapping[str, Any], axes: Optional[list[list[dict[str, Any]]]]
) -> bool:
    if any(
        name in household and not _is_absent(name, household[name])
        for name in _COUNTY_INPUTS
    ):
        return True
    return any(axis["name"] in _COUNTY_INPUTS for group in axes or [] for axis in group)


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
        "household, year, reform, extra_variables, axes, spm."
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
        "marital_units": {"marital_unit_0": _group(marital_unit)},
        "families": {"family_0": _group(family)},
        "spm_units": {"spm_unit_0": _group(spm_unit)},
        "tax_units": {"tax_unit_0": _group(tax_unit)},
        "households": {"household_0": _group(household)},
    }
    if axes is not None:
        situation["axes"] = axes
    return situation


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
        "axes",
        "spm",
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
    axes: Optional[list[Any]] = None,
    spm: Optional[SPMSelection] = None,
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
        axes: Optional household-calculator axes. Pass either the lower-level
            ``[[{"name": ..., "min": ..., "max": ..., "count": ...}]]``
            shape or a flat list of axis dictionaries. Missing ``period``
            values default to ``year``. When axes are present, result values
            are lists ordered by the axis grid instead of scalars.
        spm: SPMSelection or mapping selecting a scenario and geography from
            the bundle's independently pinned artifact. When it chooses no
            ``geography_kind``, a household with ``county_fips`` is measured
            in its county's Census SPM estimation area, and a household that
            names no county (no county input, only missing values, or
            ``county``/``county_str`` of ``"UNKNOWN"``) is measured
            nationally, with no geographic
            adjustment, in its thresholds and in the capped SPM housing
            subsidy; ``provenance["spm_geography_source"]`` is then
            ``"national_fallback"`` (otherwise ``"default"``, or
            ``"selection"`` when you chose the geography). A household that
            names its county only as ``county`` or ``county_str`` keeps county
            measurement and raises ``SPM_GEOGRAPHY_REQUIRED``, asking for
            ``county_fips``. A ``geography_kind`` you choose is used as given,
            so an explicit county selection without ``county_fips`` also
            raises ``SPM_GEOGRAPHY_REQUIRED``. Under that selection only the
            results that use the measurement need the county: SPM thresholds
            and poverty, and, for a unit allocated housing assistance, the
            capped SPM subsidy (``spm_unit_capped_housing_subsidy``) and the
            SPM resources built on it (``spm_unit_benefits``,
            ``spm_unit_net_income``, ``spm_unit_oecd_equiv_net_income``,
            ``spm_unit_income_decile``). Ordinary resource outputs use the
            actual housing assistance amount and never need one.
            Formula-owned SPM amounts and measurement counts cannot be
            supplied as inputs/axes.

    Returns:
        :class:`HouseholdResult` with dot-accessible per-entity
        variables. Singleton entities (``tax_unit``, ``household``, ...)
        return :class:`EntityResult`; ``person`` returns a list of them.
        ``provenance`` holds the resolved ``spm_config``, the
        ``spm_geography_source`` and the SPM calculation receipt (``spm``).

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
    from spm_calculator.policyengine_adapter import validate_policyengine_inputs

    validate_policyengine_inputs(
        {"person": people, **{name: [value] for name, value in entities.items()}}
    )

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
    normalized_axes = normalize_axes(axes=axes, year=year, model_version=us_latest)
    if normalized_axes is not None:
        validate_policyengine_inputs(
            {
                "axes": [
                    {axis["name"]: None} for group in normalized_axes for axis in group
                ]
            }
        )
    axes_active = normalized_axes is not None
    spm_config, spm_geography_source = resolve_household_spm_selection(
        spm,
        household_names_county=_names_county(entities["household"], normalized_axes),
    )

    simulation = Simulation(
        situation=_build_situation(
            people=people,
            marital_unit=entities["marital_unit"],
            family=entities["family"],
            spm_unit=entities["spm_unit"],
            tax_unit=entities["tax_unit"],
            household=entities["household"],
            year=year,
            axes=normalized_axes,
        ),
        reform=reform_dict,
        spm=spm_config,
    )

    result = HouseholdResult()
    for entity, columns in output_columns.items():
        raw = {
            variable: list(
                simulation.calculate(
                    variable,
                    period=year,
                    map_to=entity,
                    decode_enums=True,
                )
            )
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
    result["provenance"] = {
        "spm_config": dict(simulation.spm_config),
        "spm_geography_source": spm_geography_source,
        "spm": calculation_provenance(simulation),
    }
    return result
