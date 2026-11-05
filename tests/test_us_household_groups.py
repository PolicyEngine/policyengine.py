"""Several groups of one entity in ``pe.us.calculate_household`` (#738).

``marital_unit``, ``family``, ``spm_unit`` and ``tax_unit`` accept either one
mapping (one group holding every person) or a list of groups that each name
their ``members`` by index into ``people``.

Invariants checked here:

- Partition: a list of groups is accepted exactly when it assigns every person
  to one group, and the situation's memberships equal that partition.
- Backward compatibility: a mapping (or nothing) builds the same single group
  holding every person as before, under the same ids.
- Differential: list-form results equal a ``policyengine_us.Simulation``
  built by hand with the same groups, with and without axes.
- Semantics: with its own marital unit, a child's earnings leave its married
  parents' SSI unchanged, and a single parent faces the individual Medicaid
  income limit.

US cases select national SPM geography: they test the calculator interface
without claiming a local SPM area.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

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
            ([{"members": []}, {"members": [0, 1]}], r"marital_unit\[0\] must"),
            ([{"filing_status": "JOINT"}], r"marital_unit\[0\] must include"),
            ([{"members": "01"}], r"marital_unit\[0\] must include 'members'"),
            ([{"members": {0: 1}}], r"marital_unit\[0\] must include 'members'"),
            ([], r"marital_unit must list at least one group"),
            ([[0, 1]], r"marital_unit\[0\] must be a mapping"),
            ("01", r"marital_unit must be a mapping of inputs or a list"),
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
        if data.draw(st.booleans()):
            groups[position].pop(data.draw(st.integers(0, len(groups[position]) - 1)))
            groups = [members for members in groups if members]
            if not groups:
                groups = [[people_count]]  # every person dropped: out of range
        else:
            extra = data.draw(st.integers(0, people_count - 1))
            groups[position].append(extra)
        with pytest.raises(ValueError):
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


# --- Calculating --------------------------------------------------------------


COUPLE_AND_TEEN = dict(
    people=[{"age": 68}, {"age": 66}, {"age": 17, "employment_income": 6_000}],
    tax_unit={"filing_status": "JOINT"},
    household={"state_code": "CA"},
    year=YEAR,
    spm=NATIONAL,
)


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

    def test__group_input_on_wrong_entity__then_raises_with_entity_hint(self):
        with pytest.raises(ValueError, match="filing_status"):
            pe.us.calculate_household(
                **{
                    **COUPLE_AND_TEEN,
                    "marital_unit": [
                        {"members": [0, 1], "filing_status": "JOINT"},
                        {"members": [2]},
                    ],
                }
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

    def test__list_form__then_matches_direct_simulation(self):
        variables = {
            "person": [
                "ssi",
                "medicaid",
                "medicaid_optional_senior_or_disabled_income_limit",
            ],
            "marital_unit": ["marital_unit_id"],
            "tax_unit": ["income_tax", "eitc"],
            "spm_unit": ["snap", "spm_unit_net_income"],
            "household": ["household_net_income", "household_benefits"],
        }
        result = pe.us.calculate_household(
            **COUPLE_AND_TEEN,
            marital_unit=[{"members": [0, 1]}, {"members": [2]}],
            extra_variables=variables["person"],
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
            if entity == "person":
                actual = [person[name] for person in result.person]
            elif entity == "marital_unit":
                actual = [unit[name] for unit in result.marital_unit]
            else:
                actual = [result[entity][name]]
            assert actual == pytest.approx(expected), (entity, name)

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
