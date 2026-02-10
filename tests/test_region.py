"""Tests for Region and RegionRegistry classes."""

import pytest

from policyengine.core.region import Region, RegionRegistry

from tests.fixtures.region_fixtures import (
    FILTER_REGION,
    REGION_WITH_DATASET,
    SIMPLE_REGION,
    create_sample_us_registry,
    create_state_region,
    sample_registry,
)


class TestRegion:
    """Tests for the Region class."""

    def test__given_required_fields__then_region_created(self):
        """Given: Required fields (code, label, region_type)
        When: Creating a Region
        Then: Region is created with those values
        """
        # Given
        code = "state/ca"
        label = "California"
        region_type = "state"

        # When
        region = Region(code=code, label=label, region_type=region_type)

        # Then
        assert region.code == code
        assert region.label == label
        assert region.region_type == region_type

    def test__given_dataset_path__then_region_has_dedicated_dataset(self):
        """Given: Region with dataset_path specified
        When: Creating the Region
        Then: Region has dataset_path and requires_filter is False
        """
        # Given (using fixture)
        region = REGION_WITH_DATASET

        # Then
        assert region.dataset_path == "gs://policyengine-us-data/states/CA.h5"
        assert region.parent_code == "us"
        assert region.state_code == "CA"
        assert not region.requires_filter

    def test__given_filter_configuration__then_region_requires_filter(self):
        """Given: Region with requires_filter=True and filter fields
        When: Creating the Region
        Then: Region is configured for filtering from parent
        """
        # Given (using fixture)
        region = FILTER_REGION

        # Then
        assert region.requires_filter is True
        assert region.filter_field == "place_fips"
        assert region.filter_value == "57000"

    def test__given_same_codes__then_regions_are_equal(self):
        """Given: Two regions with the same code
        When: Comparing them
        Then: They are equal regardless of other fields
        """
        # Given
        region1 = Region(code="state/ca", label="California", region_type="state")
        region2 = Region(code="state/ca", label="California (different)", region_type="state")
        region3 = Region(code="state/ny", label="New York", region_type="state")

        # Then
        assert region1 == region2
        assert region1 != region3

    def test__given_region__then_can_use_as_dict_key_or_in_set(self):
        """Given: Multiple regions
        When: Using them in sets or as dict keys
        Then: Regions with same code are deduplicated
        """
        # Given
        region1 = Region(code="state/ca", label="California", region_type="state")
        region2 = Region(code="state/ca", label="California (duplicate)", region_type="state")
        region3 = Region(code="state/ny", label="New York", region_type="state")

        # When
        region_set = {region1, region2, region3}
        region_dict = {region1: "first", region3: "third"}

        # Then
        assert len(region_set) == 2  # region1 and region2 are same
        assert region_dict[region2] == "first"  # region2 == region1


class TestRegionRegistry:
    """Tests for the RegionRegistry class."""

    def test__given_registry_with_regions__then_length_is_correct(self, sample_registry):
        """Given: Registry with 4 regions
        When: Checking length
        Then: Length is 4
        """
        # Then
        assert len(sample_registry) == 4

    def test__given_registry__then_can_iterate_over_regions(self, sample_registry):
        """Given: Registry with regions
        When: Iterating
        Then: All region codes are accessible
        """
        # When
        codes = [r.code for r in sample_registry]

        # Then
        assert "us" in codes
        assert "state/ca" in codes
        assert "place/CA-44000" in codes

    def test__given_existing_code__then_code_is_in_registry(self, sample_registry):
        """Given: Registry with state/ca
        When: Checking if code exists
        Then: Returns True for existing, False for missing
        """
        # Then
        assert "state/ca" in sample_registry
        assert "state/tx" not in sample_registry

    def test__given_valid_code__then_get_returns_region(self, sample_registry):
        """Given: Registry with state/ca
        When: Getting by code
        Then: Returns Region for existing, None for missing
        """
        # When
        ca = sample_registry.get("state/ca")
        missing = sample_registry.get("state/tx")

        # Then
        assert ca is not None
        assert ca.label == "California"
        assert missing is None

    def test__given_type__then_get_by_type_returns_matching_regions(self, sample_registry):
        """Given: Registry with 2 states and 1 place
        When: Getting by type
        Then: Returns correct regions for each type
        """
        # When
        states = sample_registry.get_by_type("state")
        places = sample_registry.get_by_type("place")
        counties = sample_registry.get_by_type("county")

        # Then
        assert len(states) == 2
        assert all(r.region_type == "state" for r in states)
        assert len(places) == 1
        assert counties == []

    def test__given_registry__then_get_national_returns_national_region(self, sample_registry):
        """Given: Registry with national region
        When: Getting national
        Then: Returns the national region
        """
        # When
        national = sample_registry.get_national()

        # Then
        assert national is not None
        assert national.code == "us"
        assert national.region_type == "national"

    def test__given_parent_code__then_get_children_returns_child_regions(self, sample_registry):
        """Given: Registry with states under "us"
        When: Getting children of "us"
        Then: Returns state regions
        """
        # When
        us_children = sample_registry.get_children("us")
        ca_children = sample_registry.get_children("state/ca")

        # Then
        assert len(us_children) == 2  # CA and NY states
        assert len(ca_children) == 1  # Los Angeles place
        assert ca_children[0].code == "place/CA-44000"

    def test__given_registry__then_get_dataset_regions_returns_regions_with_datasets(
        self, sample_registry
    ):
        """Given: Registry with 3 dataset regions (US, CA, NY)
        When: Getting dataset regions
        Then: Returns only regions with dataset_path and no filter
        """
        # When
        dataset_regions = sample_registry.get_dataset_regions()

        # Then
        assert len(dataset_regions) == 3  # us, ca, ny
        assert all(r.dataset_path is not None for r in dataset_regions)
        assert all(not r.requires_filter for r in dataset_regions)

    def test__given_registry__then_get_filter_regions_returns_regions_requiring_filter(
        self, sample_registry
    ):
        """Given: Registry with 1 filter region (Los Angeles)
        When: Getting filter regions
        Then: Returns only regions with requires_filter=True
        """
        # When
        filter_regions = sample_registry.get_filter_regions()

        # Then
        assert len(filter_regions) == 1
        assert filter_regions[0].code == "place/CA-44000"

    def test__given_registry__then_can_add_region_dynamically(self, sample_registry):
        """Given: Registry with 4 regions
        When: Adding a new region
        Then: Registry contains 5 regions and new region is indexed
        """
        # Given
        new_region = create_state_region("TX", "Texas")

        # When
        sample_registry.add_region(new_region)

        # Then
        assert len(sample_registry) == 5
        assert "state/tx" in sample_registry
        assert sample_registry.get("state/tx").label == "Texas"
        assert len(sample_registry.get_by_type("state")) == 3

    def test__given_empty_registry__then_lookups_return_empty_results(self):
        """Given: Empty registry
        When: Performing lookups
        Then: Returns empty results without errors
        """
        # Given
        registry = RegionRegistry(country_id="test", regions=[])

        # Then
        assert len(registry) == 0
        assert registry.get("anything") is None
        assert registry.get_national() is None
        assert registry.get_by_type("state") == []
