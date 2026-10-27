"""UK nation filters agree with policyengine-uk's ``country`` formula.

The nation regions filter the stored household ``region`` column, so
policyengine.py keeps its own list of the regions in each nation
(``countries/uk/regions.py``). policyengine-uk keeps another in the formula
that derives ``country`` from ``region``. These tests take the expected
nations from policyengine-uk itself, so a change on either side fails here
instead of silently moving households between nations
(PolicyEngine/policyengine.py#569).
"""

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from microdf import MicroDataFrame

from policyengine.countries.uk.regions import UK_COUNTRIES, uk_region_registry

pytest.importorskip("policyengine_uk")

GROUP_ENTITIES = ["benunit", "household"]
NATIONS = [code.upper() for code in UK_COUNTRIES]


@pytest.fixture(scope="module")
def model_country() -> dict[str, str]:
    """policyengine-uk's ``country`` for every value of its ``Region`` enum."""
    from policyengine_uk import Simulation
    from policyengine_uk.variables.household.demographic.geography import Region

    regions = [region.name for region in Region]
    situation = {
        "people": {f"p{i}": {"age": {"2026": 40}} for i in range(len(regions))},
        "benunits": {f"b{i}": {"members": [f"p{i}"]} for i in range(len(regions))},
        "households": {
            f"h{i}": {"members": [f"p{i}"], "region": {"2026": region}}
            for i, region in enumerate(regions)
        },
    }
    simulation = Simulation(situation=situation)
    # The households come back in situation order; check rather than assume.
    assert [str(r) for r in simulation.calculate("region", 2026)] == regions
    countries = simulation.calculate("country", 2026)
    return {region: str(country) for region, country in zip(regions, countries)}


def _nation_filter(nation: str):
    return uk_region_registry.get(f"country/{nation.lower()}").scoping_strategy


def _entity_data(
    regions,
    household_ids,
    people=None,
    person_order=None,
    benunit_order=None,
    encode=False,
) -> dict[str, pd.DataFrame]:
    """Region-only UK tables, with no ``country`` column.

    Household ``h`` has benefit unit ``1000 + h`` and ``people[i]`` people
    (default one) with IDs ``100 * h + k``. ``person_order`` and
    ``benunit_order`` reorder those rows independently of the households;
    ``encode`` stores ``region`` as bytes.
    """
    household_ids = list(household_ids)
    people = people or [1] * len(household_ids)
    person = pd.DataFrame(
        {
            "person_id": [
                100 * h + k for h, n in zip(household_ids, people) for k in range(n)
            ],
            "person_household_id": [
                h for h, n in zip(household_ids, people) for _ in range(n)
            ],
            "person_benunit_id": [
                1000 + h for h, n in zip(household_ids, people) for _ in range(n)
            ],
        }
    ).assign(person_weight=1.0)
    benunit = pd.DataFrame({"benunit_id": [1000 + h for h in household_ids]}).assign(
        benunit_weight=1.0
    )
    household = pd.DataFrame(
        {
            "household_id": household_ids,
            "household_weight": 1.0,
            "region": [r.encode() if encode else r for r in regions],
        }
    )
    if person_order is not None:
        person = person.iloc[list(person_order)].reset_index(drop=True)
    if benunit_order is not None:
        benunit = benunit.iloc[list(benunit_order)].reset_index(drop=True)
    return {"person": person, "benunit": benunit, "household": household}


def _micro(tables) -> dict[str, MicroDataFrame]:
    return {
        entity: MicroDataFrame(frame, weights=f"{entity}_weight")
        for entity, frame in tables.items()
    }


def test_registry_nations_are_policyengine_uk_nations(model_country):
    assert set(model_country.values()) - {"UNKNOWN"} == set(NATIONS)


