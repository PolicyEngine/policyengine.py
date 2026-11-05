"""Several groups of one entity in ``pe.us.calculate_household`` (#738).

``marital_unit``, ``family``, ``spm_unit`` and ``tax_unit`` accept either one
mapping (one group holding every person) or a list of groups that each name
their ``members`` by index into ``people``.

Invariants checked here:

- Partition: a list of groups is accepted exactly when it assigns every person
  to one group, and the situation's memberships equal that partition.
- Backward compatibility: for mapping (or omitted) entities, the builder emits
  the same situation, key order included, as origin/main's builder before
  list form, whatever the inputs on each entity and with or without axes.
- Differential: list-form results equal a ``policyengine_us.Simulation``
  built by hand with the same groups, for every splittable entity, without
  axes, with one axis, and with perpendicular axes on a person variable and a
  group variable.
- Membership: ids passed as group inputs come back on each group and on each
  of its members.
- Semantics: with its own marital unit, a child's earnings leave its married
  parents' SSI unchanged, while one shared unit lowers it; a single parent
  faces the individual Medicaid income limit, and so does a couple sharing a
  unit with their child.

US cases select national SPM geography: they test the calculator interface
without claiming a local SPM area.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Optional

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from spm_calculator.errors import SPMInputError

import policyengine as pe
from policyengine.tax_benefit_models.common import EntityResult
from policyengine.tax_benefit_models.us.household import (
    _build_situation,
    _resolve_groups,
)
from policyengine.tax_benefit_models.us.spm import resolve_spm_selection

YEAR = 2026
NATIONAL = {"geography_kind": "national"}
GROUP_PLURALS = {
    "marital_unit": "marital_units",
    "family": "families",
    "spm_unit": "spm_units",
    "tax_unit": "tax_units",
    "household": "households",
}
SPLITTABLE = ["marital_unit", "family", "spm_unit", "tax_unit"]


def _direct_values(people, groups, variables, *, axes=None):
    """Run policyengine_us directly on a hand-written situation.

    ``groups`` maps each group entity to a list of member-index lists plus
    inputs, e.g. ``{"marital_unit": [([0, 1], {}), ([2], {})]}``. Entities not
    listed hold everyone in one group.
    """
    from policyengine_us import Simulation

    ids = [f"p{index}" for index in range(len(people))]
    situation = {
        "people": {
            pid: {key: {YEAR: value} for key, value in person.items()}
            for pid, person in zip(ids, people)
        }
    }
    for entity, plural in GROUP_PLURALS.items():
        specs = groups.get(entity, [(list(range(len(people))), {})])
        situation[plural] = {
            f"{entity}{position}": {
                "members": [ids[index] for index in members],
                **{key: {YEAR: value} for key, value in inputs.items()},
            }
            for position, (members, inputs) in enumerate(specs)
        }
    if axes is not None:
        situation["axes"] = axes
    simulation = Simulation(situation=situation, spm=resolve_spm_selection(NATIONAL))
    out = {}
    for entity, names in variables.items():
        for name in names:
            values = simulation.calculate(
                name, period=YEAR, map_to=entity, decode_enums=True
            )
            out[(entity, name)] = [
                float(value) if not isinstance(value, str) else value
                for value in values
            ]
    return out


def _result_values(result, entity, name):
    """One variable of a ``calculate_household`` result in core's layout.

    Each group gives one value, or an axis series under axes; core lays copy c
    of instance i out at ``c * count + i``.
    """
    section = result[entity]
    instances = section if isinstance(section, list) else [section]
    series = [instance[name] for instance in instances]
    if not isinstance(series[0], list):
        return series
    return [
        series[index][point]
        for point in range(len(series[0]))
        for index in range(len(instances))
    ]


def _list_kwargs(groups):
    """``calculate_household`` keyword arguments for ``_direct_values`` groups."""
    kwargs = {}
    for entity, specs in groups.items():
        if entity == "household":
            ((_, inputs),) = specs
            kwargs[entity] = dict(inputs)
        else:
            kwargs[entity] = [
                {"members": list(members), **inputs} for members, inputs in specs
            ]
    return kwargs


# --- Resolving groups ---------------------------------------------------------


class TestResolveGroups:
    def test__mapping__then_one_group_of_everyone(self):
        groups, listed = _resolve_groups(
            "tax_unit", {"filing_status": "JOINT"}, people_count=3
        )
        assert listed is False
        assert groups == [{"members": [0, 1, 2], "filing_status": "JOINT"}]

    def test__none__then_one_group_of_everyone(self):
        groups, listed = _resolve_groups("family", None, people_count=2)
        assert listed is False
        assert groups == [{"members": [0, 1]}]

    def test__list__then_members_and_inputs_kept_in_order(self):
        groups, listed = _resolve_groups(
            "tax_unit",
            [
                {"members": [2, 0], "filing_status": "JOINT"},
                {"members": (1,), "filing_status": "SINGLE"},
            ],
            people_count=3,
        )
        assert listed is True
        assert groups == [
            {"members": [2, 0], "filing_status": "JOINT"},
            {"members": [1], "filing_status": "SINGLE"},
        ]

    def test__numpy_integer_indexes__then_accepted(self):
        groups, _ = _resolve_groups(
            "marital_unit",
            [{"members": [np.int64(0)]}, {"members": [np.int32(1)]}],
            people_count=2,
        )
        assert groups == [{"members": [0]}, {"members": [1]}]

    def test__numpy_array_and_range_members__then_accepted_as_ints(self):
        groups, _ = _resolve_groups(
            "spm_unit",
            [{"members": np.array([2, 0])}, {"members": range(1, 2)}],
            people_count=3,
        )
        assert groups == [{"members": [2, 0]}, {"members": [1]}]
        assert all(type(index) is int for group in groups for index in group["members"])

    @pytest.mark.parametrize(
        ("spec", "match"),
        [
            ([{"members": [0]}], r"people\[1\] belong to no marital_unit"),
            ([{"members": [0, 0, 1]}], r"people\[0\] appears twice"),
            (
                [{"members": [0, 1]}, {"members": [1]}],
                r"people\[1\] appears in both marital_unit\[0\] and "
                r"marital_unit\[1\]",
            ),
            ([{"members": [0, 2]}], r"names person 2, but people has 2 entries"),
            ([{"members": [-1, 0, 1]}], r"names person -1"),
            ([{"members": [0.0, 1]}], r"integer indexes into people; got 0.0"),
            ([{"members": ["0", 1]}], r"integer indexes into people; got '0'"),
            ([{"members": [True, 0]}], r"integer indexes into people; got True"),
            (
                [{"members": [np.True_, 0]}],
                r"integer indexes into people; got np\.True_",
            ),
            (
                [{"members": np.array([True, False])}],
                r"integer indexes into people; got True",
            ),
            (
                [{"members": []}, {"members": [0, 1]}],
                r"marital_unit\[0\]\['members'\] is empty",
            ),
            (
                [{"filing_status": "JOINT"}],
                r"marital_unit\[0\] must include 'members'",
            ),
            ([{"members": "01"}], r"marital_unit\[0\]\['members'\] .* got str"),
            ([{"members": {0: 1}}], r"marital_unit\[0\]\['members'\] .* got dict"),
            ([{"members": b"\x00\x01"}], r"\['members'\] .* got bytes"),
            (
                [{"members": bytearray(b"\x00\x01")}],
                r"\['members'\] .* got bytearray",
            ),
            (
                [{"members": memoryview(b"\x00\x01")}],
                r"\['members'\] .* got memoryview",
            ),
            ([{"members": np.array([[0, 1]])}], r"\['members'\] .* got ndarray"),
            ([{"members": 0}], r"marital_unit\[0\]\['members'\] .* got int"),
            ([], r"marital_unit must list at least one group"),
            ([[0, 1]], r"marital_unit\[0\] must be a mapping"),
            ("01", r"marital_unit must be a mapping of inputs or a list"),
            (
                (group for group in [{"members": [0, 1]}]),
                r"marital_unit must be a mapping of inputs or a list of groups; "
                r"got generator",
            ),
            ({"members": [0, 1]}, r"takes no 'members'"),
        ],
    )
    def test__invalid_groups__then_raises(self, spec, match):
        with pytest.raises(ValueError, match=match):
            _resolve_groups("marital_unit", spec, people_count=2)

    def test__household_list__then_raises(self):
        with pytest.raises(ValueError, match="computes a single household"):
            _resolve_groups("household", [{"members": [0]}], people_count=1)


@st.composite
def _partitions(draw):
    """People count, plus groups that partition them in a random order."""
    people_count = draw(st.integers(min_value=1, max_value=8))
    labels = draw(
        st.lists(
            st.integers(min_value=0, max_value=people_count - 1),
            min_size=people_count,
            max_size=people_count,
        )
    )
    blocks: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        blocks.setdefault(label, []).append(index)
    groups = [draw(st.permutations(members)) for members in blocks.values()]
    return people_count, draw(st.permutations(groups))


class TestPartitionProperties:
    @settings(max_examples=200, deadline=None)
    @given(case=_partitions(), entity=st.sampled_from(SPLITTABLE))
    def test__any_partition__then_memberships_equal_it(self, case, entity):
        people_count, partition = case
        spec = [{"members": list(members)} for members in partition]
        groups = {
            name: _resolve_groups(name, None, people_count=people_count)[0]
            for name in GROUP_PLURALS
        }
        groups[entity], listed = _resolve_groups(
            entity, spec, people_count=people_count
        )
        assert listed is True
        situation = _build_situation(
            people=[{"age": 30}] * people_count, groups=groups, year=YEAR
        )
        built = list(situation[GROUP_PLURALS[entity]].values())
        assert [group["members"] for group in built] == [
            [f"person_{index}" for index in members] for members in partition
        ]
        everyone = sorted(pid for group in built for pid in group["members"])
        assert everyone == sorted(f"person_{i}" for i in range(people_count))

    @settings(max_examples=200, deadline=None)
    @given(case=_partitions(), data=st.data())
    def test__dropped_or_repeated_person__then_raises(self, case, data):
        people_count, partition = case
        groups = [list(members) for members in partition]
        position = data.draw(st.integers(0, len(groups) - 1))
        # Dropping the only person leaves no group at all, which is the
        # empty-list error that TestResolveGroups covers.
        if people_count > 1 and data.draw(st.booleans()):
            members = groups[position]
            dropped = members.pop(data.draw(st.integers(0, len(members) - 1)))
            groups = [members for members in groups if members]
            match = rf"people\[{dropped}\] belong to no tax_unit"
        else:
            extra = data.draw(st.integers(0, people_count - 1))
            groups[position].append(extra)
            match = rf"people\[{extra}\] appears"
        with pytest.raises(ValueError, match=match):
            _resolve_groups(
                "tax_unit",
                [{"members": members} for members in groups],
                people_count=people_count,
            )

    @settings(max_examples=100, deadline=None)
    @given(
        people_count=st.integers(min_value=1, max_value=6),
        state=st.sampled_from(["CA", "NY", "TX"]),
    )
    def test__mapping_form__then_builds_the_single_group_structure(
        self, people_count, state
    ):
        groups = {
            name: _resolve_groups(
                name,
                {"state_code": state} if name == "household" else None,
                people_count=people_count,
            )[0]
            for name in GROUP_PLURALS
        }
        situation = _build_situation(
            people=[{"age": 40}] * people_count, groups=groups, year=YEAR
        )
        everyone = [f"person_{i}" for i in range(people_count)]
        assert situation == {
            "people": {pid: {"age": {str(YEAR): 40}} for pid in everyone},
            "marital_units": {"marital_unit_0": {"members": everyone}},
            "families": {"family_0": {"members": everyone}},
            "spm_units": {"spm_unit_0": {"members": everyone}},
            "tax_units": {"tax_unit_0": {"members": everyone}},
            "households": {
                "household_0": {
                    "members": everyone,
                    "state_code": {str(YEAR): state},
                }
            },
        }


# --- Backward compatibility with the builder before list form ----------------


def _origin_main_build_situation(
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
    """``_build_situation`` as origin/main had it at 286fce481, verbatim."""
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


_RECORDS = st.dictionaries(
    st.sampled_from(["id", "age", "employment_income", "filing_status", "x"]),
    st.one_of(
        st.integers(-3, 3),
        st.booleans(),
        st.sampled_from(["JOINT", "CA"]),
        st.floats(allow_nan=False, allow_infinity=False, width=32),
    ),
    max_size=4,
)


class TestBackwardCompatibility:
    @settings(max_examples=300, deadline=None)
    @given(
        people=st.lists(_RECORDS, min_size=1, max_size=6),
        specs=st.fixed_dictionaries(
            {name: st.one_of(st.none(), _RECORDS) for name in GROUP_PLURALS}
        ),
        axes=st.one_of(
            st.none(),
            st.just(
                [
                    [
                        {
                            "name": "employment_income",
                            "min": 0,
                            "max": 10,
                            "count": 2,
                            "period": YEAR,
                        }
                    ]
                ]
            ),
        ),
    )
    def test__mapping_form__then_same_situation_as_origin_main(
        self, people, specs, axes
    ):
        groups = {
            name: _resolve_groups(name, spec, people_count=len(people))[0]
            for name, spec in specs.items()
        }
        built = _build_situation(people=people, groups=groups, year=YEAR, axes=axes)
        before = _origin_main_build_situation(
            people=people,
            year=YEAR,
            axes=axes,
            **{name: dict(spec or {}) for name, spec in specs.items()},
        )
        # Compare serialized forms, so key order has to match too.
        assert json.dumps(built) == json.dumps(before)


# --- Calculating --------------------------------------------------------------


COUPLE_AND_TEEN = dict(
    people=[{"age": 68}, {"age": 66}, {"age": 17, "employment_income": 6_000}],
    tax_unit={"filing_status": "JOINT"},
    household={"state_code": "CA"},
    year=YEAR,
    spm=NATIONAL,
)

# A parent and child, plus a grandparent who forms their own family, SPM unit
# and tax unit.
THREE_GENERATIONS_PEOPLE = [
    {"age": 34, "employment_income": 18_000},
    {"age": 9},
    {"age": 70, "social_security_retirement": 14_000},
]
THREE_GENERATIONS_GROUPS = {
    "marital_unit": [([0], {}), ([1], {}), ([2], {})],
    "family": [([0, 1], {}), ([2], {})],
    "spm_unit": [([0, 1], {}), ([2], {})],
    "tax_unit": [
        ([0, 1], {"filing_status": "HEAD_OF_HOUSEHOLD"}),
        ([2], {"filing_status": "SINGLE"}),
    ],
    "household": [([0, 1, 2], {"state_code": "PA"})],
}
THREE_GENERATIONS_VARIABLES = {
    "person": [
        "employment_income",
        "medicaid",
        "ssi",
        "ssi_claim_is_joint",
        "ssi_marital_earned_income",
    ],
    "family": ["is_married"],
    "spm_unit": [
        "spm_unit_pre_subsidy_childcare_expenses",
        "spm_unit_size",
        "snap",
        "spm_unit_net_income",
    ],
    "tax_unit": ["tax_unit_size", "income_tax", "eitc"],
    "household": ["household_size", "household_net_income"],
}
EARNINGS_AXIS = {
    "name": "employment_income",
    "min": 0,
    "max": 50_000,
    "count": 3,
    "period": YEAR,
}
CHILDCARE_AXIS = {
    "name": "spm_unit_pre_subsidy_childcare_expenses",
    "min": 0,
    "max": 8_000,
    "count": 2,
    "period": YEAR,
}


class TestCalculateWithGroups:
    def test__invalid_groups__then_raises_before_calculation(self):
        with pytest.raises(ValueError, match=r"people\[2\] belong to no"):
            pe.us.calculate_household(
                **{**COUPLE_AND_TEEN, "marital_unit": [{"members": [0, 1]}]}
            )

    def test__empty_people__then_raises(self):
        with pytest.raises(ValueError, match="people must be a non-empty list"):
            pe.us.calculate_household(
                people=[], marital_unit=[{"members": [0]}], spm=NATIONAL
            )

    def test__group_input_on_wrong_entity__then_names_the_group(self):
        with pytest.raises(ValueError) as caught:
            pe.us.calculate_household(
                **{
                    **COUPLE_AND_TEEN,
                    "marital_unit": [
                        {"members": [0, 1], "filing_status": "JOINT"},
                        {"members": [2]},
                    ],
                }
            )
        message = str(caught.value)
        assert "'filing_status' was given on marital_unit[0]" in message
        assert "pass tax_unit={'filing_status': <value>}" in message

    def test__input_belonging_on_a_listed_entity__then_hint_names_a_group(self):
        with pytest.raises(ValueError) as caught:
            pe.us.calculate_household(
                **{
                    **COUPLE_AND_TEEN,
                    "marital_unit": [
                        {"members": [0, 1], "filing_status": "JOINT"},
                        {"members": [2]},
                    ],
                    "tax_unit": [{"members": [0, 1, 2]}],
                }
            )
        assert (
            "add 'filing_status': <value> to the tax_unit group it applies to"
            in str(caught.value)
        )

    def test__periodized_group_input__then_names_the_group(self):
        with pytest.raises(ValueError, match=r"tax_unit\[1\]\.filing_status"):
            pe.us.calculate_household(
                **{
                    **COUPLE_AND_TEEN,
                    "tax_unit": [
                        {"members": [0, 1], "filing_status": "JOINT"},
                        {"members": [2], "filing_status": {"2026": "SINGLE"}},
                    ],
                }
            )

    def test__periodized_input_in_one_group_list__then_names_its_position(self):
        with pytest.raises(ValueError, match=r"tax_unit\[0\]\.filing_status"):
            pe.us.calculate_household(
                **{
                    **COUPLE_AND_TEEN,
                    "tax_unit": [
                        {"members": [0, 1, 2], "filing_status": {"2026": "JOINT"}}
                    ],
                }
            )

    def test__list_form__then_list_of_results_and_singletons_elsewhere(self):
        result = pe.us.calculate_household(
            **COUPLE_AND_TEEN,
            marital_unit=[{"members": [0, 1]}, {"members": [2]}],
        )
        assert isinstance(result.marital_unit, list)
        assert len(result.marital_unit) == 2
        assert all(isinstance(unit, EntityResult) for unit in result.marital_unit)
        assert isinstance(result.tax_unit, EntityResult)
        assert isinstance(result.household, EntityResult)
        as_dict = result.to_dict()
        assert isinstance(as_dict["marital_unit"], list)
        assert set(as_dict["marital_unit"][0]) == set(result.marital_unit[0])

    def test__marital_unit_list__then_matches_direct_simulation(self):
        variables = {
            "person": [
                "ssi",
                "ssi_claim_is_joint",
                "ssi_marital_earned_income",
                "medicaid",
                "medicaid_optional_senior_or_disabled_income_limit",
            ],
            "tax_unit": ["tax_unit_size", "income_tax", "eitc"],
            "spm_unit": ["spm_unit_size", "snap", "spm_unit_net_income"],
            "household": ["household_net_income", "household_benefits"],
        }
        result = pe.us.calculate_household(
            **COUPLE_AND_TEEN,
            marital_unit=[{"members": [0, 1]}, {"members": [2]}],
            extra_variables=[
                *variables["person"],
                "tax_unit_size",
                "spm_unit_size",
            ],
        )
        direct = _direct_values(
            COUPLE_AND_TEEN["people"],
            {
                "marital_unit": [([0, 1], {}), ([2], {})],
                "tax_unit": [([0, 1, 2], {"filing_status": "JOINT"})],
                "household": [([0, 1, 2], {"state_code": "CA"})],
            },
            variables,
        )
        for (entity, name), expected in direct.items():
            actual = (
                [person[name] for person in result.person]
                if entity == "person"
                else _result_values(result, entity, name)
            )
            assert actual == pytest.approx(expected), (entity, name)

    @pytest.mark.parametrize(
        "axes",
        [None, [[EARNINGS_AXIS]], [[EARNINGS_AXIS], [CHILDCARE_AXIS]]],
        ids=["no_axes", "one_axis", "perpendicular_axes"],
    )
    def test__every_entity_as_a_list__then_matches_direct_simulation(self, axes):
        variables = THREE_GENERATIONS_VARIABLES
        # Default outputs among these come back once either way.
        extra = sorted({name for names in variables.values() for name in names})
        result = pe.us.calculate_household(
            people=THREE_GENERATIONS_PEOPLE,
            **_list_kwargs(THREE_GENERATIONS_GROUPS),
            year=YEAR,
            spm=NATIONAL,
            axes=axes,
            extra_variables=extra,
        )
        direct = _direct_values(
            THREE_GENERATIONS_PEOPLE,
            THREE_GENERATIONS_GROUPS,
            variables,
            axes=axes,
        )
        for (entity, name), expected in direct.items():
            assert _result_values(result, entity, name) == pytest.approx(expected), (
                entity,
                name,
            )
        points = 1 if axes is None else 3 * (2 if len(axes) == 2 else 1)
        assert len(direct[("person", "employment_income")]) == 3 * points
        assert [len(unit) for unit in (result.family, result.spm_unit)] == [2, 2]
        assert [unit.tax_unit_size for unit in result.tax_unit] == (
            [2, 1] if axes is None else [[2] * points, [1] * points]
        )

    def test__ids_passed_as_group_inputs__then_on_each_group_and_member(self):
        result = pe.us.calculate_household(
            people=[{"age": 40}, {"age": 38}, {"age": 12}, {"age": 19}],
            marital_unit=[
                {"members": [0, 1], "marital_unit_id": 7},
                {"members": [2], "marital_unit_id": 8},
                {"members": [3], "marital_unit_id": 9},
            ],
            family=[
                {"members": [0, 1, 2], "family_id": 4},
                {"members": [3], "family_id": 5},
            ],
            spm_unit=[
                {"members": [0, 1, 2], "spm_unit_id": 2},
                {"members": [3], "spm_unit_id": 3},
            ],
            tax_unit=[
                {"members": [0, 1, 2], "tax_unit_id": 1, "filing_status": "JOINT"},
                {"members": [3], "tax_unit_id": 6, "filing_status": "SINGLE"},
            ],
            household={"state_code": "OH"},
            year=YEAR,
            spm=NATIONAL,
        )
        members = {
            "marital_unit": [7, 7, 8, 9],
            "family": [4, 4, 4, 5],
            "spm_unit": [2, 2, 2, 3],
            "tax_unit": [1, 1, 1, 6],
        }
        for entity, ids in members.items():
            variable = f"{entity}_id"
            assert [person[variable] for person in result.person] == ids
            assert [group[variable] for group in result[entity]] == list(
                dict.fromkeys(ids)
            )

    def test__spm_unit_of_children__then_composition_error(self):
        with pytest.raises(SPMInputError) as caught:
            pe.us.calculate_household(
                people=[{"age": 40, "employment_income": 20_000}, {"age": 13}],
                marital_unit=[{"members": [0]}, {"members": [1]}],
                spm_unit=[{"members": [0]}, {"members": [1]}],
                household={"state_code": "TX"},
                year=YEAR,
                spm=NATIONAL,
            )
        assert caught.value.code == "SPM_COMPOSITION_REQUIRED"

    def test__tax_unit_of_children__then_it_has_no_head(self):
        result = pe.us.calculate_household(
            people=[{"age": 40, "employment_income": 20_000}, {"age": 13}],
            marital_unit=[{"members": [0]}, {"members": [1]}],
            tax_unit=[
                {"members": [0], "filing_status": "SINGLE"},
                {"members": [1], "filing_status": "SINGLE"},
            ],
            household={"state_code": "TX"},
            year=YEAR,
            spm=NATIONAL,
            extra_variables=["is_tax_unit_head"],
        )
        assert [person.is_tax_unit_head for person in result.person] == [1, 0]

    def test__own_marital_unit__then_child_earnings_leave_parents_ssi(self):
        def adult_ssi(child_earnings, marital_unit):
            people = [
                {"age": 68},
                {"age": 66},
                {"age": 17, "employment_income": child_earnings},
            ]
            result = pe.us.calculate_household(
                **{**COUPLE_AND_TEEN, "people": people},
                marital_unit=marital_unit,
                extra_variables=["ssi"],
            )
            return [person.ssi for person in result.person[:2]]

        own_units = [{"members": [0, 1]}, {"members": [2]}]
        with_earnings = adult_ssi(6_000, own_units)
        assert with_earnings[0] > 0
        assert with_earnings == adult_ssi(0, own_units)
        # One marital unit for all three adds the child's earnings to the
        # couple's income, as the docs warn.
        shared = [{"members": [0, 1, 2]}]
        assert sum(adult_ssi(6_000, shared)) < sum(adult_ssi(0, shared))

    def test__single_parent_own_unit__then_individual_medicaid_limit(self):
        parent = {"age": 63, "is_blind": True, "social_security_retirement": 12_000}
        variable = "medicaid_optional_senior_or_disabled_income_limit"
        common = dict(household={"state_code": "MI"}, year=YEAR, spm=NATIONAL)
        with_child = pe.us.calculate_household(
            people=[parent, {"age": 13}],
            marital_unit=[{"members": [0]}, {"members": [1]}],
            tax_unit={"filing_status": "HEAD_OF_HOUSEHOLD"},
            extra_variables=[variable],
            **common,
        )
        alone = pe.us.calculate_household(
            people=[parent],
            tax_unit={"filing_status": "SINGLE"},
            extra_variables=[variable],
            **common,
        )
        assert with_child.person[0][variable] > 0
        assert with_child.person[0][variable] == alone.person[0][variable]

    def test__couple_sharing_a_unit_with_their_child__then_individual_limit(self):
        variable = "medicaid_optional_senior_or_disabled_income_limit"

        def parent_limits(marital_unit):
            result = pe.us.calculate_household(
                **{**COUPLE_AND_TEEN, "household": {"state_code": "MI"}},
                marital_unit=marital_unit,
                extra_variables=[variable],
            )
            return [person[variable] for person in result.person[:2]]

        alone = pe.us.calculate_household(
            people=[{"age": 68}],
            tax_unit={"filing_status": "SINGLE"},
            household={"state_code": "MI"},
            year=YEAR,
            spm=NATIONAL,
            extra_variables=[variable],
        ).person[0][variable]
        couple = parent_limits([{"members": [0, 1]}, {"members": [2]}])
        assert couple[0] > alone > 0
        assert parent_limits([{"members": [0, 1, 2]}]) == [alone, alone]

    def test__list_form_with_axes__then_each_group_gets_its_own_series(self):
        people = [
            {"age": 40, "employment_income": 0},
            {"age": 20, "employment_income": 15_000},
        ]
        axes = [{"name": "employment_income", "min": 0, "max": 60_000, "count": 4}]
        result = pe.us.calculate_household(
            people=people,
            marital_unit=[{"members": [0]}, {"members": [1]}],
            tax_unit=[
                {"members": [0], "filing_status": "SINGLE"},
                {"members": [1], "filing_status": "SINGLE"},
            ],
            household={"state_code": "TX"},
            year=YEAR,
            spm=NATIONAL,
            axes=axes,
        )
        direct = _direct_values(
            people,
            {
                "marital_unit": [([0], {}), ([1], {})],
                "tax_unit": [
                    ([0], {"filing_status": "SINGLE"}),
                    ([1], {"filing_status": "SINGLE"}),
                ],
                "household": [([0, 1], {"state_code": "TX"})],
            },
            {"tax_unit": ["income_tax"], "person": ["employment_income"]},
            axes=[[{**axes[0], "period": YEAR}]],
        )
        income_tax = direct[("tax_unit", "income_tax")]
        assert [unit.income_tax for unit in result.tax_unit] == [
            pytest.approx(income_tax[0::2]),
            pytest.approx(income_tax[1::2]),
        ]
        assert result.person[0].employment_income == [0, 20_000, 40_000, 60_000]
        assert result.person[1].employment_income == [15_000] * 4
        parent_tax, child_tax = (unit.income_tax for unit in result.tax_unit)
        assert all(a <= b for a, b in zip(parent_tax, parent_tax[1:]))
        assert parent_tax[-1] > parent_tax[0]
        assert child_tax == [child_tax[0]] * 4
