"""Tests for dataset filtering functionality.

Tests the _build_entity_relationships and _filter_dataset_by_household_variable
methods in both US and UK models.
"""

import pandas as pd
import pytest

from policyengine.core.simulation import Simulation


class TestSimulationFilterParameters:
    """Tests for Simulation filter_field and filter_value parameters."""

    def test__given_no_filter_params__then_simulation_has_none_values(self):
        """Given: Simulation created without filter parameters
        When: Accessing filter_field and filter_value
        Then: Both are None
        """
        # When
        simulation = Simulation()

        # Then
        assert simulation.filter_field is None
        assert simulation.filter_value is None

    def test__given_filter_params__then_simulation_stores_them(self):
        """Given: Simulation created with filter parameters
        When: Accessing filter_field and filter_value
        Then: Values are stored correctly
        """
        # When
        simulation = Simulation(
            filter_field="place_fips",
            filter_value="44000",
        )

        # Then
        assert simulation.filter_field == "place_fips"
        assert simulation.filter_value == "44000"


class TestUSBuildEntityRelationships:
    """Tests for US model _build_entity_relationships method."""

    def test__given_us_dataset__then_entity_relationships_has_all_columns(
        self, us_test_dataset
    ):
        """Given: US dataset with persons and entities
        When: Building entity relationships
        Then: DataFrame has all entity ID columns
        """
        # Given
        from policyengine.tax_benefit_models.us.model import (
            PolicyEngineUSLatest,
        )

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)

        # When
        entity_rel = model._build_entity_relationships(us_test_dataset)

        # Then
        expected_columns = {
            "person_id",
            "household_id",
            "tax_unit_id",
            "spm_unit_id",
            "family_id",
            "marital_unit_id",
        }
        assert set(entity_rel.columns) == expected_columns

    def test__given_us_dataset__then_entity_relationships_has_correct_row_count(
        self, us_test_dataset
    ):
        """Given: US dataset with 6 persons
        When: Building entity relationships
        Then: DataFrame has 6 rows (one per person)
        """
        # Given
        from policyengine.tax_benefit_models.us.model import (
            PolicyEngineUSLatest,
        )

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)

        # When
        entity_rel = model._build_entity_relationships(us_test_dataset)

        # Then
        assert len(entity_rel) == 6

    def test__given_us_dataset__then_entity_relationships_preserves_mappings(
        self, us_test_dataset
    ):
        """Given: US dataset where persons 1,2 belong to household 1
        When: Building entity relationships
        Then: Mappings are preserved correctly
        """
        # Given
        from policyengine.tax_benefit_models.us.model import (
            PolicyEngineUSLatest,
        )

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)

        # When
        entity_rel = model._build_entity_relationships(us_test_dataset)

        # Then
        person_1_row = entity_rel[entity_rel["person_id"] == 1].iloc[0]
        assert person_1_row["household_id"] == 1
        assert person_1_row["tax_unit_id"] == 1


