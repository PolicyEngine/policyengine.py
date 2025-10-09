"""
Unit tests for AggregateUtils cross-entity mapping functionality.

These tests verify that variables can be correctly mapped between entities
(person <-> household, person <-> tax_unit, etc.) while preserving weights.
"""

import pytest
import pandas as pd
from microdf import MicroDataFrame
from policyengine.models.aggregate import AggregateUtils, AggregateType


class MockSimulation:
    """Mock simulation for testing."""
    def __init__(self, result):
        self.result = result


@pytest.fixture
def sample_person_household_tables():
    """
    Create sample tables with person and household entities.

    Structure:
    - 2 households (ids 0, 1)
    - 4 persons (ids 0, 1, 2, 3)
      - Persons 0, 1 belong to household 0
      - Persons 2, 3 belong to household 1
    """
    person_table = pd.DataFrame({
        'person_id': [0, 1, 2, 3],
        'person_household_id': [0, 0, 1, 1],
        'person_weight': [1.0, 1.0, 1.0, 1.0],
        'age': [30, 5, 45, 40],
        'employment_income': [50000, 0, 60000, 55000],
    })

    household_table = pd.DataFrame({
        'household_id': [0, 1],
        'household_weight': [1.0, 1.0],
        'household_net_income': [50000, 115000],
        'is_in_poverty': [1, 0],  # household 0 is in poverty, household 1 is not
    })

    return {
        'person': person_table,
        'household': household_table
    }


@pytest.fixture
def weighted_person_household_tables():
    """
    Create sample tables with different weights to test weight preservation.

    Structure:
    - 2 households with different weights
    - 4 persons with weights matching their households
    """
    person_table = pd.DataFrame({
        'person_id': [0, 1, 2, 3],
        'person_household_id': [0, 0, 1, 1],
        'person_weight': [100.0, 100.0, 200.0, 200.0],  # Different weights
        'age': [30, 5, 45, 40],
        'employment_income': [50000, 0, 60000, 55000],
    })

    household_table = pd.DataFrame({
        'household_id': [0, 1],
        'household_weight': [100.0, 200.0],  # Different weights
        'household_net_income': [50000, 115000],
        'is_in_poverty': [1, 0],
    })

    return {
        'person': person_table,
        'household': household_table
    }


class TestPrepareTablesWithWeights:
    """Test that prepare_tables correctly creates MicroDataFrames with weights."""

    def test_prepare_tables_creates_microdataframes(self, sample_person_household_tables):
        """Test that tables with weight columns become MicroDataFrames."""
        mock_sim = MockSimulation(sample_person_household_tables)
        tables = AggregateUtils.prepare_tables(mock_sim)

        # Both tables should be MicroDataFrames
        assert isinstance(tables['person'], MicroDataFrame)
        assert isinstance(tables['household'], MicroDataFrame)

        # Check that weights are set correctly
        assert tables['person'].weights_col == 'person_weight'
        assert tables['household'].weights_col == 'household_weight'

    def test_prepare_tables_without_weights(self):
        """Test that tables without weight columns remain regular DataFrames."""
        tables_without_weights = {
            'person': pd.DataFrame({
                'person_id': [0, 1],
                'age': [30, 40]
            })
        }
        mock_sim = MockSimulation(tables_without_weights)
        tables = AggregateUtils.prepare_tables(mock_sim)

        # Should be regular DataFrame, not MicroDataFrame
        assert isinstance(tables['person'], pd.DataFrame)
        assert not isinstance(tables['person'], MicroDataFrame)


class TestInferEntity:
    """Test entity inference from variable names."""

    def test_infer_entity_person_variable(self, sample_person_household_tables):
        """Test inferring entity for a person-level variable."""
        entity = AggregateUtils.infer_entity('age', sample_person_household_tables)
        assert entity == 'person'

    def test_infer_entity_household_variable(self, sample_person_household_tables):
        """Test inferring entity for a household-level variable."""
        entity = AggregateUtils.infer_entity('is_in_poverty', sample_person_household_tables)
        assert entity == 'household'

    def test_infer_entity_nonexistent_variable(self, sample_person_household_tables):
        """Test that nonexistent variable raises ValueError."""
        with pytest.raises(ValueError, match="Variable nonexistent not found"):
            AggregateUtils.infer_entity('nonexistent', sample_person_household_tables)


