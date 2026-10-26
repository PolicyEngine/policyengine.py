"""Tests for UK region definitions."""

from collections import Counter
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
from policyengine.provenance.manifest import CountryReleaseManifest

# The certified bundle's national dataset, and the Microcosm local-area
# release its constituency and local-authority regions are routed to.
UK_CERTIFIED_NATIONAL_URI = (
    "hf://policyengine/populace-uk-private/microcosm_uk_2024_25.h5"
    "@microcosm-uk-2024-25-national-20261025T091414Z-a6299504"
)
UK_CERTIFIED_LOCAL_AREA_URI = (
    "hf://policyengine/populace-uk-private/microcosm_uk_2024_25_dense.h5"
    "@microcosm-uk-2024-25-dense-20261019T000432Z-ee5c2dbe"
)
UK_AREA_REGION_COUNT = 650 + 361


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
        assert national.dataset_path == UK_CERTIFIED_NATIONAL_URI
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

    def test__given_uk_national__then_children_are_countries_and_areas(self):
        """Given: UK national region
        When: Getting its children
        Then: The 4 countries, 650 constituencies and 361 local authorities
        """
        # When
        uk_children = uk_region_registry.get_children("uk")

        # Then
        assert Counter(c.region_type for c in uk_children) == {
            "country": 4,
            "constituency": 650,
            "local_authority": 361,
        }

    def test__given_uk_registry__then_national_and_area_regions_have_datasets(
        self,
    ):
        """Given: UK region registry routed to a Microcosm local-area release
        When: Getting dataset regions
        Then: National loads the national dataset, area regions the local one
        """
        # When
        dataset_regions = uk_region_registry.get_dataset_regions()

        # Then
        assert len(dataset_regions) == 1 + UK_AREA_REGION_COUNT
        paths = {r.region_type: set() for r in dataset_regions}
        for region in dataset_regions:
            paths[region.region_type].add(region.dataset_path)
        assert paths == {
            "national": {UK_CERTIFIED_NATIONAL_URI},
            "constituency": {UK_CERTIFIED_LOCAL_AREA_URI},
            "local_authority": {UK_CERTIFIED_LOCAL_AREA_URI},
        }

    def test__given_uk_registry__then_countries_and_areas_filter(self):
        """Given: UK region registry
        When: Getting filter regions
        Then: The 4 countries and every area region require a filter
        """
        # When
        filter_regions = uk_region_registry.get_filter_regions()

        # Then
        assert len(filter_regions) == 4 + UK_AREA_REGION_COUNT
        assert {r.region_type for r in filter_regions} == {
            "country",
            "constituency",
            "local_authority",
        }

    def test__given_default_registry__then_has_1016_regions(self):
        """Given: Default UK registry routed to a Microcosm local-area release
        When: Counting regions
        Then: 1 national + 4 countries + 650 constituencies + 361 LAs = 1,016
        """
        # Then
        assert len(uk_region_registry) == 5 + UK_AREA_REGION_COUNT


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


MICROCOSM_NATIONAL_TAG = "microcosm-uk-2024-25-national-20261101T000000Z-aaaaaaaa"
MICROCOSM_DENSE_TAG = "microcosm-uk-2024-25-dense-20261101T000000Z-bbbbbbbb"
MICROCOSM_NATIONAL_URI = (
    "hf://policyengine/populace-uk-private/microcosm_uk_2024_25.h5"
    f"@{MICROCOSM_NATIONAL_TAG}"
)
EFRS_AREA_URI = (
    "hf://policyengine/policyengine-uk-data-private/enhanced_frs_2024_25.h5@1.58.0"
)
MICROCOSM_DENSE_URI = (
    "hf://policyengine/populace-uk-private/microcosm_uk_2024_25_dense.h5"
    f"@{MICROCOSM_DENSE_TAG}"
)


