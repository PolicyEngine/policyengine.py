"""Tests for US region definitions."""

from policyengine.countries.us.data import DISTRICT_COUNTS, US_STATES
from policyengine.countries.us.regions import (
    build_us_region_registry,
    us_region_registry,
)
from policyengine.provenance.manifest import CountryReleaseManifest


class TestUSStates:
    """Tests for US state definitions."""

    def test__given_us_states_dict__then_has_51_entries(self):
        """Given: US_STATES dictionary
        When: Checking length
        Then: Contains 50 states + DC = 51 entries
        """
        # Then
        assert len(US_STATES) == 51

    def test__given_us_states__then_includes_dc(self):
        """Given: US_STATES dictionary
        When: Looking for DC
        Then: DC is present with full name
        """
        # Then
        assert "DC" in US_STATES
        assert US_STATES["DC"] == "District of Columbia"

    def test__given_us_states__then_includes_major_states(self):
        """Given: US_STATES dictionary
        When: Checking for major states
        Then: CA, TX, NY, FL are present
        """
        # Then
        assert "CA" in US_STATES
        assert "TX" in US_STATES
        assert "NY" in US_STATES
        assert "FL" in US_STATES


class TestUSDistrictCounts:
    """Tests for congressional district counts."""

    def test__given_district_counts__then_every_state_has_count(self):
        """Given: DISTRICT_COUNTS dictionary
        When: Checking against US_STATES
        Then: Every state has a district count
        """
        # When/Then
        for state in US_STATES:
            assert state in DISTRICT_COUNTS, f"Missing district count for {state}"

    def test__given_district_counts__then_total_is_436(self):
        """Given: DISTRICT_COUNTS dictionary
        When: Summing all values
        Then: Total is 435 voting + 1 DC delegate = 436
        """
        # When
        total = sum(DISTRICT_COUNTS.values())

        # Then
        assert total == 436

    def test__given_district_counts__then_dc_has_one(self):
        """Given: DISTRICT_COUNTS for DC
        When: Checking value
        Then: DC has 1 at-large delegate
        """
        # Then
        assert DISTRICT_COUNTS["DC"] == 1

    def test__given_district_counts__then_large_states_have_many(self):
        """Given: DISTRICT_COUNTS for large states
        When: Checking CA and TX
        Then: CA >= 50, TX >= 35 (based on 2020 census)
        """
        # Then
        assert DISTRICT_COUNTS["CA"] >= 50  # CA has 52
        assert DISTRICT_COUNTS["TX"] >= 35  # TX has 38