class TestMapVariableAcrossEntities:
    """Test cross-entity variable mapping."""

    def test_map_household_to_person(self, sample_person_household_tables):
        """
        Test mapping a household variable to person level.
        Each person should get their household's value.
        """
        mapped = AggregateUtils.map_variable_across_entities(
            sample_person_household_tables['household'],
            'is_in_poverty',
            'household',
            'person',
            sample_person_household_tables
        )

        # Persons 0, 1 belong to household 0 (in poverty)
        assert mapped.iloc[0] == 1
        assert mapped.iloc[1] == 1

        # Persons 2, 3 belong to household 1 (not in poverty)
        assert mapped.iloc[2] == 0
        assert mapped.iloc[3] == 0

    def test_map_person_to_household(self, sample_person_household_tables):
        """
        Test mapping a person variable to household level.
        Should sum persons' values within each household.
        """
        mapped = AggregateUtils.map_variable_across_entities(
            sample_person_household_tables['person'],
            'employment_income',
            'person',
            'household',
            sample_person_household_tables
        )

        # Household 0: persons 0 (50000) + 1 (0) = 50000
        assert mapped.iloc[0] == 50000

        # Household 1: persons 2 (60000) + 3 (55000) = 115000
        assert mapped.iloc[1] == 115000

    def test_map_same_entity(self, sample_person_household_tables):
        """Test that mapping to same entity returns the variable as-is."""
        mapped = AggregateUtils.map_variable_across_entities(
            sample_person_household_tables['person'],
            'age',
            'person',
            'person',
            sample_person_household_tables
        )

        pd.testing.assert_series_equal(
            mapped,
            sample_person_household_tables['person']['age'],
            check_names=False
        )

    def test_map_preserves_length(self, sample_person_household_tables):
        """Test that mapped series has correct length for target entity."""
        # Household to person: should have 4 entries (4 persons)
        mapped_h_to_p = AggregateUtils.map_variable_across_entities(
            sample_person_household_tables['household'],
            'is_in_poverty',
            'household',
            'person',
            sample_person_household_tables
        )
        assert len(mapped_h_to_p) == 4

        # Person to household: should have 2 entries (2 households)
        mapped_p_to_h = AggregateUtils.map_variable_across_entities(
            sample_person_household_tables['person'],
            'employment_income',
            'person',
            'household',
            sample_person_household_tables
        )
        assert len(mapped_p_to_h) == 2


class TestComputeAggregate:
    """Test aggregate computation functions."""

    def test_sum_simple(self):
        """Test simple sum aggregation."""
        series = pd.Series([10, 20, 30, 40])
        result = AggregateUtils.compute_aggregate(series, AggregateType.SUM)
        assert result == 100.0

    def test_sum_weighted(self):
        """Test weighted sum using MicroDataFrame."""
        df = pd.DataFrame({
            'value': [10, 20, 30],
            'weight': [1.0, 2.0, 1.0]
        })
        mdf = MicroDataFrame(df, weights='weight')
        result = AggregateUtils.compute_aggregate(mdf['value'], AggregateType.SUM)

        # Weighted sum: 10*1 + 20*2 + 30*1 = 80
        assert result == 80.0

    def test_mean_simple(self):
        """Test simple mean aggregation."""
        series = pd.Series([10, 20, 30, 40])
        result = AggregateUtils.compute_aggregate(series, AggregateType.MEAN)
        assert result == 25.0

    def test_mean_weighted(self):
        """Test weighted mean using MicroDataFrame."""
        df = pd.DataFrame({
            'value': [10, 20, 30],
            'weight': [1.0, 2.0, 1.0]
        })
        mdf = MicroDataFrame(df, weights='weight')
        result = AggregateUtils.compute_aggregate(mdf['value'], AggregateType.MEAN)

        # Weighted mean: (10*1 + 20*2 + 30*1) / (1+2+1) = 80/4 = 20
        assert result == 20.0

    def test_median_simple(self):
        """Test simple median aggregation."""
        series = pd.Series([10, 20, 30, 40, 50])
        result = AggregateUtils.compute_aggregate(series, AggregateType.MEDIAN)
        assert result == 30.0

    def test_count(self):
        """Test count aggregation (counts all entries)."""
        series = pd.Series([0, 10, 0, 20, 30, 0])
        result = AggregateUtils.compute_aggregate(series, AggregateType.COUNT)
        # COUNT returns the total number of entries, not just non-zero
        assert result == 6.0

        # To count only non-zero values, filter first then count
        non_zero = series[series > 0]
        result_filtered = AggregateUtils.compute_aggregate(non_zero, AggregateType.COUNT)
        assert result_filtered == 3.0

    def test_empty_series(self):
        """Test that empty series returns 0."""
        series = pd.Series([])
        for agg_type in [AggregateType.SUM, AggregateType.MEAN, AggregateType.MEDIAN, AggregateType.COUNT]:
            result = AggregateUtils.compute_aggregate(series, agg_type)
            assert result == 0.0


