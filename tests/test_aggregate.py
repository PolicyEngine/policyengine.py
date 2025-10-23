"""
Tests for the clean aggregate implementation.

Tests cover:
- Basic aggregations (sum, mean, median, count)
- Filtering (value, range, quantile)
- Cross-entity queries
- Batching efficiency
- Edge cases
"""

import pytest
import pandas as pd

from policyengine.models.aggregate import Aggregate, AggregateType


class MockSimulation:
    """Mock simulation for testing."""

    def __init__(self, result, year=2024):
        self.result = result
        self.dataset = MockDataset(year)


class MockDataset:
    def __init__(self, year):
        self.year = year


@pytest.fixture
def sample_tables():
    """Create sample person/household tables for testing."""
    person = pd.DataFrame({
        'person_id': [0, 1, 2, 3],
        'person_household_id': [0, 0, 1, 1],
        'person_weight': [100.0, 100.0, 200.0, 200.0],
        'age': [30, 5, 45, 40],
        'employment_income': [50000, 0, 60000, 55000],
    })

    household = pd.DataFrame({
        'household_id': [0, 1],
        'household_weight': [100.0, 200.0],
        'household_net_income': [50000, 115000],
        'is_in_poverty': [1, 0],
    })

    return {'person': person, 'household': household}


class TestBasicAggregations:
    """Test basic aggregation functions."""

    def test_sum(self, sample_tables):
        """Test sum aggregation."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='employment_income',
            aggregate_function=AggregateType.SUM,
            entity='person'
        )
        results = Aggregate.run([agg])
        # Weighted sum: 50000*100 + 0*100 + 60000*200 + 55000*200 = 28,000,000
        assert results[0].value == 28_000_000.0

    def test_mean(self, sample_tables):
        """Test mean aggregation."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='age',
            aggregate_function=AggregateType.MEAN,
            entity='person'
        )
        results = Aggregate.run([agg])
        # Weighted mean: (30*100 + 5*100 + 45*200 + 40*200) / 600 = 34.17
        assert round(results[0].value, 2) == 34.17

    def test_count(self, sample_tables):
        """Test count aggregation."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person'
        )
        results = Aggregate.run([agg])
        # Weighted count: sum of person weights = 100 + 100 + 200 + 200 = 600
        assert results[0].value == 600.0

    def test_median(self, sample_tables):
        """Test median aggregation."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='age',
            aggregate_function=AggregateType.MEDIAN,
            entity='person'
        )
        results = Aggregate.run([agg])
        assert results[0].value > 0

    def test_entity_inference(self, sample_tables):
        """Test that entity is inferred correctly."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='employment_income',
            aggregate_function=AggregateType.SUM
            # entity not specified
        )
        results = Aggregate.run([agg])
        assert results[0].entity == 'person'
        assert results[0].value == 28_000_000.0


class TestFiltering:
    """Test filtering functionality."""

    def test_value_filter(self, sample_tables):
        """Test filtering with exact value match."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person',
            filter_variable_name='age',
            filter_variable_value=30
        )
        results = Aggregate.run([agg])
        # Weighted count: person 0 has age 30 and weight 100
        assert results[0].value == 100.0

    def test_range_filter_leq(self, sample_tables):
        """Test filtering with <= operator."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='employment_income',
            aggregate_function=AggregateType.SUM,
            entity='person',
            filter_variable_name='age',
            filter_variable_leq=35
        )
        results = Aggregate.run([agg])
        # Persons with age <= 35: person 0 (age 30) and person 1 (age 5)
        # Weighted sum: 50000*100 + 0*100 = 5,000,000
        assert results[0].value == 5_000_000.0

    def test_range_filter_geq(self, sample_tables):
        """Test filtering with >= operator."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='employment_income',
            aggregate_function=AggregateType.SUM,
            entity='person',
            filter_variable_name='age',
            filter_variable_geq=40
        )
        results = Aggregate.run([agg])
        # Persons with age >= 40: person 2 (age 45) and person 3 (age 40)
        # Weighted sum: 60000*200 + 55000*200 = 23,000,000
        assert results[0].value == 23_000_000.0

    def test_combined_range_filters(self, sample_tables):
        """Test combining leq and geq filters."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='employment_income',
            aggregate_function=AggregateType.SUM,
            entity='person',
            filter_variable_name='age',
            filter_variable_geq=18,
            filter_variable_leq=35
        )
        results = Aggregate.run([agg])
        # Person 0: age 30, income 50000, weight 100
        assert results[0].value == 5_000_000.0

    def test_quantile_filter_leq(self, sample_tables):
        """Test filtering with quantile_leq."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person',
            filter_variable_name='age',
            filter_variable_quantile_leq=0.5
        )
        results = Aggregate.run([agg])
        # Weighted median age is 40, so includes ages <= 40: persons 0, 1, 3
        # Weighted count: 100 + 100 + 200 = 400
        assert results[0].value == 400.0

    def test_quantile_filter_geq(self, sample_tables):
        """Test filtering with quantile_geq."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person',
            filter_variable_name='age',
            filter_variable_quantile_geq=0.5
        )
        results = Aggregate.run([agg])
        # Weighted median age is 40, so includes ages >= 40: persons 2, 3
        # Weighted count: 200 + 200 = 400
        assert results[0].value == 400.0


class TestCrossEntity:
    """Test cross-entity queries."""

    def test_household_filter_on_person_aggregation(self, sample_tables):
        """Test filtering persons by household variable."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person',
            filter_variable_name='is_in_poverty',
            filter_variable_value=1
        )
        results = Aggregate.run([agg])
        # Persons in poor households (household 0): persons 0 and 1
        # Weighted count: 100 + 100 = 200
        assert results[0].value == 200.0

    def test_person_to_household_aggregation(self, sample_tables):
        """Test aggregating person variable at household level."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='employment_income',
            aggregate_function=AggregateType.SUM,
            entity='household'
        )
        results = Aggregate.run([agg])
        # Employment income summed to household level with household weights:
        # Household 0: (50000 + 0) * 100 = 5,000,000
        # Household 1: (60000 + 55000) * 200 = 23,000,000
        # Total weighted sum: 28,000,000
        assert results[0].value == 28_000_000.0

    def test_poverty_rate_calculation(self, sample_tables):
        """Test calculating poverty rate."""
        sim = MockSimulation(sample_tables)

        # Count persons in poverty
        poor = Aggregate(
            simulation=sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person',
            filter_variable_name='is_in_poverty',
            filter_variable_value=1
        )

        # Total persons
        total = Aggregate(
            simulation=sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person'
        )

        results = Aggregate.run([poor, total])
        poverty_rate = results[0].value / results[1].value
        # Weighted: 200 poor / 600 total = 1/3
        assert round(poverty_rate, 3) == 0.333

    def test_mean_income_for_poor(self, sample_tables):
        """Test mean income for persons in poor households."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='employment_income',
            aggregate_function=AggregateType.MEAN,
            entity='person',
            filter_variable_name='is_in_poverty',
            filter_variable_value=1
        )
        results = Aggregate.run([agg])
        # Persons in poverty: person 0 (income 50000, weight 100), person 1 (income 0, weight 100)
        # Weighted mean: (50000*100 + 0*100) / 200 = 25000
        assert results[0].value == 25000.0