class TestUSRegionRegistry:
    """Tests for the US region registry."""

    def test__given_us_registry__then_country_id_is_us(self):
        """Given: US region registry
        When: Checking country_id
        Then: Value is "us"
        """
        # Then
        assert us_region_registry.country_id == "us"

    def test__given_us_registry__then_has_national_region(self):
        """Given: US region registry
        When: Getting national region
        Then: Returns US with the certified national dataset path
        """
        # When
        national = us_region_registry.get_national()

        # Then
        assert national is not None
        assert national.code == "us"
        assert national.label == "United States"
        assert national.region_type == "national"
        assert national.dataset_path == (
            "hf://policyengine/populace-us/populace_us_2024.h5"
            "@populace-us-2024-cd-concept-budget-dbbdcec-512e-b2500-r2-"
            "20260627T022640Z"
        )

    def test__given_us_registry__then_has_51_states(self):
        """Given: US region registry
        When: Getting state regions
        Then: Contains 51 states (including DC)
        """
        # When
        states = us_region_registry.get_by_type("state")

        # Then
        assert len(states) == 51

    def test__given_california_region__then_has_correct_format(self):
        """Given: California state region
        When: Checking its properties
        Then: Has correct code, label, and metadata
        """
        # When
        ca = us_region_registry.get("state/ca")

        # Then
        assert ca is not None
        assert ca.label == "California"
        assert ca.region_type == "state"
        assert ca.parent_code == "us"
        assert ca.dataset_path == (
            "hf://policyengine/policyengine-us-data/states/CA.h5@1.115.5"
        )
        assert ca.state_code == "CA"
        assert ca.state_name == "California"
        assert not ca.requires_filter

    def test__given_us_registry__then_has_436_congressional_districts(self):
        """Given: US region registry
        When: Getting congressional district regions
        Then: Contains 436 districts
        """
        # When
        districts = us_region_registry.get_by_type("congressional_district")

        # Then
        assert len(districts) == 436

    def test__given_ca_first_district__then_has_correct_format(self):
        """Given: California's 1st congressional district
        When: Checking its properties
        Then: Has correct code, label, and metadata
        """
        # When
        ca01 = us_region_registry.get("congressional_district/CA-01")

        # Then
        assert ca01 is not None
        assert "California" in ca01.label
        assert "1st" in ca01.label.lower() or "1 " in ca01.label
        assert ca01.region_type == "congressional_district"
        assert ca01.parent_code == "state/ca"
        assert ca01.dataset_path is None
        assert ca01.state_code == "CA"
        assert not ca01.requires_filter

    def test__given_dc_district__then_is_at_large(self):
        """Given: DC's congressional district
        When: Checking its properties
        Then: Is labeled as at-large
        """
        # When
        dc_al = us_region_registry.get("congressional_district/DC-01")

        # Then
        assert dc_al is not None
        assert dc_al.label == "District of Columbia's at-large congressional district"
        assert dc_al.parent_code == "state/dc"

    def test__given_us_registry__then_has_places(self):
        """Given: US region registry
        When: Getting place regions
        Then: Contains 100+ large cities
        """
        # When
        places = us_region_registry.get_by_type("place")

        # Then
        assert len(places) >= 100

    def test__given_los_angeles_region__then_has_correct_format(self):
        """Given: Los Angeles place region
        When: Checking its properties
        Then: Requires filter with place_fips field
        """
        # When
        la = us_region_registry.get("place/CA-44000")

        # Then
        assert la is not None
        assert "Los Angeles" in la.label
        assert la.region_type == "place"
        assert la.parent_code == "state/ca"
        assert la.requires_filter
        assert la.scoping_strategy is not None
        assert la.scoping_strategy.variable_name == "place_fips"
        assert la.scoping_strategy.variable_value == "44000"
        assert la.state_code == "CA"
        assert la.dataset_path is None  # No dedicated dataset

    def test__given_california__then_children_include_districts_and_places(
        self,
    ):
        """Given: California state region
        When: Getting its children
        Then: Includes all 52 districts and 10+ places
        """
        # When
        ca_children = us_region_registry.get_children("state/ca")
        district_children = [
            c for c in ca_children if c.region_type == "congressional_district"
        ]
        place_children = [c for c in ca_children if c.region_type == "place"]

        # Then
        assert len(district_children) == DISTRICT_COUNTS["CA"]
        assert len(place_children) >= 10  # CA has many large cities

    def test__given_us_registry__then_dataset_regions_are_national_and_states(self):
        """Given: US region registry
        When: Getting regions with datasets
        Then: Current certified bundle has national and state datasets
        """
        # When
        dataset_regions = us_region_registry.get_dataset_regions()

        # Then
        assert len(dataset_regions) == 52
        assert {region.region_type for region in dataset_regions} == {
            "national",
            "state",
        }

    def test__given_certified_state_template__then_states_have_dataset_paths(
        self, monkeypatch
    ):
        """Given: US bundle manifest with a certified state template
        When: Building the region registry
        Then: State regions resolve to pinned state dataset artifacts
        """
        manifest = CountryReleaseManifest.model_validate(
            {
                "country_id": "us",
                "policyengine_version": "9.9.9",
                "model_package": {
                    "name": "policyengine-us",
                    "version": "1.723.0",
                },
                "data_package": {
                    "name": "populace-data",
                    "version": "0.1.0",
                    "repo_id": "policyengine/populace-us",
                    "repo_type": "dataset",
                    "release_manifest_revision": "populace-us-tag",
                },
                "default_dataset": "populace_us_2024",
                "datasets": {
                    "populace_us_2024": {
                        "path": "populace_us_2024.h5",
                        "repo_id": "policyengine/populace-us",
                        "revision": "populace-us-tag",
                    },
                    "states/CA": {
                        "path": "states/CA.h5",
                        "repo_id": "policyengine/policyengine-us-data",
                        "revision": "1.115.5",
                    },
                },
                "region_datasets": {
                    "national": {"path_template": "populace_us_2024.h5"},
                    "state": {"path_template": "states/{state_code}.h5"},
                },
            }
        )
        monkeypatch.setattr(
            "policyengine.provenance.manifest.get_release_manifest",
            lambda country_id: manifest,
        )

        registry = build_us_region_registry()
        ca = registry.get("state/ca")

        assert ca is not None
        assert ca.dataset_path == (
            "hf://policyengine/policyengine-us-data/states/CA.h5@1.115.5"
        )

    def test__given_us_registry__then_filter_regions_are_all_places(self):
        """Given: US region registry
        When: Getting regions requiring filter
        Then: All are place regions
        """
        # When
        filter_regions = us_region_registry.get_filter_regions()

        # Then
        assert all(r.region_type == "place" for r in filter_regions)

    def test__given_us_registry__then_total_exceeds_588(self):
        """Given: US region registry
        When: Counting all regions
        Then: Total is at least 488 US political regions + 100 places
        """
        # When
        total = len(us_region_registry)

        # Then
        assert total >= 488 + 100
