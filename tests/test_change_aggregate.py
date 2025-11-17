import os
import tempfile

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import (
    Simulation,
)
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType,
)
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest,
)


def test_change_aggregate_count():
    """Test counting people with any change."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "benunit_id": [1, 1, 2, 2],
                "household_id": [1, 1, 2, 2],
                "age": [30, 25, 40, 35],
                "employment_income": [50000, 30000, 60000, 40000],
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
        baseline_filepath = os.path.join(tmpdir, "baseline.h5")
        reform_filepath = os.path.join(tmpdir, "reform.h5")

        baseline_dataset = PolicyEngineUKDataset(
            name="Baseline",
            description="Baseline dataset",
            filepath=baseline_filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        # Reform: increase everyone's income by 1000
        reform_person_df = MicroDataFrame(
            pd.DataFrame(
                {
                    "person_id": [1, 2, 3, 4],
                    "benunit_id": [1, 1, 2, 2],
                    "household_id": [1, 1, 2, 2],
                    "age": [30, 25, 40, 35],
                    "employment_income": [51000, 31000, 61000, 41000],
                    "person_weight": [1.0, 1.0, 1.0, 1.0],
                }
            ),
            weights="person_weight",
        )

        reform_dataset = PolicyEngineUKDataset(
            name="Reform",
            description="Reform dataset",
            filepath=reform_filepath,
            year=2024,
            data=UKYearData(
                person=reform_person_df,
                benunit=benunit_df,
                household=household_df,
            ),
        )

        baseline_sim = Simulation(
            dataset=baseline_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=baseline_dataset,
        )

        reform_sim = Simulation(
            dataset=reform_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=reform_dataset,
        )

        # Count people with any change (all 4 should have changed)
        agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="employment_income",
            aggregate_type=ChangeAggregateType.COUNT,
        )
        agg.run()

        assert agg.result == 4


def test_change_aggregate_with_absolute_filter():
    """Test filtering by absolute change amount."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "benunit_id": [1, 1, 2, 2],
                "household_id": [1, 1, 2, 2],
                "age": [30, 25, 40, 35],
                "employment_income": [50000, 30000, 60000, 40000],
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
        baseline_filepath = os.path.join(tmpdir, "baseline.h5")
        reform_filepath = os.path.join(tmpdir, "reform.h5")

        baseline_dataset = PolicyEngineUKDataset(
            name="Baseline",
            description="Baseline dataset",
            filepath=baseline_filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        # Reform: different gains for different people
        reform_person_df = MicroDataFrame(
            pd.DataFrame(
                {
                    "person_id": [1, 2, 3, 4],
                    "benunit_id": [1, 1, 2, 2],
                    "household_id": [1, 1, 2, 2],
                    "age": [30, 25, 40, 35],
                    "employment_income": [
                        52000,
                        30500,
                        61500,
                        40200,
                    ],  # Gains: 2000, 500, 1500, 200
                    "person_weight": [1.0, 1.0, 1.0, 1.0],
                }
            ),
            weights="person_weight",
        )

        reform_dataset = PolicyEngineUKDataset(
            name="Reform",
            description="Reform dataset",
            filepath=reform_filepath,
            year=2024,
            data=UKYearData(
                person=reform_person_df,
                benunit=benunit_df,
                household=household_df,
            ),
        )

        baseline_sim = Simulation(
            dataset=baseline_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=baseline_dataset,
        )

        reform_sim = Simulation(
            dataset=reform_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=reform_dataset,
        )

        # Count people who gain at least 1000
        agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="employment_income",
            aggregate_type=ChangeAggregateType.COUNT,
            change_geq=1000,
        )
        agg.run()

        assert agg.result == 2  # People 1 and 3


