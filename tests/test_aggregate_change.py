"""
Tests for the clean AggregateChange implementation.

Tests cover:
- Basic change calculations
- Relative change calculations
- Cross-entity filters
- Batching multiple changes
- Edge cases
"""

import pytest
import pandas as pd

from policyengine.models.aggregate_change import AggregateChange
from policyengine.models.aggregate import AggregateType


class MockSimulation:
    """Mock simulation for testing."""

    def __init__(self, result, year=2024, sim_id=None):
        self.result = result
        self.dataset = MockDataset(year)
        self.id = sim_id or "sim_123"


class MockDataset:
    def __init__(self, year):
        self.year = year


@pytest.fixture
def baseline_tables():
    """Baseline simulation tables."""
    person = pd.DataFrame({
        'person_id': [0, 1, 2, 3],
        'person_household_id': [0, 0, 1, 1],
        'person_weight': [100.0, 100.0, 200.0, 200.0],
        'age': [30, 5, 45, 40],
        'employment_income': [50000, 0, 60000, 55000],
        'benefits': [5000, 2000, 0, 0],
    })

    household = pd.DataFrame({
        'household_id': [0, 1],
        'household_weight': [100.0, 200.0],
        'household_net_income': [57000, 115000],
        'is_in_poverty': [1, 0],
    })

    return {'person': person, 'household': household}


@pytest.fixture
def comparison_tables():
    """Comparison simulation tables (with policy change)."""
    person = pd.DataFrame({
        'person_id': [0, 1, 2, 3],
        'person_household_id': [0, 0, 1, 1],
        'person_weight': [100.0, 100.0, 200.0, 200.0],
        'age': [30, 5, 45, 40],
        'employment_income': [50000, 0, 60000, 55000],
        'benefits': [8000, 3000, 1000, 1000],  # Benefits increased
    })

    household = pd.DataFrame({
        'household_id': [0, 1],
        'household_weight': [100.0, 200.0],
        'household_net_income': [61000, 117000],  # Incomes increased
        'is_in_poverty': [0, 0],  # Household 0 lifted out of poverty
    })

    return {'person': person, 'household': household}


class TestBasicChanges:
    """Test basic change calculations."""

    def test_simple_change(self, baseline_tables, comparison_tables):
        """Test calculating a simple change in totals."""
        baseline_sim = MockSimulation(baseline_tables)
        comparison_sim = MockSimulation(comparison_tables)

        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='benefits',
            aggregate_function=AggregateType.SUM,
            entity='person'
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        # Baseline weighted sum: 5000*100 + 2000*100 + 0*200 + 0*200 = 700,000
        assert result.baseline_value == 700_000.0

        # Comparison weighted sum: 8000*100 + 3000*100 + 1000*200 + 1000*200 = 1,500,000
        assert result.comparison_value == 1_500_000.0

        # Change: 1,500,000 - 700,000 = 800,000
        assert result.change == 800_000.0

        # Relative change: 800,000 / 700,000 ≈ 1.14
        assert round(result.relative_change, 2) == 1.14

    def test_mean_change(self, baseline_tables, comparison_tables):
        """Test calculating change in mean values."""
        baseline_sim = MockSimulation(baseline_tables)
        comparison_sim = MockSimulation(comparison_tables)

        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='benefits',
            aggregate_function=AggregateType.MEAN,
            entity='person'
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        # Baseline weighted mean: 700,000 / 600 = 1,166.67
        assert round(result.baseline_value, 2) == 1166.67

        # Comparison weighted mean: 1,500,000 / 600 = 2,500
        assert result.comparison_value == 2500.0

        # Change: 2,500 - 1,166.67 = 1,333.33
        assert round(result.change, 2) == 1333.33

    def test_count_change(self, baseline_tables, comparison_tables):
        """Test change in counts (e.g., poverty count)."""
        baseline_sim = MockSimulation(baseline_tables)
        comparison_sim = MockSimulation(comparison_tables)

        # Count households in poverty
        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='household_id',
            aggregate_function=AggregateType.COUNT,
            entity='household',
            filter_variable_name='is_in_poverty',
            filter_variable_value=1
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        # Baseline: household 0 in poverty with weight 100
        assert result.baseline_value == 100.0

        # Comparison: 0 households in poverty
        assert result.comparison_value == 0.0

        # Change: -100 (weighted household count)
        assert result.change == -100.0


