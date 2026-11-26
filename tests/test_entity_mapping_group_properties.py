"""Properties of map_to_entity between two group entities.

The random cases link each person to a household and to two group entities
inside it, ``tax_unit`` and ``spm_unit``. In the crossing cases the two are
drawn independently within each household, so one tax unit's members can sit
in several SPM units and the reverse. In the nested cases every tax unit sits
inside one SPM unit. Each random group table may also hold one group with no
members, every random table lists its rows in a shuffled order, and each
household draws a weight that its people and groups share. Every group carries
two value columns, ``value`` and ``other``.

These tests call the module-level function on plain tables, so they run
without a country model under ``pytest --noconftest``.
"""

from collections import Counter, namedtuple
from itertools import permutations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from microdf import MicroDataFrame, MicroSeries

from policyengine.core import map_to_entity

GROUPS = ("tax_unit", "spm_unit", "household")
COLUMNS = ("value", "other")
# Position of each group's id in a person's (household, spm_unit, tax_unit) triple.
INDEX = {"household": 0, "spm_unit": 1, "tax_unit": 2}
# Ids for groups with no members; person-drawn ids stay below 1,000.
EMPTY_ID = {"household": 9_001, "spm_unit": 9_002, "tax_unit": 9_003}
# Shares are sums of quotients, so exact totals of 0 need an absolute tolerance.
ABS = 1e-6

Case = namedtuple("Case", "data amounts people weights")


def _build(
    people: list[tuple[int, int, int]],
    prefixed: bool,
    amounts: dict,
    empty: frozenset = frozenset(),
    rng=None,
    weights: dict | None = None,
):
    """Build entity tables from (household, spm_unit, tax_unit) id triples.

    ``amounts`` maps a column to {group entity: {group id: amount}}; groups
    without an amount get 0. ``prefixed`` stores person links as
    ``person_<entity>_id`` instead of ``<entity>_id``, the two layouts
    map_to_entity accepts. Each entity in ``empty`` gets one more group, with
    no members. ``rng`` shuffles the rows of every table. ``weights`` maps a
    household id to the weight its people and groups share (default 1.0).
    """
    weights = weights or {}
    link = (lambda e: f"person_{e}_id") if prefixed else (lambda e: f"{e}_id")
    rows = list(people)
    if rng is not None:
        rng.shuffle(rows)
    person = pd.DataFrame(
        {
            "person_id": range(len(rows)),
            link("household"): [p[INDEX["household"]] for p in rows],
            link("spm_unit"): [p[INDEX["spm_unit"]] for p in rows],
            link("tax_unit"): [p[INDEX["tax_unit"]] for p in rows],
            "person_weight": [weights.get(p[INDEX["household"]], 1.0) for p in rows],
        }
    )
    data = {"person": MicroDataFrame(person, weights="person_weight")}
    for entity in GROUPS:
        household_of = {p[INDEX[entity]]: p[INDEX["household"]] for p in people}
        ids = sorted(household_of)
        if entity in empty:
            ids.append(EMPTY_ID[entity])
        if rng is not None:
            rng.shuffle(ids)
        table = pd.DataFrame(
            {
                f"{entity}_id": ids,
                f"{entity}_weight": [
                    weights.get(household_of.get(i), 1.0) for i in ids
                ],
            }
        )
        for column in COLUMNS:
            by_id = amounts.get(column, {}).get(entity, {})
            table[column] = [float(by_id.get(i, 0)) for i in ids]
        data[entity] = MicroDataFrame(table, weights=f"{entity}_weight")
    return data


@st.composite
def entity_data(draw, nested: bool) -> Case:
    """Random households of 1-5 people with tax units and SPM units in them."""
    people = []
    weights = {}
    for h in range(draw(st.integers(1, 4))):
        weights[h] = draw(st.sampled_from([0.5, 1.0, 2.0, 7.0]))
        for _ in range(draw(st.integers(1, 5))):
            spm = draw(st.integers(0, 2))
            if nested:
                # Each tax unit id belongs to exactly one SPM unit.
                tax = spm * 3 + draw(st.integers(0, 2))
            else:
                tax = draw(st.integers(0, 2))
            people.append((h, h * 100 + spm, h * 100 + tax))
    empty = frozenset(e for e in GROUPS if draw(st.booleans()))
    amounts = {}
    for column in COLUMNS:
        amounts[column] = {}
        for entity in GROUPS:
            ids = sorted({p[INDEX[entity]] for p in people})
            if entity in empty:
                ids.append(EMPTY_ID[entity])
            drawn = draw(
                st.lists(
                    st.integers(-1_000, 100_000),
                    min_size=len(ids),
                    max_size=len(ids),
                )
            )
            amounts[column][entity] = dict(zip(ids, drawn))
    data = _build(
        people,
        draw(st.booleans()),
        amounts,
        empty=empty,
        rng=draw(st.randoms(use_true_random=False)),
        weights=weights,
    )
    return Case(data, amounts, people, weights)


