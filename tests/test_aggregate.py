import os
import tempfile

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest,
)


def test_aggregate_sum():
    """Test basic sum aggregation."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "age": [30, 25, 40],
                "employment_income": [50000, 30000, 60000],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.h5")

        dataset = PolicyEngineUKDataset(
            name="Test",
            description="Test dataset",
            filepath=filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=dataset,
        )

        agg = Aggregate(
            simulation=simulation,
            variable="employment_income",
            aggregate_type=AggregateType.SUM,
        )
        agg.run()

        assert agg.result == 140000


def test_aggregate_mean():
    """Test mean aggregation."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "age": [30, 25, 40],
                "employment_income": [50000, 30000, 60000],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.h5")

        dataset = PolicyEngineUKDataset(
            name="Test",
            description="Test dataset",
            filepath=filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=dataset,
        )

        agg = Aggregate(
            simulation=simulation,
            variable="employment_income",
            aggregate_type=AggregateType.MEAN,
        )
        agg.run()

        assert abs(agg.result - 46666.67) < 1


def test_aggregate_count():
    """Test count aggregation."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "age": [30, 25, 40],
                "employment_income": [50000, 30000, 60000],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.h5")

        dataset = PolicyEngineUKDataset(
            name="Test",
            description="Test dataset",
            filepath=filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=dataset,
        )

        agg = Aggregate(
            simulation=simulation,
            variable="employment_income",
            aggregate_type=AggregateType.COUNT,
        )
        agg.run()

        assert agg.result == 3


def test_aggregate_with_entity_mapping():
    """Test aggregation with entity mapping (person var at household level)."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "benunit_id": [1, 1, 2],
                "household_id": [1, 1, 2],
                "age": [30, 25, 40],
                "employment_income": [50000, 30000, 60000],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.h5")

        dataset = PolicyEngineUKDataset(
            name="Test",
            description="Test dataset",
            filepath=filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=dataset,
        )

        # Aggregate person-level income at household level
        agg = Aggregate(
            simulation=simulation,
            variable="employment_income",
            aggregate_type=AggregateType.SUM,
            entity="household",
        )
        agg.run()

        # Should sum across all people mapped to households
        assert agg.result == 140000


def test_aggregate_with_filter():
    """Test aggregation with basic filter."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "benunit_id": [1, 1, 2, 2],
                "household_id": [1, 1, 2, 2],
                "age": [30, 25, 40, 35],
                "employment_income": [50000, 30000, 60000, 45000],
                "person_weight": [1.0, 1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2],
                "household_weight": [1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.h5")

        dataset = PolicyEngineUKDataset(
            name="Test",
            description="Test dataset",
            filepath=filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=dataset,
        )

        # Sum income for people age >= 30
        agg = Aggregate(
            simulation=simulation,
            variable="employment_income",
            aggregate_type=AggregateType.SUM,
            filter_variable="age",
            filter_variable_geq=30,
        )
        agg.run()

        # Should only include people aged 30, 40, and 35
        assert agg.result == 50000 + 60000 + 45000


def test_aggregate_with_quantile_filter():
    """Test aggregation with quantile-based filter."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4, 5],
                "benunit_id": [1, 1, 2, 2, 3],
                "household_id": [1, 1, 2, 2, 3],
                "age": [20, 30, 40, 50, 60],
                "employment_income": [10000, 20000, 30000, 40000, 50000],
                "person_weight": [1.0, 1.0, 1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2, 3],
                "benunit_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1, 2, 3],
                "household_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="household_weight",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.h5")

        dataset = PolicyEngineUKDataset(
            name="Test",
            description="Test dataset",
            filepath=filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=dataset,
        )

        # Sum income for bottom 50% (by income)
        agg = Aggregate(
            simulation=simulation,
            variable="employment_income",
            aggregate_type=AggregateType.SUM,
            filter_variable="employment_income",
            filter_variable_leq=0.5,
            filter_variable_describes_quantiles=True,
        )
        agg.run()

        # Should include people with income <= median (30000)
        assert agg.result == 10000 + 20000 + 30000


def test_aggregate_invalid_variable():
    """Test that invalid variable names raise errors during run()."""
    import pytest

    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1],
                "benunit_id": [1],
                "household_id": [1],
                "age": [30],
                "employment_income": [50000],
                "person_weight": [1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1],
                "benunit_weight": [1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1],
                "household_weight": [1.0],
            }
        ),
        weights="household_weight",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.h5")

        dataset = PolicyEngineUKDataset(
            name="Test",
            description="Test dataset",
            filepath=filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=dataset,
        )

        # Invalid variable name should raise error on run()
        agg = Aggregate(
            simulation=simulation,
            variable="nonexistent_variable",
            aggregate_type=AggregateType.SUM,
        )
        with pytest.raises(StopIteration):
            agg.run()

        # Invalid filter variable name should raise error on run()
        agg = Aggregate(
            simulation=simulation,
            variable="employment_income",
            aggregate_type=AggregateType.SUM,
            filter_variable="nonexistent_filter",
        )
        with pytest.raises(StopIteration):
            agg.run()