class TestCrossEntityChanges:
    """Test changes with cross-entity filters."""

    def test_persons_in_poverty_change(self, baseline_tables, comparison_tables):
        """Test change in count of persons in poor households."""
        baseline_sim = MockSimulation(baseline_tables)
        comparison_sim = MockSimulation(comparison_tables)

        # Count persons in poor households
        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='person_id',
            aggregate_function=AggregateType.COUNT,
            entity='person',
            filter_variable_name='is_in_poverty',
            filter_variable_value=1
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        # Baseline: persons 0, 1 in poor households with weights 100 + 100 = 200
        assert result.baseline_value == 200.0

        # Comparison: 0 persons in poor households
        assert result.comparison_value == 0.0

        # Change: -200 (weighted person count)
        assert result.change == -200.0

    def test_mean_benefits_for_poor(self, baseline_tables, comparison_tables):
        """Test change in mean benefits for persons in poor households."""
        baseline_sim = MockSimulation(baseline_tables)
        comparison_sim = MockSimulation(comparison_tables)

        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='benefits',
            aggregate_function=AggregateType.MEAN,
            entity='person',
            filter_variable_name='is_in_poverty',
            filter_variable_value=1
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        # Baseline: persons 0 and 1 in poverty
        # Weighted mean: (5000*100 + 2000*100) / 200 = 3,500
        assert result.baseline_value == 3500.0

        # Comparison: 0 persons in poverty (empty filter)
        assert result.comparison_value == 0.0


class TestBatching:
    """Test efficient batching of multiple changes."""

    def test_batch_multiple_changes(self, baseline_tables, comparison_tables):
        """Test processing multiple aggregate changes efficiently."""
        baseline_sim = MockSimulation(baseline_tables)
        comparison_sim = MockSimulation(comparison_tables)

        changes = [
            AggregateChange(
                baseline_simulation=baseline_sim,
                comparison_simulation=comparison_sim,
                variable_name='benefits',
                aggregate_function=AggregateType.SUM,
                entity='person'
            ),
            AggregateChange(
                baseline_simulation=baseline_sim,
                comparison_simulation=comparison_sim,
                variable_name='employment_income',
                aggregate_function=AggregateType.MEAN,
                entity='person'
            ),
            AggregateChange(
                baseline_simulation=baseline_sim,
                comparison_simulation=comparison_sim,
                variable_name='person_id',
                aggregate_function=AggregateType.COUNT,
                entity='person',
                filter_variable_name='is_in_poverty',
                filter_variable_value=1
            ),
        ]

        results = AggregateChange.run(changes)

        assert len(results) == 3
        assert results[0].change == 800_000.0  # Benefits increased
        assert results[1].change == 0.0  # Employment income unchanged
        assert results[2].change == -200.0  # Poverty count decreased (weighted)


class TestRangeFilters:
    """Test aggregate changes with range filters."""

    def test_change_with_age_filter(self, baseline_tables, comparison_tables):
        """Test change in benefits for specific age group."""
        baseline_sim = MockSimulation(baseline_tables)
        comparison_sim = MockSimulation(comparison_tables)

        # Benefits for children (age < 18)
        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='benefits',
            aggregate_function=AggregateType.SUM,
            entity='person',
            filter_variable_name='age',
            filter_variable_leq=17
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        # Person 1 (age 5): baseline 2000*100, comparison 3000*100
        assert result.baseline_value == 200_000.0
        assert result.comparison_value == 300_000.0
        assert result.change == 100_000.0

    def test_change_with_quantile_filter(self, baseline_tables, comparison_tables):
        """Test change for income quantiles."""
        baseline_sim = MockSimulation(baseline_tables)
        comparison_sim = MockSimulation(comparison_tables)

        # Benefits for bottom 50% by income
        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='benefits',
            aggregate_function=AggregateType.MEAN,
            entity='person',
            filter_variable_name='employment_income',
            filter_variable_quantile_leq=0.5
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        # Should get results for lower-income persons
        assert result.baseline_value >= 0
        assert result.comparison_value >= 0