def _mapped(data, source, target, how, columns=COLUMNS) -> pd.DataFrame:
    """Map value columns, as a plain (unweighted) DataFrame."""
    return pd.DataFrame(
        map_to_entity(data, source, target, columns=list(columns), how=how)
    )


def _target_ids(data, target) -> list:
    return pd.DataFrame(data[target])[f"{target}_id"].tolist()


def _assert_target_order(mapped: pd.DataFrame, data, target) -> None:
    """The result lists the target table's groups in the table's row order.

    Every table here has a RangeIndex; map_to_entity restores row order by
    sorting on the index labels.
    """
    assert mapped[f"{target}_id"].tolist() == _target_ids(data, target)


def _member_total(case: Case, column, entity, weighted=False) -> float:
    """Sum of the amounts of the groups that have members."""
    household_of = {p[INDEX[entity]]: p[INDEX["household"]] for p in case.people}
    return sum(
        amount * (case.weights[household_of[i]] if weighted else 1.0)
        for i, amount in case.amounts[column][entity].items()
        if i in household_of
    )


def _expected_divide(case: Case, column, source, target) -> dict:
    """Each target group's share of the source amounts, counted person by person.

    Each source amount splits equally among the source's members, and each
    member's share goes to that member's target group. Target groups with no
    members get 0.
    """
    size = Counter(p[INDEX[source]] for p in case.people)
    expected = {t: 0.0 for t in _target_ids(case.data, target)}
    for p in case.people:
        s, t = p[INDEX[source]], p[INDEX[target]]
        expected[t] += case.amounts[column][source][s] / size[s]
    return expected


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=False))
def test_divide_keeps_each_total(case):
    """A source's shares add up to its amount, so column totals match.

    A group with no members has nobody to pass its amount to, so it adds
    nothing.
    """
    for source, target in permutations(GROUPS, 2):
        mapped = _mapped(case.data, source, target, "divide")
        _assert_target_order(mapped, case.data, target)
        for column in COLUMNS:
            assert mapped[column].to_numpy().sum() == pytest.approx(
                _member_total(case, column, source), abs=ABS
            ), (source, target, column)


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=False))
def test_divide_keeps_each_weighted_total(case):
    """The result carries the target weights, so weighted totals match too.

    People and groups in a household share its weight, so each share keeps
    its source's weight.
    """
    for source, target in permutations(GROUPS, 2):
        mapped = map_to_entity(
            case.data, source, target, columns=list(COLUMNS), how="divide"
        )
        target_weights = pd.DataFrame(case.data[target])[f"{target}_weight"]
        for column in COLUMNS:
            plain = pd.DataFrame(mapped)[column].to_numpy()
            assert float(mapped[column].sum()) == pytest.approx(
                float((plain * target_weights.to_numpy()).sum()), abs=ABS
            ), (source, target, column)
            assert float(mapped[column].sum()) == pytest.approx(
                _member_total(case, column, source, weighted=True), abs=ABS
            ), (source, target, column)


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=False))
def test_divide_gives_each_target_its_members_shares(case):
    """Each target receives the shares of the members it holds, in every
    column, and a target with no members receives 0."""
    for source, target in permutations(GROUPS, 2):
        # columns=None maps every non-id, non-weight column.
        mapped = pd.DataFrame(map_to_entity(case.data, source, target, how="divide"))
        assert set(COLUMNS) <= set(mapped.columns)
        for column in COLUMNS:
            got = dict(zip(mapped[f"{target}_id"], mapped[column]))
            assert got == pytest.approx(
                _expected_divide(case, column, source, target), abs=ABS
            ), (source, target, column)


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=False))
def test_divide_matches_the_route_through_persons(case):
    """Group-to-group divide equals group->person divide, then person->group sum."""
    for source, target in permutations(GROUPS, 2):
        per_person = _mapped(case.data, source, "person", "divide", ["value"])
        through_persons = pd.Series(
            map_to_entity(
                case.data,
                "person",
                target,
                values=per_person["value"].to_numpy(),
                how="sum",
            )
        )
        direct = _mapped(case.data, source, target, "divide", ["value"])
        assert direct["value"].to_numpy() == pytest.approx(
            through_persons.to_numpy(), abs=ABS
        ), (source, target)