class TestUSFilterDatasetByHouseholdVariable:
    """Tests for US model _filter_dataset_by_household_variable method."""

    def test__given_filter_by_place_fips__then_returns_matching_households(
        self, us_test_dataset
    ):
        """Given: US dataset with households in places 44000 and 57000
        When: Filtering by place_fips=44000
        Then: Returns only households in place 44000
        """
        # Given
        from policyengine.tax_benefit_models.us.model import (
            PolicyEngineUSLatest,
        )

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)

        # When
        filtered = model._filter_dataset_by_household_variable(
            us_test_dataset,
            variable_name="place_fips",
            variable_value="44000",
        )

        # Then
        household_df = pd.DataFrame(filtered.data.household)
        assert len(household_df) == 2
        assert all(household_df["place_fips"] == "44000")

    def test__given_filter_by_place_fips__then_preserves_related_persons(
        self, us_test_dataset
    ):
        """Given: US dataset with 4 persons in place 44000
        When: Filtering by place_fips=44000
        Then: Returns all 4 persons in matching households
        """
        # Given
        from policyengine.tax_benefit_models.us.model import (
            PolicyEngineUSLatest,
        )

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)

        # When
        filtered = model._filter_dataset_by_household_variable(
            us_test_dataset,
            variable_name="place_fips",
            variable_value="44000",
        )

        # Then
        person_df = pd.DataFrame(filtered.data.person)
        assert len(person_df) == 4
        assert set(person_df["person_id"]) == {1, 2, 3, 4}

    def test__given_filter_by_place_fips__then_preserves_related_entities(
        self, us_test_dataset
    ):
        """Given: US dataset with 2 tax units in place 44000
        When: Filtering by place_fips=44000
        Then: Returns all related entities (tax_unit, spm_unit, etc.)
        """
        # Given
        from policyengine.tax_benefit_models.us.model import (
            PolicyEngineUSLatest,
        )

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)

        # When
        filtered = model._filter_dataset_by_household_variable(
            us_test_dataset,
            variable_name="place_fips",
            variable_value="44000",
        )

        # Then
        assert len(pd.DataFrame(filtered.data.tax_unit)) == 2
        assert len(pd.DataFrame(filtered.data.spm_unit)) == 2
        assert len(pd.DataFrame(filtered.data.family)) == 2
        assert len(pd.DataFrame(filtered.data.marital_unit)) == 2

    def test__given_no_matching_households__then_raises_value_error(
        self, us_test_dataset
    ):
        """Given: US dataset with no households matching filter
        When: Filtering by place_fips=99999
        Then: Raises ValueError
        """
        # Given
        from policyengine.tax_benefit_models.us.model import (
            PolicyEngineUSLatest,
        )

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)

        # Then
        with pytest.raises(ValueError, match="No households found"):
            model._filter_dataset_by_household_variable(
                us_test_dataset,
                variable_name="place_fips",
                variable_value="99999",
            )

    def test__given_invalid_variable_name__then_raises_value_error(
        self, us_test_dataset
    ):
        """Given: US dataset
        When: Filtering by non-existent variable
        Then: Raises ValueError with helpful message
        """
        # Given
        from policyengine.tax_benefit_models.us.model import (
            PolicyEngineUSLatest,
        )

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)

        # Then
        with pytest.raises(ValueError, match="not found in household data"):
            model._filter_dataset_by_household_variable(
                us_test_dataset,
                variable_name="nonexistent_var",
                variable_value="value",
            )

    def test__given_filtered_dataset__then_has_updated_metadata(
        self, us_test_dataset
    ):
        """Given: US dataset
        When: Filtering by place_fips
        Then: Filtered dataset has updated id and description
        """
        # Given
        from policyengine.tax_benefit_models.us.model import (
            PolicyEngineUSLatest,
        )

        model = PolicyEngineUSLatest.__new__(PolicyEngineUSLatest)

        # When
        filtered = model._filter_dataset_by_household_variable(
            us_test_dataset,
            variable_name="place_fips",
            variable_value="44000",
        )

        # Then
        assert "filtered" in filtered.id
        assert "place_fips=44000" in filtered.description


class TestUKBuildEntityRelationships:
    """Tests for UK model _build_entity_relationships method."""

    def test__given_uk_dataset__then_entity_relationships_has_all_columns(
        self, uk_test_dataset
    ):
        """Given: UK dataset with persons and entities
        When: Building entity relationships
        Then: DataFrame has all entity ID columns
        """
        # Given
        from policyengine.tax_benefit_models.uk.model import (
            PolicyEngineUKLatest,
        )

        model = PolicyEngineUKLatest.__new__(PolicyEngineUKLatest)

        # When
        entity_rel = model._build_entity_relationships(uk_test_dataset)

        # Then
        expected_columns = {"person_id", "benunit_id", "household_id"}
        assert set(entity_rel.columns) == expected_columns

    def test__given_uk_dataset__then_entity_relationships_has_correct_row_count(
        self, uk_test_dataset
    ):
        """Given: UK dataset with 6 persons
        When: Building entity relationships
        Then: DataFrame has 6 rows (one per person)
        """
        # Given
        from policyengine.tax_benefit_models.uk.model import (
            PolicyEngineUKLatest,
        )

        model = PolicyEngineUKLatest.__new__(PolicyEngineUKLatest)

        # When
        entity_rel = model._build_entity_relationships(uk_test_dataset)

        # Then
        assert len(entity_rel) == 6


