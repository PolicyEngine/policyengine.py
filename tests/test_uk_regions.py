"""Tests for UK region definitions."""

from policyengine.countries.uk.regions import (
    UK_COUNTRIES,
    UK_DATA_BUCKET,
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
        assert national.dataset_path == f"{UK_DATA_BUCKET}/enhanced_frs_2023_24.h5"
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
        Then: Filters from national with country field
        """
        # When
        england = uk_region_registry.get("country/england")

        # Then
        assert england is not None
        assert england.label == "England"
        assert england.region_type == "country"
        assert england.parent_code == "uk"
        assert england.requires_filter
        assert england.filter_field == "country"
        assert england.filter_value == "ENGLAND"
        assert england.dataset_path is None

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
        assert scotland.filter_value == "SCOTLAND"

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
        assert wales.filter_value == "WALES"

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
        assert ni.filter_value == "NORTHERN_IRELAND"

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

    def test__given_builder_without_optional_regions__then_returns_5_regions(self):
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