@settings(max_examples=100, deadline=None)
@given(entity_data(nested=False))
def test_divide_with_values_matches_the_column_path(case):
    """Passing the amounts as an array returns a weighted series that matches
    naming the column."""
    for source, target in permutations(GROUPS, 2):
        from_values = map_to_entity(
            case.data,
            source,
            target,
            values=pd.DataFrame(case.data[source])["value"].to_numpy(),
            how="divide",
        )
        from_column = map_to_entity(
            case.data, source, target, columns=["value"], how="divide"
        )
        assert isinstance(from_values, MicroSeries)
        assert len(from_values) == len(case.data[target])
        assert pd.Series(from_values).to_numpy() == pytest.approx(
            pd.DataFrame(from_column)["value"].to_numpy(), abs=ABS
        ), (source, target)
        assert float(from_values.sum()) == pytest.approx(
            float(from_column["value"].sum()), abs=ABS
        ), (source, target)


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=True))
def test_sum_keeps_the_total_when_sources_nest_in_targets(case):
    for source, target in [
        ("tax_unit", "spm_unit"),
        ("tax_unit", "household"),
        ("spm_unit", "household"),
    ]:
        mapped = _mapped(case.data, source, target, "sum")
        _assert_target_order(mapped, case.data, target)
        for column in COLUMNS:
            assert mapped[column].to_numpy().sum() == pytest.approx(
                _member_total(case, column, source), abs=ABS
            ), (source, target, column)
        # When every source sits in one target, sum and divide agree.
        assert mapped[list(COLUMNS)].to_numpy() == pytest.approx(
            _mapped(case.data, source, target, "divide")[list(COLUMNS)].to_numpy(),
            abs=ABS,
        ), (source, target)


@settings(max_examples=200, deadline=None)
@given(entity_data(nested=True))
def test_sum_from_a_containing_group_gives_each_member_group_its_value(case):
    """Mapping a group onto the smaller groups inside it repeats its value.

    This pins the current coarse-to-fine behaviour, which the UK
    household-to-benunit test checks only for one benunit per household. A
    group with no members sits in no containing group and gets 0.
    """
    for source, target in [
        ("spm_unit", "tax_unit"),
        ("household", "tax_unit"),
        ("household", "spm_unit"),
    ]:
        container = {p[INDEX[target]]: p[INDEX[source]] for p in case.people}
        mapped = _mapped(case.data, source, target, "sum")
        _assert_target_order(mapped, case.data, target)
        for column in COLUMNS:
            for target_id, value in zip(mapped[f"{target}_id"], mapped[column]):
                if target_id in container:
                    expected = case.amounts[column][source][container[target_id]]
                else:
                    expected = 0
                assert value == expected, (source, target, column, target_id)


def _one_column(column_amounts: dict) -> dict:
    return {"value": column_amounts}


def test_divide_keeps_a_two_person_unit_whole_inside_one_household():
    """A $100 tax unit whose two members share a household maps to $100.

    Before the fix, divide split the value by the unit's two members but added
    it once per (tax unit, household) pair, so the household received $50.
    """
    data = _build(
        [(1, 10, 100), (1, 10, 100)],
        prefixed=False,
        amounts=_one_column({"tax_unit": {100: 100}}),
    )
    mapped = _mapped(data, "tax_unit", "household", "divide", ["value"])
    assert mapped["value"].tolist() == [100.0]


def test_divide_splits_a_unit_across_targets_by_member_share():
    """Two of a tax unit's three members are in SPM unit 10, one in SPM unit 11."""
    data = _build(
        [(1, 10, 100), (1, 10, 100), (1, 11, 100)],
        prefixed=True,
        amounts=_one_column({"tax_unit": {100: 300}}),
    )
    mapped = _mapped(data, "tax_unit", "spm_unit", "divide", ["value"])
    by_spm = dict(zip(mapped["spm_unit_id"], mapped["value"]))
    assert by_spm == pytest.approx({10: 200.0, 11: 100.0})


def test_divide_leaves_out_the_share_of_a_member_with_no_target_link():
    """A $100 tax unit has two members, and only one has a household link.

    The linked member's household gets that member's $50 share. The other
    share has no target to go to, as in the route through persons. This
    case has no SPM units.
    """
    person = pd.DataFrame(
        {
            "person_id": [0, 1],
            "household_id": [1, np.nan],
            "tax_unit_id": [100, 100],
            "person_weight": 1.0,
        }
    )
    data = {
        "person": MicroDataFrame(person, weights="person_weight"),
        "tax_unit": MicroDataFrame(
            pd.DataFrame(
                {"tax_unit_id": [100], "tax_unit_weight": 1.0, "value": 100.0}
            ),
            weights="tax_unit_weight",
        ),
        "household": MicroDataFrame(
            pd.DataFrame({"household_id": [1], "household_weight": 1.0}),
            weights="household_weight",
        ),
    }
    mapped = _mapped(data, "tax_unit", "household", "divide", ["value"])
    assert mapped["value"].tolist() == [50.0]
