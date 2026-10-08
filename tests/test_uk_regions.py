"""Tests for UK region definitions."""

from unittest.mock import patch

import pandas as pd
import pytest
from microdf import MicroDataFrame
from pydantic import TypeAdapter

from policyengine.core.scoping_strategy import (
    RegionGroupStrategy,
    RowFilterStrategy,
    ScopingStrategy,
)
from policyengine.countries.uk.regions import (
    UK_COUNTRIES,
    build_uk_region_registry,
    uk_region_registry,
)


class TestUKCountries:
    """Tests for UK country definitions."""

    def test__given_uk_countries__then_has_four_entries(self):
        """Given: UK_COUNTRIES dictionary
        When: Checking length
        Then: Contains 4 countries
        """
        # Then
        assert len(UK_COUNTRIES) == 4

    def test__given_uk_countries__then_all_countries_present(self):
        """Given: UK_COUNTRIES dictionary
        When: Checking for countries
        Then: England, Scotland, Wales, NI are all present
        """
        # Then
        assert "england" in UK_COUNTRIES
        assert "scotland" in UK_COUNTRIES
        assert "wales" in UK_COUNTRIES
        assert "northern_ireland" in UK_COUNTRIES

    def test__given_uk_countries__then_labels_capitalized(self):
        """Given: UK_COUNTRIES dictionary
        When: Checking labels
        Then: Labels are properly capitalized
        """
        # Then
        assert UK_COUNTRIES["england"] == "England"
        assert UK_COUNTRIES["scotland"] == "Scotland"
        assert UK_COUNTRIES["wales"] == "Wales"
        assert UK_COUNTRIES["northern_ireland"] == "Northern Ireland"


class TestUKRegionRegistry:
    """Tests for the UK region registry."""

    def test__given_uk_registry__then_country_id_is_uk(self):
        """Given: UK region registry
        When: Checking country_id
        Then: Value is "uk"
        """
        # Then
        assert uk_region_registry.country_id == "uk"

    def test__given_uk_registry__then_has_national_region(self):
        """Given: UK region registry
        When: Getting national region
        Then: Returns UK with correct dataset path
        """
        # When
        national = uk_region_registry.get_national()

        # Then
        assert national is not None
        assert national.code == "uk"
        assert national.label == "United Kingdom"
        assert national.region_type == "national"
        assert (
            national.dataset_path
            == "hf://policyengine/policyengine-uk-data-private/enhanced_frs_2024_25.h5"
            "@1.56.16"
        )
        assert not national.requires_filter

    def test__given_uk_registry__then_has_four_country_regions(self):
        """Given: UK region registry
        When: Getting country regions
        Then: Contains 4 countries
        """
        # When
        countries = uk_region_registry.get_by_type("country")

        # Then
        assert len(countries) == 4

    def test__given_england_region__then_filters_from_national(self):
        """Given: England country region
        When: Checking its properties
        Then: Filters from national using the nine English regions
        """
        # When
        england = uk_region_registry.get("country/england")

        # Then
        assert england is not None
        assert england.label == "England"
        assert england.region_type == "country"
        assert england.parent_code == "uk"
        assert england.requires_filter
        assert isinstance(england.scoping_strategy, RowFilterStrategy)
        assert england.scoping_strategy.variable_name == "region"
        assert len(england.scoping_strategy.variable_value) == 9
        assert england.dataset_path is None

    def test__given_country_regions__then_filter_stored_regions(self):
        """Given: UK country regions
        When: Checking their scoping strategies
        Then: Each country retains a row filter on stored regions
        """
        for code in UK_COUNTRIES:
            region = uk_region_registry.get(f"country/{code}")
            assert region is not None
            assert region.scoping_strategy is not None
            assert isinstance(region.scoping_strategy, RowFilterStrategy)
            assert region.scoping_strategy.variable_name == "region"
            if code != "england":
                assert region.scoping_strategy.variable_value == code.upper()

    def test__given_scotland_region__then_filters_from_national(self):
        """Given: Scotland country region
        When: Checking its properties
        Then: Filters from national with correct value
        """
        # When
        scotland = uk_region_registry.get("country/scotland")

        # Then
        assert scotland is not None
        assert scotland.label == "Scotland"
        assert scotland.requires_filter
        assert scotland.scoping_strategy.variable_value == "SCOTLAND"

    def test__given_wales_region__then_filters_from_national(self):
        """Given: Wales country region
        When: Checking its properties
        Then: Filters from national with correct value
        """
        # When
        wales = uk_region_registry.get("country/wales")

        # Then
        assert wales is not None
        assert wales.label == "Wales"
        assert wales.requires_filter
        assert wales.scoping_strategy.variable_value == "WALES"

    def test__given_northern_ireland_region__then_filters_from_national(self):
        """Given: Northern Ireland country region
        When: Checking its properties
        Then: Filters from national with correct value
        """
        # When
        ni = uk_region_registry.get("country/northern_ireland")

        # Then
        assert ni is not None
        assert ni.label == "Northern Ireland"
        assert ni.requires_filter
        assert ni.scoping_strategy.variable_value == "NORTHERN_IRELAND"

    def test__given_uk_national__then_children_are_countries(self):
        """Given: UK national region
        When: Getting its children
        Then: All children are country regions
        """
        # When
        uk_children = uk_region_registry.get_children("uk")

        # Then
        assert len(uk_children) == 4
        assert all(c.region_type == "country" for c in uk_children)

    def test__given_uk_registry__then_only_national_has_dataset(self):
        """Given: UK region registry
        When: Getting dataset regions
        Then: Only national has dedicated dataset
        """
        # When
        dataset_regions = uk_region_registry.get_dataset_regions()

        # Then
        assert len(dataset_regions) == 1
        assert dataset_regions[0].code == "uk"

    def test__given_uk_registry__then_filter_regions_are_countries(self):
        """Given: UK region registry
        When: Getting filter regions
        Then: All 4 countries require filter
        """
        # When
        filter_regions = uk_region_registry.get_filter_regions()

        # Then
        assert len(filter_regions) == 4
        assert all(r.region_type == "country" for r in filter_regions)

    def test__given_default_registry__then_has_5_regions(self):
        """Given: Default UK registry
        When: Counting regions
        Then: Contains 1 national + 4 countries = 5
        """
        # Then
        assert len(uk_region_registry) == 5