class TestBatching:
    """Test batch processing efficiency."""

    def test_batch_same_simulation(self, sample_tables):
        """Test that aggregates with same simulation are batched."""
        sim = MockSimulation(sample_tables)

        aggregates = [
            Aggregate(
                simulation=sim,
                variable_name='employment_income',
                aggregate_function=AggregateType.SUM,
                entity='person'
            ),
            Aggregate(
                simulation=sim,
                variable_name='age',
                aggregate_function=AggregateType.MEAN,
                entity='person'
            ),
            Aggregate(
                simulation=sim,
                variable_name='person_id',
                aggregate_function=AggregateType.COUNT,
                entity='person'
            ),
        ]

        results = Aggregate.run(aggregates)
        assert len(results) == 3
        assert results[0].value == 28_000_000.0
        assert round(results[1].value, 2) == 34.17
        assert results[2].value == 600.0  # Weighted count

    def test_batch_different_filters(self, sample_tables):
        """Test batching aggregates with different filters."""
        sim = MockSimulation(sample_tables)

        aggregates = [
            Aggregate(
                simulation=sim,
                variable_name='person_id',
                aggregate_function=AggregateType.COUNT,
                entity='person',
                filter_variable_name='age',
                filter_variable_leq=17
            ),
            Aggregate(
                simulation=sim,
                variable_name='person_id',
                aggregate_function=AggregateType.COUNT,
                entity='person',
                filter_variable_name='age',
                filter_variable_geq=18
            ),
        ]

        results = Aggregate.run(aggregates)
        assert len(results) == 2
        assert results[0].value == 100.0  # Children: person 1 weight 100
        assert results[1].value == 500.0  # Adults: persons 0,2,3 weights 100+200+200


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_result(self, sample_tables):
        """Test filtering that results in empty set."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person',
            filter_variable_name='age',
            filter_variable_value=999
        )
        results = Aggregate.run([agg])
        assert results[0].value == 0.0

    def test_weight_column_sum(self, sample_tables):
        """Test that weight columns avoid double-weighting."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='person_weight',
            aggregate_function=AggregateType.SUM,
            entity='person'
        )
        results = Aggregate.run([agg])
        # Simple sum (not weighted): 100 + 100 + 200 + 200 = 600
        assert results[0].value == 600.0

    def test_missing_variable(self, sample_tables):
        """Test error when variable doesn't exist."""
        sim = MockSimulation(sample_tables)
        agg = Aggregate(
            simulation=sim,
            variable_name='nonexistent',
            aggregate_function=AggregateType.SUM
        )
        with pytest.raises(ValueError, match='not found'):
            Aggregate.run([agg])


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_poverty_by_age_group(self, sample_tables):
        """Test poverty analysis by age group."""
        sim = MockSimulation(sample_tables)

        # Children in poverty
        children_poor = Aggregate(
            simulation=sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person',
            filter_variable_name='age',
            filter_variable_leq=17
        )

        results = Aggregate.run([children_poor])
        assert results[0].value == 100.0  # Person 1 (age 5, weight 100)

    def test_multiple_aggregations(self, sample_tables):
        """Test running multiple different aggregations together."""
        sim = MockSimulation(sample_tables)

        aggs = [
            Aggregate(
                simulation=sim,
                variable_name='employment_income',
                aggregate_function=AggregateType.SUM,
                entity='person'
            ),
            Aggregate(
                simulation=sim,
                variable_name='employment_income',
                aggregate_function=AggregateType.MEAN,
                entity='person'
            ),
            Aggregate(
                simulation=sim,
                variable_name='employment_income',
                aggregate_function=AggregateType.MEDIAN,
                entity='person'
            ),
        ]

        results = Aggregate.run(aggs)
        assert len(results) == 3
        assert results[0].value > results[1].value > 0
        assert results[2].value > 0