def _uk_routed_manifest(kind: str) -> CountryReleaseManifest:
    """A certified Microcosm national bundle whose area regions are routed."""
    if kind == "area_coded_national":
        area_name, area_reference = (
            "enhanced_frs_2024_25",
            {
                "path": "enhanced_frs_2024_25.h5",
                "repo_id": "policyengine/policyengine-uk-data-private",
                "repo_type": "model",
                "revision": "1.58.0",
            },
        )
    else:
        area_name, area_reference = (
            "microcosm_uk_2024_25_dense",
            {
                "path": "microcosm_uk_2024_25_dense.h5",
                "repo_id": "policyengine/populace-uk-private",
                "repo_type": "dataset",
                "revision": MICROCOSM_DENSE_TAG,
            },
        )
    area_template = {"path_template": area_reference["path"]}
    return CountryReleaseManifest.model_validate(
        {
            "country_id": "uk",
            "policyengine_version": "9.9.9",
            "model_package": {"name": "policyengine-uk", "version": "2.126.12"},
            "data_package": {
                "name": "microcosm-data",
                "version": "0.1.0",
                "repo_id": "policyengine/populace-uk-private",
                "repo_type": "dataset",
                "release_manifest_revision": MICROCOSM_NATIONAL_TAG,
            },
            "default_dataset": "microcosm_uk_2024_25",
            "datasets": {
                "microcosm_uk_2024_25": {
                    "path": "microcosm_uk_2024_25.h5",
                    "repo_id": "policyengine/populace-uk-private",
                    "revision": MICROCOSM_NATIONAL_TAG,
                },
                area_name: area_reference,
            },
            "region_datasets": {
                "national": {"path_template": "microcosm_uk_2024_25.h5"},
                "constituency": area_template,
                "local_authority": area_template,
            },
            "regional_release_kind": kind,
        }
    )


def _uk_unrouted_manifest() -> CountryReleaseManifest:
    """A certified national bundle that routes no area regions."""
    manifest = _uk_routed_manifest("local_area")
    return manifest.model_copy(
        update={
            "region_datasets": {"national": manifest.region_datasets["national"]},
            "regional_release_kind": None,
        }
    )


class TestUKAreaRegionRouting:
    """Area regions load the dataset certification routes them to."""

    def test__given_unrouted_bundle__then_area_regions_filter_the_national_dataset(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            "policyengine.provenance.manifest.get_release_manifest",
            lambda country_id: _uk_unrouted_manifest(),
        )

        default = build_uk_region_registry()
        registry = build_uk_region_registry(
            include_constituencies=True, include_local_authorities=True
        )

        assert registry.get("constituency/E14001063").dataset_path is None
        assert registry.get("local_authority/N09000011").dataset_path is None
        assert len(default) == 5

    def test__given_national_first_bundle__then_area_regions_load_the_efrs(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            "policyengine.provenance.manifest.get_release_manifest",
            lambda country_id: _uk_routed_manifest("area_coded_national"),
        )

        default = build_uk_region_registry()
        registry = build_uk_region_registry(
            include_constituencies=True, include_local_authorities=True
        )

        # An area-coded national route does not add area regions by default.
        assert len(default) == 5
        assert registry.get("uk").dataset_path == MICROCOSM_NATIONAL_URI
        assert registry.get("country/wales").dataset_path is None
        constituency = registry.get("constituency/E14001063")
        assert constituency.dataset_path == EFRS_AREA_URI
        assert constituency.scoping_strategy.variable_name == "constituency_code_oa"
        local_authority = registry.get("local_authority/N09000011")
        assert local_authority.dataset_path == EFRS_AREA_URI
        assert local_authority.scoping_strategy.variable_name == "la_code_oa"

    def test__given_local_area_bundle__then_default_registry_adds_area_regions(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            "policyengine.provenance.manifest.get_release_manifest",
            lambda country_id: _uk_routed_manifest("local_area"),
        )

        registry = build_uk_region_registry()

        assert len(registry.get_by_type("constituency")) == 650
        assert len(registry.get_by_type("local_authority")) == 361
        assert registry.get("constituency/N05000001").dataset_path == (
            MICROCOSM_DENSE_URI
        )
        assert registry.get("local_authority/E06000063").dataset_path == (
            MICROCOSM_DENSE_URI
        )
        assert registry.get("uk").dataset_path == MICROCOSM_NATIONAL_URI

    def test__given_local_area_bundle__then_explicit_exclusion_wins(self, monkeypatch):
        monkeypatch.setattr(
            "policyengine.provenance.manifest.get_release_manifest",
            lambda country_id: _uk_routed_manifest("local_area"),
        )

        registry = build_uk_region_registry(
            include_constituencies=False, include_local_authorities=False
        )

        assert len(registry) == 5


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