class TestEdgeCases:
    """Test edge cases."""

    def test_zero_baseline_value(self, baseline_tables, comparison_tables):
        """Test relative change when baseline is zero."""
        # Create tables where baseline has zero value
        baseline_zero = {
            'person': pd.DataFrame({
                'person_id': [0, 1],
                'person_weight': [1.0, 1.0],
                'new_benefit': [0, 0]
            })
        }

        comparison_nonzero = {
            'person': pd.DataFrame({
                'person_id': [0, 1],
                'person_weight': [1.0, 1.0],
                'new_benefit': [1000, 1000]
            })
        }

        baseline_sim = MockSimulation(baseline_zero)
        comparison_sim = MockSimulation(comparison_nonzero)

        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='new_benefit',
            aggregate_function=AggregateType.SUM,
            entity='person'
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        assert result.baseline_value == 0.0
        assert result.comparison_value == 2000.0
        assert result.change == 2000.0
        assert result.relative_change == float('inf')

    def test_both_zero(self):
        """Test when both baseline and comparison are zero."""
        baseline = {
            'person': pd.DataFrame({
                'person_id': [0, 1],
                'person_weight': [1.0, 1.0],
                'value': [0, 0]
            })
        }

        baseline_sim = MockSimulation(baseline)
        comparison_sim = MockSimulation(baseline)

        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='value',
            aggregate_function=AggregateType.SUM,
            entity='person'
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        assert result.baseline_value == 0.0
        assert result.comparison_value == 0.0
        assert result.change == 0.0
        assert result.relative_change is None

    def test_missing_simulation(self):
        """Test error when simulation is missing."""
        agg_change = AggregateChange(
            variable_name='value',
            aggregate_function=AggregateType.SUM
        )

        with pytest.raises(ValueError, match='missing baseline_simulation'):
            AggregateChange.run([agg_change])

    def test_negative_change(self, baseline_tables, comparison_tables):
        """Test calculating negative changes correctly."""
        # Create scenario where value decreases
        baseline_high = {
            'person': pd.DataFrame({
                'person_id': [0, 1],
                'person_weight': [1.0, 1.0],
                'value': [1000, 1000]
            })
        }

        comparison_low = {
            'person': pd.DataFrame({
                'person_id': [0, 1],
                'person_weight': [1.0, 1.0],
                'value': [500, 500]
            })
        }

        baseline_sim = MockSimulation(baseline_high)
        comparison_sim = MockSimulation(comparison_low)

        agg_change = AggregateChange(
            baseline_simulation=baseline_sim,
            comparison_simulation=comparison_sim,
            variable_name='value',
            aggregate_function=AggregateType.SUM,
            entity='person'
        )

        results = AggregateChange.run([agg_change])
        result = results[0]

        assert result.baseline_value == 2000.0
        assert result.comparison_value == 1000.0
        assert result.change == -1000.0
        assert result.relative_change == -0.5


class TestRealWorldScenarios:
    """Test realistic policy analysis scenarios."""

    def test_poverty_impact_analysis(self, baseline_tables, comparison_tables):
        """Test complete poverty impact analysis."""
        baseline_sim = MockSimulation(baseline_tables)
        comparison_sim = MockSimulation(comparison_tables)

        analysis = [
            # Total poverty count
            AggregateChange(
                baseline_simulation=baseline_sim,
                comparison_simulation=comparison_sim,
                variable_name='household_id',
                aggregate_function=AggregateType.COUNT,
                entity='household',
                filter_variable_name='is_in_poverty',
                filter_variable_value=1
            ),
            # Persons in poverty
            AggregateChange(
                baseline_simulation=baseline_sim,
                comparison_simulation=comparison_sim,
                variable_name='person_id',
                aggregate_function=AggregateType.COUNT,
                entity='person',
                filter_variable_name='is_in_poverty',
                filter_variable_value=1
            ),
            # Mean benefits for poor households
            AggregateChange(
                baseline_simulation=baseline_sim,
                comparison_simulation=comparison_sim,
                variable_name='benefits',
                aggregate_function=AggregateType.MEAN,
                entity='person',
                filter_variable_name='is_in_poverty',
                filter_variable_value=1
            ),
        ]

        results = AggregateChange.run(analysis)

        # Poverty decreased
        assert results[0].change < 0  # Fewer poor households
        assert results[1].change < 0  # Fewer poor persons

        # Benefits increased for those who were poor
        assert results[2].baseline_value > 0
