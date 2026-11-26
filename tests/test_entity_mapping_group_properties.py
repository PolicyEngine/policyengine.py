"""Properties of map_to_entity between two group entities.

Every case links each person to a household and to two group entities inside
it, ``tax_unit`` and ``spm_unit``. In the crossing cases the two are drawn
independently within each household, so one tax unit's members can sit in
several SPM units and the reverse. In the nested cases every tax unit sits
inside one SPM unit.

These tests use the module-level function on plain tables, so they need no
country model.
"""

from itertools import permutations

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from microdf import MicroDataFrame

from policyengine.core import map_to_entity

GROUPS = ("tax_unit", "spm_unit", "household")


def _build(people: list[tuple[int, int, int]], prefixed: bool, values: dict):
    """Build entity tables from (household, spm_unit, tax_unit) id triples.

    ``values`` maps a group entity to {group id: value}; groups without a value
    get 0. ``prefixed`` stores person links as ``person_<entity>_id`` instead of
    ``<entity>_id``, the two layouts map_to_entity accepts.
    """
    link = (lambda e: f"person_{e}_id") if prefixed else (lambda e: f"{e}_id")
    person = pd.DataFrame(
        {
            "person_id": range(len(people)),
            link("household"): [h for h, _, _ in people],
            link("spm_unit"): [s for _, s, _ in people],
            link("tax_unit"): [t for _, _, t in people],
            "person_weight": 1.0,
        }
    )
    data = {"person": MicroDataFrame(person, weights="person_weight")}
    for entity in GROUPS:
        ids = sorted(person[link(entity)].unique())
        table = pd.DataFrame(
            {
                f"{entity}_id": ids,
                f"{entity}_weight": 1.0,
                "value": [float(values.get(entity, {}).get(i, 0)) for i in ids],
            }
        )
        data[entity] = MicroDataFrame(table, weights=f"{entity}_weight")
    return data


@st.composite
def entity_data(draw, nested: bool):
    """Random households of 1-5 people with tax units and SPM units in them."""
    people = []
    for h in range(draw(st.integers(1, 4))):
        for _ in range(draw(st.integers(1, 5))):
            spm = draw(st.integers(0, 2))
            if nested:
                # Each tax unit id belongs to exactly one SPM unit.
                tax = spm * 3 + draw(st.integers(0, 2))
            else:
                tax = draw(st.integers(0, 2))
            people.append((h, h * 100 + spm, h * 100 + tax))
    values = {}
    for entity in GROUPS:
        index = {"household": 0, "spm_unit": 1, "tax_unit": 2}[entity]
        ids = sorted({p[index] for p in people})
        amounts = draw(
            st.lists(st.integers(-1_000, 100_000), min_size=len(ids), max_size=len(ids))
        )
        values[entity] = dict(zip(ids, amounts))
    return _build(people, draw(st.booleans()), values), values


def _mapped(data, source, target, how) -> pd.DataFrame:
    """Map the value column, as a plain (unweighted) DataFrame."""
    return pd.DataFrame(map_to_entity(data, source, target, columns=["value"], how=how))


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=False))
def test_divide_keeps_each_total(case):
    data, values = case
    for source, target in permutations(GROUPS, 2):
        mapped = _mapped(data, source, target, "divide")
        assert len(mapped) == len(data[target])
        assert mapped["value"].to_numpy().sum() == pytest.approx(
            sum(values[source].values())
        ), (source, target)


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=False))
def test_divide_matches_the_route_through_persons(case):
    """Group-to-group divide equals group->person divide, then person->group sum."""
    data, _ = case
    for source, target in permutations(GROUPS, 2):
        per_person = _mapped(data, source, "person", "divide")
        through_persons = pd.Series(
            map_to_entity(
                data,
                "person",
                target,
                values=per_person["value"].to_numpy(),
                how="sum",
            )
        )
        direct = _mapped(data, source, target, "divide")
        assert direct["value"].to_numpy() == pytest.approx(
            through_persons.to_numpy()
        ), (source, target)


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=True))
def test_sum_keeps_the_total_when_sources_nest_in_targets(case):
    data, values = case
    for source, target in [
        ("tax_unit", "spm_unit"),
        ("tax_unit", "household"),
        ("spm_unit", "household"),
    ]:
        mapped = _mapped(data, source, target, "sum")
        assert mapped["value"].to_numpy().sum() == pytest.approx(
            sum(values[source].values())
        ), (source, target)
        # When every source sits in one target, sum and divide agree.
        assert mapped["value"].to_numpy() == pytest.approx(
            _mapped(data, source, target, "divide")["value"].to_numpy()
        ), (source, target)


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=True))
def test_sum_from_a_containing_group_gives_each_member_group_its_value(case):
    """Mapping a group onto the smaller groups inside it repeats its value.

    This pins the current coarse-to-fine behaviour, which the UK
    household-to-benunit test checks only for one benunit per household.
    """
    data, values = case
    person = pd.DataFrame(data["person"])
    link = "person_tax_unit_id" if "person_tax_unit_id" in person else "tax_unit_id"
    spm_link = "person_spm_unit_id" if "person_spm_unit_id" in person else "spm_unit_id"
    spm_of_tax = person.groupby(link)[spm_link].first()
    mapped = _mapped(data, "spm_unit", "tax_unit", "sum")
    for tax_id, value in zip(mapped["tax_unit_id"], mapped["value"]):
        assert value == values["spm_unit"][spm_of_tax[tax_id]]


def test_divide_keeps_a_two_person_unit_whole_inside_one_household():
    """A $100 tax unit whose two members share a household maps to $100.

    Before the fix, divide split the value by the unit's two members but added
    it once per (tax unit, household) pair, so the household received $50.
    """
    data = _build(
        [(1, 10, 100), (1, 10, 100)],
        prefixed=False,
        values={"tax_unit": {100: 100}},
    )
    mapped = _mapped(data, "tax_unit", "household", "divide")
    assert mapped["value"].tolist() == [100.0]


def test_divide_splits_a_unit_across_targets_by_member_share():
    """Two of a tax unit's three members are in SPM unit 10, one in SPM unit 11."""
    data = _build(
        [(1, 10, 100), (1, 10, 100), (1, 11, 100)],
        prefixed=True,
        values={"tax_unit": {100: 300}},
    )
    mapped = _mapped(data, "tax_unit", "spm_unit", "divide")
    by_spm = dict(zip(mapped["spm_unit_id"], mapped["value"]))
    assert by_spm == pytest.approx({10: 200.0, 11: 100.0})