class TestPovertyRateScenario:
    """
    Test the specific poverty rate scenario that was giving 1% result.

    This tests the complete flow: prepare tables, map variables, apply filters,
    and compute aggregates with weights.
    """

    def test_poverty_rate_with_household_filter_person_aggregation(self, weighted_person_household_tables):
        """
        Test computing poverty rate at person level with household-level filter.

        Scenario:
        - Filter: households in poverty (is_in_poverty == 1)
        - Variable: count of persons
        - This should count persons in poor households
        """
        # Prepare tables as they would be in production
        mock_sim = MockSimulation(weighted_person_household_tables)
        tables = AggregateUtils.prepare_tables(mock_sim)

        # Step 1: Get household filter variable and map to person level
        household_df = tables['household']
        filter_variable = 'is_in_poverty'

        # Map household filter to person level
        mapped_filter = AggregateUtils.map_variable_across_entities(
            household_df,
            filter_variable,
            'household',
            'person',
            tables
        )

        # Build filter mask at person level
        person_table = tables['person']
        mask = mapped_filter == 1

        # Step 2: Filter the person table
        filtered_table = person_table[mask]

        # Step 3: Count persons (weighted)
        # Persons 0 and 1 are in poor households, each with weight 100
        count = AggregateUtils.compute_aggregate(
            filtered_table['person_id'],
            AggregateType.COUNT
        )

        # Should count 2 persons (weighted count with MicroDataFrame should be 200)
        # But COUNT just counts entries > 0, not weighted
        assert count == 2.0

        # For weighted sum of persons in poverty:
        sum_weights = AggregateUtils.compute_aggregate(
            filtered_table['person_weight'],
            AggregateType.SUM
        )
        assert sum_weights == 200.0  # 100 + 100

    def test_poverty_rate_household_level(self, weighted_person_household_tables):
        """
        Test computing poverty rate at household level.

        This is more straightforward - just filter households and count.
        """
        mock_sim = MockSimulation(weighted_person_household_tables)
        tables = AggregateUtils.prepare_tables(mock_sim)

        household_table = tables['household']

        # Filter to households in poverty
        mask = household_table['is_in_poverty'] == 1
        filtered = household_table[mask]

        # Count households
        count = AggregateUtils.compute_aggregate(
            filtered['is_in_poverty'],
            AggregateType.COUNT
        )
        assert count == 1.0  # Only 1 household in poverty

        # Weighted sum
        sum_weights = AggregateUtils.compute_aggregate(
            filtered['household_weight'],
            AggregateType.SUM
        )
        assert sum_weights == 100.0  # Weight of household 0

    def test_mean_income_in_poor_households(self, weighted_person_household_tables):
        """
        Test computing mean income for persons in poor households.

        This tests the complete cross-entity flow with weights.
        """
        mock_sim = MockSimulation(weighted_person_household_tables)
        tables = AggregateUtils.prepare_tables(mock_sim)

        # Step 1: Map household poverty status to person level
        mapped_poverty = AggregateUtils.map_variable_across_entities(
            tables['household'],
            'is_in_poverty',
            'household',
            'person',
            tables
        )

        # Step 2: Filter persons in poor households
        person_table = tables['person']
        mask = mapped_poverty == 1
        filtered_table = person_table[mask]

        # Step 3: Compute mean employment income
        mean_income = AggregateUtils.compute_aggregate(
            filtered_table['employment_income'],
            AggregateType.MEAN
        )

        # Persons 0 (income 50000, weight 100) and 1 (income 0, weight 100)
        # Weighted mean: (50000*100 + 0*100) / (100+100) = 25000
        assert mean_income == 25000.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_link_column(self):
        """Test error when link column is missing."""
        tables = {
            'person': pd.DataFrame({'age': [30, 40]}),
            'household': pd.DataFrame({'income': [50000, 60000]})
        }

        with pytest.raises(ValueError, match="Link column .* not found"):
            AggregateUtils.map_variable_across_entities(
                tables['household'],
                'income',
                'household',
                'person',
                tables
            )

    def test_unknown_aggregate_function(self):
        """Test error with unknown aggregate function."""
        series = pd.Series([10, 20, 30])

        with pytest.raises(ValueError, match="Unknown aggregate function"):
            AggregateUtils.compute_aggregate(series, 'unknown_function')

    def test_map_with_missing_entity(self):
        """Test error when entity doesn't exist in tables."""
        tables = {
            'person': pd.DataFrame({'age': [30, 40]})
        }

        with pytest.raises(ValueError, match="No known link"):
            AggregateUtils.map_variable_across_entities(
                tables['person'],
                'age',
                'person',
                'nonexistent_entity',
                tables
            )