def test_change_aggregate_with_loss_filter():
    """Test filtering for losses (negative changes)."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "benunit_id": [1, 1, 2, 2],
                "household_id": [1, 1, 2, 2],
                "age": [30, 25, 40, 35],
                "employment_income": [50000, 30000, 60000, 40000],
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
        baseline_filepath = os.path.join(tmpdir, "baseline.h5")
        reform_filepath = os.path.join(tmpdir, "reform.h5")

        baseline_dataset = PolicyEngineUKDataset(
            name="Baseline",
            description="Baseline dataset",
            filepath=baseline_filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        # Reform: some people lose money
        reform_person_df = MicroDataFrame(
            pd.DataFrame(
                {
                    "person_id": [1, 2, 3, 4],
                    "benunit_id": [1, 1, 2, 2],
                    "household_id": [1, 1, 2, 2],
                    "age": [30, 25, 40, 35],
                    "employment_income": [
                        49000,
                        29000,
                        60500,
                        39000,
                    ],  # Changes: -1000, -1000, 500, -1000
                    "person_weight": [1.0, 1.0, 1.0, 1.0],
                }
            ),
            weights="person_weight",
        )

        reform_dataset = PolicyEngineUKDataset(
            name="Reform",
            description="Reform dataset",
            filepath=reform_filepath,
            year=2024,
            data=UKYearData(
                person=reform_person_df,
                benunit=benunit_df,
                household=household_df,
            ),
        )

        baseline_sim = Simulation(
            dataset=baseline_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=baseline_dataset,
        )

        reform_sim = Simulation(
            dataset=reform_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=reform_dataset,
        )

        # Count people who lose at least 500 (change <= -500)
        agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="employment_income",
            aggregate_type=ChangeAggregateType.COUNT,
            change_leq=-500,
        )
        agg.run()

        assert agg.result == 3  # People 1, 2, and 4


def test_change_aggregate_with_relative_filter():
    """Test filtering by relative (percentage) change."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "benunit_id": [1, 1, 2, 2],
                "household_id": [1, 1, 2, 2],
                "age": [30, 25, 40, 35],
                "employment_income": [50000, 20000, 60000, 40000],
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
        baseline_filepath = os.path.join(tmpdir, "baseline.h5")
        reform_filepath = os.path.join(tmpdir, "reform.h5")

        baseline_dataset = PolicyEngineUKDataset(
            name="Baseline",
            description="Baseline dataset",
            filepath=baseline_filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        # Reform: different percentage gains
        reform_person_df = MicroDataFrame(
            pd.DataFrame(
                {
                    "person_id": [1, 2, 3, 4],
                    "benunit_id": [1, 1, 2, 2],
                    "household_id": [1, 1, 2, 2],
                    "age": [30, 25, 40, 35],
                    # Gains: 5000 (10%), 2000 (10%), 3000 (5%), 1000 (2.5%)
                    "employment_income": [55000, 22000, 63000, 41000],
                    "person_weight": [1.0, 1.0, 1.0, 1.0],
                }
            ),
            weights="person_weight",
        )

        reform_dataset = PolicyEngineUKDataset(
            name="Reform",
            description="Reform dataset",
            filepath=reform_filepath,
            year=2024,
            data=UKYearData(
                person=reform_person_df,
                benunit=benunit_df,
                household=household_df,
            ),
        )

        baseline_sim = Simulation(
            dataset=baseline_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=baseline_dataset,
        )

        reform_sim = Simulation(
            dataset=reform_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=reform_dataset,
        )

        # Count people who gain at least 8% (0.08 relative change)
        agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="employment_income",
            aggregate_type=ChangeAggregateType.COUNT,
            relative_change_geq=0.08,
        )
        agg.run()

        assert agg.result == 2  # People 1 and 2 (both 10%)


def test_change_aggregate_sum():
    """Test summing changes."""
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
        baseline_filepath = os.path.join(tmpdir, "baseline.h5")
        reform_filepath = os.path.join(tmpdir, "reform.h5")

        baseline_dataset = PolicyEngineUKDataset(
            name="Baseline",
            description="Baseline dataset",
            filepath=baseline_filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        # Reform: everyone gains 1000
        reform_person_df = MicroDataFrame(
            pd.DataFrame(
                {
                    "person_id": [1, 2, 3],
                    "benunit_id": [1, 1, 2],
                    "household_id": [1, 1, 2],
                    "age": [30, 25, 40],
                    "employment_income": [51000, 31000, 61000],
                    "person_weight": [1.0, 1.0, 1.0],
                }
            ),
            weights="person_weight",
        )

        reform_dataset = PolicyEngineUKDataset(
            name="Reform",
            description="Reform dataset",
            filepath=reform_filepath,
            year=2024,
            data=UKYearData(
                person=reform_person_df,
                benunit=benunit_df,
                household=household_df,
            ),
        )

        baseline_sim = Simulation(
            dataset=baseline_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=baseline_dataset,
        )

        reform_sim = Simulation(
            dataset=reform_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=reform_dataset,
        )

        # Sum all changes
        agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="employment_income",
            aggregate_type=ChangeAggregateType.SUM,
        )
        agg.run()

        assert agg.result == 3000


def test_change_aggregate_mean():
    """Test mean change."""
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
        baseline_filepath = os.path.join(tmpdir, "baseline.h5")
        reform_filepath = os.path.join(tmpdir, "reform.h5")

        baseline_dataset = PolicyEngineUKDataset(
            name="Baseline",
            description="Baseline dataset",
            filepath=baseline_filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        # Reform: different gains
        reform_person_df = MicroDataFrame(
            pd.DataFrame(
                {
                    "person_id": [1, 2, 3],
                    "benunit_id": [1, 1, 2],
                    "household_id": [1, 1, 2],
                    "age": [30, 25, 40],
                    "employment_income": [
                        51000,
                        32000,
                        63000,
                    ],  # Gains: 1000, 2000, 3000
                    "person_weight": [1.0, 1.0, 1.0],
                }
            ),
            weights="person_weight",
        )

        reform_dataset = PolicyEngineUKDataset(
            name="Reform",
            description="Reform dataset",
            filepath=reform_filepath,
            year=2024,
            data=UKYearData(
                person=reform_person_df,
                benunit=benunit_df,
                household=household_df,
            ),
        )

        baseline_sim = Simulation(
            dataset=baseline_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=baseline_dataset,
        )

        reform_sim = Simulation(
            dataset=reform_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=reform_dataset,
        )

        # Mean change
        agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="employment_income",
            aggregate_type=ChangeAggregateType.MEAN,
        )
        agg.run()

        assert agg.result == 2000


