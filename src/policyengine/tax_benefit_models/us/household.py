"""Single-household calculation for the US model.

``calculate_household`` is the one-call entry point for the household
calculator journey: pass the people plus any per-entity overrides plus
an optional reform, get back a dot-accessible result.

.. code-block:: python

    import policyengine as pe

    # Single parent with one child in New York, $45k wages.
    inputs = dict(
        people=[
            {"age": 32, "employment_income": 45000, "is_tax_unit_head": True},
            {"age": 6, "is_tax_unit_dependent": True},
        ],
        # A marital unit is one unmarried person or one married couple.
        marital_unit=[{"members": [0]}, {"members": [1]}],
        tax_unit={"filing_status": "HEAD_OF_HOUSEHOLD"},
        household={"state_code": "NY", "county_fips": "36061"},
        year=2026,
    )
    result = pe.us.calculate_household(
        **inputs, extra_variables=["adjusted_gross_income"]
    )
    print(result.tax_unit.income_tax)
    print(result.tax_unit.ctc, result.tax_unit.eitc)
    print(result.household.household_net_income)
    print(result.marital_unit[0])  # one result per marital unit
    # Reform: zero out SNAP.
    reformed = pe.us.calculate_household(
        **inputs, reform={"gov.usda.snap.income.deductions.earned_income": 0}
    )
"""

from __future__ import annotations

import operator
from collections.abc import Mapping, Sequence
from typing import Any, Optional, Union

import numpy as np

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
from .spm import SPMSelection, calculation_provenance, resolve_spm_selection

_GROUP_ENTITIES = ("marital_unit", "family", "spm_unit", "tax_unit", "household")
# Group entities a caller may split into several groups. The household stays
# one group: ``calculate_household`` computes a single household.
_SPLITTABLE_GROUP_ENTITIES = ("marital_unit", "family", "spm_unit", "tax_unit")
_GROUP_PLURALS = {
    "marital_unit": "marital_units",
    "family": "families",
    "spm_unit": "spm_units",
    "tax_unit": "tax_units",
    "household": "households",
}

GroupInput = Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]
"""One group's inputs, or a list of groups that each name their ``members``."""


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


def _person_index(value: Any, *, location: str, people_count: int) -> int:
    # NumPy booleans support operator.index (np.True_ gives 1), so they need
    # their own check, like Python's.
    if isinstance(value, (bool, np.bool_)):
        index = None
    else:
        try:
            index = operator.index(value)
        except TypeError:
            index = None
    if index is None:
        raise ValueError(
            f"{location} must hold integer indexes into people; got {value!r}."
        )
    if not 0 <= index < people_count:
        raise ValueError(
            f"{location} names person {index}, but people has "
            f"{people_count} entries (indexes 0 to {people_count - 1})."
        )
    return index