@pytest.mark.parametrize("nation", NATIONS)
def test_each_nation_keeps_the_regions_policyengine_uk_puts_in_it(
    model_country, nation
):
    """Exhaustive over policyengine-uk's Region enum, UNKNOWN included."""
    regions = list(model_country)
    household_ids = range(1, len(regions) + 1)

    result = _nation_filter(nation).apply(
        _micro(_entity_data(regions, household_ids)), GROUP_ENTITIES, 2026
    )

    expected = [
        household_id
        for household_id, region in zip(household_ids, regions)
        if model_country[region] == nation
    ]
    assert sorted(result["household"]["household_id"]) == expected


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_nation_filters_split_any_dataset_as_policyengine_uk_does(model_country, data):
    """For region-only data with 1-3 people per household, separately ordered
    person, benefit-unit and household rows, and str or bytes regions: each
    nation filter keeps exactly the households policyengine-uk assigns to that
    nation, once each, with all their people and their benefit units. The four
    are disjoint and together keep every household whose region policyengine-uk
    places in a nation."""
    regions = data.draw(
        st.lists(st.sampled_from(sorted(model_country)), min_size=1, max_size=20)
    )
    n = len(regions)
    household_ids = data.draw(st.permutations(range(1, n + 1)))
    people = data.draw(st.lists(st.integers(1, 3), min_size=n, max_size=n))
    tables = _entity_data(
        regions,
        household_ids,
        people=people,
        person_order=data.draw(st.permutations(range(sum(people)))),
        benunit_order=data.draw(st.permutations(range(n))),
        encode=data.draw(st.booleans()),
    )
    nation_of = {
        household_id: model_country[region]
        for household_id, region in zip(household_ids, regions)
    }
    person = tables["person"]

    kept = {}
    for nation in NATIONS:
        expected = sorted(h for h, n in nation_of.items() if n == nation)
        if not expected:
            with pytest.raises(ValueError, match="No households found"):
                _nation_filter(nation).apply(_micro(tables), GROUP_ENTITIES, 2026)
            continue
        result = _nation_filter(nation).apply(_micro(tables), GROUP_ENTITIES, 2026)
        kept[nation] = sorted(result["household"]["household_id"])
        assert kept[nation] == expected
        assert sorted(result["person"]["person_id"]) == sorted(
            person.loc[person["person_household_id"].isin(expected), "person_id"]
        )
        assert sorted(result["benunit"]["benunit_id"]) == [1000 + h for h in expected]

    all_kept = [h for households in kept.values() for h in households]
    assert sorted(all_kept) == sorted(h for h, n in nation_of.items() if n != "UNKNOWN")


@pytest.mark.parametrize("nation", NATIONS)
def test_nation_simulation_runs_on_region_only_data(model_country, nation):
    """End to end through the UK model on data that stores ``region`` only."""
    import policyengine as pe
    from policyengine.core import Simulation
    from policyengine.tax_benefit_models.uk.datasets import (
        PolicyEngineUKDataset,
        UKYearData,
    )

    regions = list(model_country)
    household_ids = list(range(1, len(regions) + 1))
    tables = _entity_data(regions, household_ids)
    tables["person"]["age"] = 40
    tables["household"] = tables["household"].assign(
        tenure_type="RENT_PRIVATELY", rent=9_000.0, council_tax=1_500.0
    )
    micro = _micro(tables)
    dataset = PolicyEngineUKDataset(
        name="region-only",
        description="UK tables with region and no country column",
        filepath=None,
        year=2026,
        data=UKYearData(
            person=micro["person"],
            benunit=micro["benunit"],
            household=micro["household"],
        ),
    )

    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.uk.model,
        scoping_strategy=_nation_filter(nation),
        extra_variables={"household": ["country"]},
    )
    simulation.run()

    household = pd.DataFrame(simulation.output_dataset.data.household)
    assert sorted(household["household_id"]) == [
        household_id
        for household_id, region in zip(household_ids, regions)
        if model_country[region] == nation
    ]
    assert set(household["country"]) == {nation}