class TestUKRegionRegistryBuilder:
    """Tests for UK registry builder with optional regions."""

    def test__given_builder_without_optional_regions__then_returns_5_regions(
        self,
    ):
        """Given: build_uk_region_registry with optional regions disabled
        When: Building registry
        Then: Returns 5 base regions only
        """
        # When
        registry = build_uk_region_registry(
            include_constituencies=False,
            include_local_authorities=False,
        )

        # Then
        assert len(registry) == 5  # national + 4 countries

    def test__given_builder__then_accepts_include_constituencies_flag(self):
        """Given: build_uk_region_registry
        When: Passing include_constituencies=False
        Then: Returns registry without constituencies
        """
        # When
        registry = build_uk_region_registry(include_constituencies=False)

        # Then
        assert registry is not None
        assert len(registry.get_by_type("constituency")) == 0

    def test__given_builder__then_accepts_include_local_authorities_flag(self):
        """Given: build_uk_region_registry
        When: Passing include_local_authorities=False
        Then: Returns registry without local authorities
        """
        # When
        registry = build_uk_region_registry(include_local_authorities=False)

        # Then
        assert registry is not None
        assert len(registry.get_by_type("local_authority")) == 0

    @patch(
        "policyengine.countries.uk.regions._load_constituencies_from_csv",
        return_value=[{"code": "C001", "name": "Constituency A"}],
    )
    def test__given_constituencies_included__then_filters_on_dataset_geography(
        self,
        _mock_loader,
    ):
        """Given: constituencies are included
        When: Building the registry
        Then: They filter on the dataset's longwise constituency code
        """
        # When
        registry = build_uk_region_registry(include_constituencies=True)
        constituency = registry.get("constituency/C001")

        # Then
        assert constituency is not None
        assert isinstance(constituency.scoping_strategy, RowFilterStrategy)
        assert constituency.scoping_strategy.variable_name == "constituency_code_oa"
        assert constituency.scoping_strategy.variable_value == "C001"

    @patch(
        "policyengine.countries.uk.regions._load_local_authorities_from_csv",
        return_value=[{"code": "LA001", "name": "Local Authority A"}],
    )
    def test__given_local_authorities_included__then_filters_on_dataset_geography(
        self,
        _mock_loader,
    ):
        """Given: local authorities are included
        When: Building the registry
        Then: They filter on the dataset's longwise local-authority code
        """
        # When
        registry = build_uk_region_registry(include_local_authorities=True)
        local_authority = registry.get("local_authority/LA001")

        # Then
        assert local_authority is not None
        assert isinstance(local_authority.scoping_strategy, RowFilterStrategy)
        assert local_authority.scoping_strategy.variable_name == "la_code_oa"
        assert local_authority.scoping_strategy.variable_value == "LA001"


# The pinned UK model's Region enum contains nine English ITL1 regions and
# Scotland, Wales and Northern Ireland. Country is derived, not a stored input.
_REGION_COUNTRIES = [
    ("NORTH_EAST", "england"),
    ("NORTH_WEST", "england"),
    ("YORKSHIRE", "england"),
    ("EAST_MIDLANDS", "england"),
    ("WEST_MIDLANDS", "england"),
    ("EAST_OF_ENGLAND", "england"),
    ("LONDON", "england"),
    ("SOUTH_EAST", "england"),
    ("SOUTH_WEST", "england"),
    ("SCOTLAND", "scotland"),
    ("WALES", "wales"),
    ("NORTHERN_IRELAND", "northern_ireland"),
    ("UNKNOWN", None),
]