class TestUKFilterDatasetByHouseholdVariable:
    """Tests for UK model _filter_dataset_by_household_variable method."""

    def test__given_filter_by_country__then_returns_matching_households(
        self, uk_test_dataset
    ):
        """Given: UK dataset with households in England and Scotland
        When: Filtering by country=ENGLAND
        Then: Returns only households in England
        """
        # Given
        from policyengine.tax_benefit_models.uk.model import (
            PolicyEngineUKLatest,
        )

        model = PolicyEngineUKLatest.__new__(PolicyEngineUKLatest)

        # When
        filtered = model._filter_dataset_by_household_variable(
            uk_test_dataset,
            variable_name="country",
            variable_value="ENGLAND",
        )

        # Then
        household_df = pd.DataFrame(filtered.data.household)
        assert len(household_df) == 2
        assert all(household_df["country"] == "ENGLAND")

    def test__given_filter_by_country__then_preserves_related_persons(
        self, uk_test_dataset
    ):
        """Given: UK dataset with 4 persons in England
        When: Filtering by country=ENGLAND
        Then: Returns all 4 persons in matching households
        """
        # Given
        from policyengine.tax_benefit_models.uk.model import (
            PolicyEngineUKLatest,
        )

        model = PolicyEngineUKLatest.__new__(PolicyEngineUKLatest)

        # When
        filtered = model._filter_dataset_by_household_variable(
            uk_test_dataset,
            variable_name="country",
            variable_value="ENGLAND",
        )

        # Then
        person_df = pd.DataFrame(filtered.data.person)
        assert len(person_df) == 4
        assert set(person_df["person_id"]) == {1, 2, 3, 4}

    def test__given_filter_by_country__then_preserves_related_benunits(
        self, uk_test_dataset
    ):
        """Given: UK dataset with 2 benunits in England
        When: Filtering by country=ENGLAND
        Then: Returns all related benunits
        """
        # Given
        from policyengine.tax_benefit_models.uk.model import (
            PolicyEngineUKLatest,
        )

        model = PolicyEngineUKLatest.__new__(PolicyEngineUKLatest)

        # When
        filtered = model._filter_dataset_by_household_variable(
            uk_test_dataset,
            variable_name="country",
            variable_value="ENGLAND",
        )

        # Then
        assert len(pd.DataFrame(filtered.data.benunit)) == 2

    def test__given_no_matching_households__then_raises_value_error(
        self, uk_test_dataset
    ):
        """Given: UK dataset with no households matching filter
        When: Filtering by country=WALES
        Then: Raises ValueError
        """
        # Given
        from policyengine.tax_benefit_models.uk.model import (
            PolicyEngineUKLatest,
        )

        model = PolicyEngineUKLatest.__new__(PolicyEngineUKLatest)

        # Then
        with pytest.raises(ValueError, match="No households found"):
            model._filter_dataset_by_household_variable(
                uk_test_dataset,
                variable_name="country",
                variable_value="WALES",
            )

    def test__given_filtered_dataset__then_has_updated_metadata(
        self, uk_test_dataset
    ):
        """Given: UK dataset
        When: Filtering by country
        Then: Filtered dataset has updated id and description
        """
        # Given
        from policyengine.tax_benefit_models.uk.model import (
            PolicyEngineUKLatest,
        )

        model = PolicyEngineUKLatest.__new__(PolicyEngineUKLatest)

        # When
        filtered = model._filter_dataset_by_household_variable(
            uk_test_dataset,
            variable_name="country",
            variable_value="ENGLAND",
        )

        # Then
        assert "filtered" in filtered.id
        assert "country=ENGLAND" in filtered.description