def test_change_aggregate_with_filter_variable():
    """Test filtering by another variable (e.g., only adults)."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "benunit_id": [1, 1, 2, 2],
                "household_id": [1, 1, 2, 2],
                "age": [30, 25, 40, 15],  # Person 4 is a child
                "employment_income": [50000, 30000, 60000, 5000],
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
        baseline_filepath = os.path.join(tmpdir, "baseline.h5")
        reform_filepath = os.path.join(tmpdir, "reform.h5")

        baseline_dataset = PolicyEngineUKDataset(
            name="Baseline",
            description="Baseline dataset",
            filepath=baseline_filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        # Reform: everyone gains 1000
        reform_person_df = MicroDataFrame(
            pd.DataFrame(
                {
                    "person_id": [1, 2, 3, 4],
                    "benunit_id": [1, 1, 2, 2],
                    "household_id": [1, 1, 2, 2],
                    "age": [30, 25, 40, 15],
                    "employment_income": [51000, 31000, 61000, 6000],
                    "person_weight": [1.0, 1.0, 1.0, 1.0],
                }
            ),
            weights="person_weight",
        )

        reform_dataset = PolicyEngineUKDataset(
            name="Reform",
            description="Reform dataset",
            filepath=reform_filepath,
            year=2024,
            data=UKYearData(
                person=reform_person_df,
                benunit=benunit_df,
                household=household_df,
            ),
        )

        baseline_sim = Simulation(
            dataset=baseline_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=baseline_dataset,
        )

        reform_sim = Simulation(
            dataset=reform_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=reform_dataset,
        )

        # Count adults (age >= 18) who gain money
        agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="employment_income",
            aggregate_type=ChangeAggregateType.COUNT,
            change_geq=1,
            filter_variable="age",
            filter_variable_geq=18,
        )
        agg.run()

        assert agg.result == 3  # Exclude person 4 (age 15)


def test_change_aggregate_combined_filters():
    """Test combining multiple filter types."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4, 5],
                "benunit_id": [1, 1, 2, 2, 3],
                "household_id": [1, 1, 2, 2, 3],
                "age": [30, 25, 40, 35, 45],
                "employment_income": [50000, 20000, 60000, 40000, 80000],
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
        baseline_filepath = os.path.join(tmpdir, "baseline.h5")
        reform_filepath = os.path.join(tmpdir, "reform.h5")

        baseline_dataset = PolicyEngineUKDataset(
            name="Baseline",
            description="Baseline dataset",
            filepath=baseline_filepath,
            year=2024,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        # Reform: varying gains
        reform_person_df = MicroDataFrame(
            pd.DataFrame(
                {
                    "person_id": [1, 2, 3, 4, 5],
                    "benunit_id": [1, 1, 2, 2, 3],
                    "household_id": [1, 1, 2, 2, 3],
                    "age": [30, 25, 40, 35, 45],
                    # Changes: 10000 (20%), 2000 (10%), 3000 (5%), 800 (2%), 4000 (5%)
                    "employment_income": [60000, 22000, 63000, 40800, 84000],
                    "person_weight": [1.0, 1.0, 1.0, 1.0, 1.0],
                }
            ),
            weights="person_weight",
        )

        reform_dataset = PolicyEngineUKDataset(
            name="Reform",
            description="Reform dataset",
            filepath=reform_filepath,
            year=2024,
            data=UKYearData(
                person=reform_person_df,
                benunit=benunit_df,
                household=household_df,
            ),
        )

        baseline_sim = Simulation(
            dataset=baseline_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=baseline_dataset,
        )

        reform_sim = Simulation(
            dataset=reform_dataset,
            tax_benefit_model_version=uk_latest,
            output_dataset=reform_dataset,
        )

        # Count people age >= 30 who gain at least 2000 and at least 5% relative gain
        agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="employment_income",
            aggregate_type=ChangeAggregateType.COUNT,
            change_geq=2000,
            relative_change_geq=0.05,
            filter_variable="age",
            filter_variable_geq=30,
        )
        agg.run()

        # Should include: person 1 (10000/20%, age 30), person 3 (3000/5%, age 40), person 5 (4000/5%, age 45)
        # Should exclude: person 2 (age 25), person 4 (only 800 gain)
        assert agg.result == 3