@pytest.fixture
def region_only_uk_data():
    """Raw UK entities without a derived country column, with distinct weights."""
    household_ids = list(range(1, len(_REGION_COUNTRIES) + 1))
    household = pd.DataFrame(
        {
            "household_id": household_ids,
            "household_weight": [100.0 + hid for hid in household_ids],
            "region": [region for region, _ in _REGION_COUNTRIES],
        }
    ).iloc[::-1]
    person = pd.DataFrame(
        {
            "person_id": [
                hid * 10 + offset for hid in household_ids for offset in (1, 2)
            ],
            "person_household_id": [hid for hid in household_ids for _ in (1, 2)],
            "person_benunit_id": [hid * 100 for hid in household_ids for _ in (1, 2)],
            "person_weight": [100.0 + hid for hid in household_ids for _ in (1, 2)],
        }
    )
    benunit = pd.DataFrame(
        {
            "benunit_id": [hid * 100 for hid in household_ids],
            "benunit_weight": [100.0 + hid for hid in household_ids],
        }
    )
    return {
        name: MicroDataFrame(frame, weights=f"{name}_weight")
        for name, frame in (
            ("person", person),
            ("benunit", benunit),
            ("household", household),
        )
    }


@pytest.mark.parametrize("country", UK_COUNTRIES)
@pytest.mark.parametrize("encoding", ["str", "bytes", "category"])
def test_country_scoping_uses_raw_regions_and_preserves_entities(
    country, encoding, region_only_uk_data
):
    household = region_only_uk_data["household"]
    if encoding == "bytes":
        household["region"] = household["region"].map(str.encode)
    elif encoding == "category":
        household["region"] = household["region"].astype("category")
    originals = {
        entity: pd.DataFrame(frame).copy(deep=True)
        for entity, frame in region_only_uk_data.items()
    }
    expected_households = {
        index
        for index, (_, expected_country) in enumerate(_REGION_COUNTRIES, start=1)
        if expected_country == country
    }

    strategy = uk_region_registry.get(f"country/{country}").scoping_strategy
    result = strategy.apply(region_only_uk_data, ["benunit", "household"], 2026)

    for entity, id_column, ids in (
        ("household", "household_id", expected_households),
        ("person", "person_household_id", expected_households),
        ("benunit", "benunit_id", {hid * 100 for hid in expected_households}),
    ):
        expected = originals[entity][originals[entity][id_column].isin(ids)]
        pd.testing.assert_frame_equal(
            pd.DataFrame(result[entity]), expected.reset_index(drop=True)
        )
        assert result[entity].weights.tolist() == expected[f"{entity}_weight"].tolist()
        pd.testing.assert_frame_equal(
            pd.DataFrame(region_only_uk_data[entity]), originals[entity]
        )


def test_england_scoping_allows_unrepresented_english_regions(region_only_uk_data):
    """Missing English regions must not prevent selecting those present."""
    # Only North West (household 2) and Scotland (household 10) are represented.
    selected = {
        entity: MicroDataFrame(
            pd.DataFrame(frame)[frame[column].isin(ids)], weights=f"{entity}_weight"
        )
        for entity, frame, column, ids in (
            ("household", region_only_uk_data["household"], "household_id", [2, 10]),
            ("person", region_only_uk_data["person"], "person_household_id", [2, 10]),
            ("benunit", region_only_uk_data["benunit"], "benunit_id", [200, 1000]),
        )
    }

    result = uk_region_registry.get("country/england").scoping_strategy.apply(
        selected, ["benunit", "household"], 2026
    )

    assert result["household"]["household_id"].tolist() == [2]
    assert result["person"]["person_id"].tolist() == [21, 22]
    assert result["benunit"]["benunit_id"].tolist() == [200]


@pytest.mark.parametrize("country", UK_COUNTRIES)
def test_country_scoping_json_round_trip(country, region_only_uk_data):
    strategy = uk_region_registry.get(f"country/{country}").scoping_strategy
    restored = TypeAdapter(ScopingStrategy).validate_json(strategy.model_dump_json())

    assert restored == strategy
    assert restored.cache_key == strategy.cache_key
    expected = strategy.apply(region_only_uk_data, ["benunit", "household"], 2026)
    actual = restored.apply(region_only_uk_data, ["benunit", "household"], 2026)
    for entity in expected:
        pd.testing.assert_frame_equal(
            pd.DataFrame(actual[entity]), pd.DataFrame(expected[entity])
        )


def test_country_filters_can_be_combined_without_duplicate_households(
    region_only_uk_data,
):
    """The worker composes country groups from RowFilterStrategy members."""
    members = [
        uk_region_registry.get(f"country/{country}").scoping_strategy
        for country in ("england", "scotland", "england")
    ]
    assert all(isinstance(member, RowFilterStrategy) for member in members)

    result = RegionGroupStrategy(members=members).apply(
        region_only_uk_data, ["benunit", "household"], 2026
    )

    assert set(result["household"]["household_id"]) == set(range(1, 11))
    assert result["household"]["household_id"].is_unique