def _resolve_groups(
    entity: str,
    spec: Optional[GroupInput],
    *,
    people_count: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Return one entity's groups, each with ``members`` as person indexes.

    A mapping (or ``None``) is one group holding every person; the flag in the
    return value is then ``False``. A list holds several groups, each naming
    its ``members``; every person must belong to exactly one of them.
    """
    everyone = list(range(people_count))
    if spec is None:
        return [{"members": everyone}], False
    if isinstance(spec, Mapping):
        if "members" in spec:
            raise ValueError(
                f"{entity} is a single group holding every person, so it "
                "takes no 'members'. To split people into several groups, "
                f"pass a list: {entity}=[{{'members': [0, 1]}}, "
                "{'members': [2]}]."
            )
        return [{"members": everyone, **spec}], False
    if entity not in _SPLITTABLE_GROUP_ENTITIES:
        raise ValueError(
            f"{entity} takes one mapping of inputs: calculate_household "
            "computes a single household."
        )
    if isinstance(spec, (str, bytes)) or not isinstance(spec, Sequence):
        raise ValueError(
            f"{entity} must be a mapping of inputs or a list of groups; "
            f"got {type(spec).__name__}."
        )
    groups = list(spec)
    if not groups:
        raise ValueError(f"{entity} must list at least one group.")

    owner: dict[int, int] = {}
    resolved: list[dict[str, Any]] = []
    for position, group in enumerate(groups):
        location = f"{entity}[{position}]"
        if not isinstance(group, Mapping):
            raise ValueError(
                f"{location} must be a mapping with 'members' and the group's "
                f"inputs; got {type(group).__name__}."
            )
        if "members" not in group:
            raise ValueError(
                f"{location} must include 'members', a list of indexes into people."
            )
        members = group["members"]
        if isinstance(members, np.ndarray) and members.ndim == 1:
            members = members.tolist()
        if isinstance(
            members, (str, bytes, bytearray, memoryview, Mapping)
        ) or not isinstance(members, Sequence):
            raise ValueError(
                f"{location}['members'] must be a list of indexes into "
                f"people; got {type(members).__name__}."
            )
        if not members:
            raise ValueError(
                f"{location}['members'] is empty; each group holds at least one person."
            )
        indexes = []
        for value in members:
            index = _person_index(
                value,
                location=f"{location}['members']",
                people_count=people_count,
            )
            if index in owner:
                where = (
                    "twice"
                    if owner[index] == position
                    else f"in both {entity}[{owner[index]}] and {location}"
                )
                raise ValueError(
                    f"people[{index}] appears {where}; each person belongs to "
                    f"exactly one {entity}."
                )
            owner[index] = position
            indexes.append(index)
        resolved.append({**group, "members": indexes})

    unassigned = [index for index in everyone if index not in owner]
    if unassigned:
        listed = ", ".join(f"people[{index}]" for index in unassigned)
        raise ValueError(
            f"{listed} belong to no {entity}; each person belongs to exactly "
            f"one {entity}."
        )
    return resolved, True


def _group_inputs(group: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in group.items() if key != "members"}


def _build_situation(
    *,
    people: list[Mapping[str, Any]],
    groups: Mapping[str, list[dict[str, Any]]],
    year: int,
    axes: Optional[list[Any]] = None,
) -> dict[str, Any]:
    year_str = str(year)

    def _periodise(spec: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        return {key: {year_str: value} for key, value in spec.items() if key != "id"}

    person_ids = [f"person_{i}" for i in range(len(people))]
    persons = {pid: _periodise(person) for pid, person in zip(person_ids, people)}

    def _group(spec: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "members": [person_ids[index] for index in spec["members"]],
            **_periodise(_group_inputs(spec)),
        }

    situation: dict[str, Any] = {"people": persons}
    for entity in _GROUP_ENTITIES:
        situation[_GROUP_PLURALS[entity]] = {
            f"{entity}_{position}": _group(spec)
            for position, spec in enumerate(groups[entity])
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
    marital_unit: Optional[GroupInput] = None,
    family: Optional[GroupInput] = None,
    spm_unit: Optional[GroupInput] = None,
    tax_unit: Optional[GroupInput] = None,
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
            ``household={"state_code": "NY"}``). A mapping applies to one
            group holding every person. ``marital_unit``, ``family``,
            ``spm_unit`` and ``tax_unit`` also accept a list of groups, each a
            mapping with ``members`` (indexes into ``people``) plus that
            group's inputs; each person must belong to exactly one group of
            the entity. policyengine-us defines a marital unit as one
            unmarried person or one married couple. Medicaid's optional
            pathway for seniors and people with disabilities applies the
            couple income limit to a marital unit of exactly two people, and
            SSI treats two aged, blind or disabled heads or spouses in one
            marital unit as a couple and then adds up income across the whole
            unit. So a household with children or other adults needs the list
            form, e.g. ``marital_unit=[{"members": [0, 1]}, {"members": [2]}]``
            for a married couple and their child.
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
            the bundle's independently pinned artifact. Geography is demanded
            only by the results that actually use the measurement. SPM
            measurement itself — thresholds, the geographic factor and SPM
            poverty — always requires household county_fips or an explicit
            metro/national selection, and so do the default outputs, which
            include SPM poverty. The ordinary resource outputs take the
            household's housing assistance amount rather than the capped SPM
            subsidy, so they compute on state alone whether or not the unit is
            allocated assistance. The country's cap
            (``spm_unit_capped_housing_subsidy``) is what consults the
            canonical housing portion, and only for units allocated
            assistance, so for an assisted unit without a geography the cap
            and everything downstream of it — ``spm_unit_benefits``,
            ``spm_unit_net_income`` and in turn
            ``spm_unit_oecd_equiv_net_income`` and
            ``spm_unit_income_decile`` — raise ``SPM_GEOGRAPHY_REQUIRED``;
            a unit allocated none has a capped subsidy of zero by
            construction.
            Formula-owned SPM amounts and measurement counts cannot be
            supplied as inputs/axes.

    Returns:
        :class:`HouseholdResult` with dot-accessible per-entity
        variables. An entity passed as a mapping (or omitted) returns one
        :class:`EntityResult`; an entity passed as a list of groups returns
        a list of them in the same order, and ``person`` returns one per
        person.

    Raises:
        ValueError: if any input dict uses an unknown variable name,
            if a variable is placed on the wrong entity (e.g.
            ``filing_status`` on ``people``), or if ``extra_variables``
            / ``reform`` names a variable or parameter path not defined
            on the US model. Raises if ``year`` is not an annual calendar
            year or if household input values are already periodized.
            Raises if a list of groups leaves a person out, names a
            person twice, or names an index outside ``people``.
    """
    if unexpected:
        _raise_unexpected_kwargs(unexpected)

    people = list(people)
    if not people:
        raise ValueError(
            "people must be a non-empty list. At minimum pass people=[{'age': <int>}]."
        )
    specs: dict[str, Optional[GroupInput]] = {
        "marital_unit": marital_unit,
        "family": family,
        "spm_unit": spm_unit,
        "tax_unit": tax_unit,
        "household": household,
    }
    groups: dict[str, list[dict[str, Any]]] = {}
    listed: dict[str, bool] = {}
    for name, spec in specs.items():
        groups[name], listed[name] = _resolve_groups(
            name, spec, people_count=len(people)
        )
    records = {
        name: [_group_inputs(group) for group in entity_groups]
        for name, entity_groups in groups.items()
    }
    listed_entities = frozenset(name for name, is_list in listed.items() if is_list)
    year = validate_annual_household_inputs(
        year=year,
        entities={"people": people, **records},
        listed_entities=listed_entities,
    )

    from policyengine_us import Simulation
    from spm_calculator.policyengine_adapter import validate_policyengine_inputs

    validate_policyengine_inputs({"person": people, **records})

    validate_household_input(
        model_version=us_latest,
        entities={"person": people, **records},
        listed_entities=listed_entities,
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
    spm_config = resolve_spm_selection(spm)

    simulation = Simulation(
        situation=_build_situation(
            people=people,
            groups=groups,
            year=year,
            axes=normalized_axes,
        ),
        reform=reform_dict,
        spm=spm_config,
    )

    result = HouseholdResult()
    for entity, columns in output_columns.items():
        values = {
            variable: [
                _safe_convert(value)
                for value in simulation.calculate(
                    variable,
                    period=year,
                    map_to=entity,
                    decode_enums=True,
                )
            ]
            for variable in columns
        }
        count = len(people) if entity == "person" else len(groups[entity])
        # Core lays each entity's instances out copy by copy across the axis
        # grid, so instance i of this entity sits at i, i + count, ...
        entity_results = [
            EntityResult(
                {
                    variable: values_for_entity(
                        values[variable],
                        entity_index=index,
                        entity_count=count,
                        axes_active=axes_active,
                    )
                    for variable in columns
                }
            )
            for index in range(count)
        ]
        if entity == "person" or listed[entity]:
            result[entity] = entity_results
        else:
            result[entity] = entity_results[0]
    result["provenance"] = {
        "spm_config": dict(simulation.spm_config),
        "spm": calculation_provenance(simulation),
    }
    return result
