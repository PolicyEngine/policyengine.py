"""Tests for inequality analysis output type."""

import os
import tempfile

import numpy as np
import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.outputs.inequality import (
    UK_INEQUALITY_INCOME_VARIABLE,
    US_INEQUALITY_INCOME_VARIABLE,
    Inequality,
    _gini,
)
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest,
)


def test_gini_perfect_equality():
    """Test Gini coefficient with perfect equality (all same income)."""
    values = np.array([100.0, 100.0, 100.0, 100.0])
    weights = np.array([1.0, 1.0, 1.0, 1.0])
    gini = _gini(values, weights)
    assert abs(gini) < 0.01  # Should be ~0


def test_gini_perfect_inequality():
    """Test Gini coefficient with extreme inequality."""
    # One person has all income, others have none
    values = np.array([0.0, 0.0, 0.0, 1000.0])
    weights = np.array([1.0, 1.0, 1.0, 1.0])
    gini = _gini(values, weights)
    assert gini > 0.7  # Should be high


def test_gini_moderate_inequality():
    """Test Gini coefficient with moderate inequality."""
    values = np.array([10.0, 20.0, 30.0, 40.0])
    weights = np.array([1.0, 1.0, 1.0, 1.0])
    gini = _gini(values, weights)
    # Moderate inequality should be between 0.1 and 0.4
    assert 0.1 < gini < 0.4


def test_gini_weighted():
    """Test Gini coefficient with different weights."""
    values = np.array([100.0, 200.0])
    weights = np.array([3.0, 1.0])  # 3 people with 100, 1 with 200
    gini = _gini(values, weights)
    # Should reflect that 75% have lower income
    assert 0.05 < gini < 0.3


def test_inequality_basic():
    """Test basic inequality calculation."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [0, 1, 2, 3],
                "benunit_id": [0, 0, 1, 1],
                "household_id": [0, 0, 1, 1],
                "person_weight": [1.0, 1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [0, 1],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    # Two households with different incomes
    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [0, 1],
                "household_weight": [1.0, 1.0],
                "equiv_hbai_household_net_income": [20000.0, 80000.0],
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

        inequality = Inequality(
            simulation=simulation,
            income_variable="equiv_hbai_household_net_income",
            entity="household",
        )
        inequality.run()

        # Check Gini is calculated
        assert inequality.gini is not None
        assert 0 <= inequality.gini <= 1

        # Check income shares are calculated
        assert inequality.top_10_share is not None
        assert inequality.top_1_share is not None
        assert inequality.bottom_50_share is not None

        # With 2 households of equal weight, one with 20k and one with 80k:
        # Top 50% (1 hh) has 80k, bottom 50% (1 hh) has 20k
        # Total = 100k, so bottom 50% share = 20%
        assert abs(inequality.bottom_50_share - 0.2) < 0.01


def test_inequality_income_shares():
    """Test income share calculations with more households."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": list(range(10)),
                "benunit_id": list(range(10)),
                "household_id": list(range(10)),
                "person_weight": [1.0] * 10,
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": list(range(10)),
                "benunit_weight": [1.0] * 10,
            }
        ),
        weights="benunit_weight",
    )

    # 10 households with incomes 10k, 20k, ..., 100k
    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": list(range(10)),
                "household_weight": [1.0] * 10,
                "equiv_hbai_household_net_income": [
                    10000.0,
                    20000.0,
                    30000.0,
                    40000.0,
                    50000.0,
                    60000.0,
                    70000.0,
                    80000.0,
                    90000.0,
                    100000.0,
                ],
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

        inequality = Inequality(
            simulation=simulation,
            income_variable="equiv_hbai_household_net_income",
            entity="household",
        )
        inequality.run()

        # Total income = 550k
        # Top 10% (1 hh with 100k) = 100k/550k = 18.2%
        assert abs(inequality.top_10_share - 100000 / 550000) < 0.02

        # Bottom 50% (5 hh with 10k-50k) = 150k/550k = 27.3%
        assert abs(inequality.bottom_50_share - 150000 / 550000) < 0.02


def test_inequality_variable_defaults():
    """Test default income variables for UK and US."""
    assert UK_INEQUALITY_INCOME_VARIABLE == "equiv_hbai_household_net_income"
    assert US_INEQUALITY_INCOME_VARIABLE == "household_net_income"


def test_inequality_weighted():
    """Test inequality with weighted households."""
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [0, 1],
                "benunit_id": [0, 1],
                "household_id": [0, 1],
                "person_weight": [1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [0, 1],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    # Two households: one with weight 9 (30k), one with weight 1 (100k)
    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [0, 1],
                "household_weight": [9.0, 1.0],
                "equiv_hbai_household_net_income": [30000.0, 100000.0],
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

        inequality = Inequality(
            simulation=simulation,
            income_variable="equiv_hbai_household_net_income",
            entity="household",
        )
        inequality.run()

        # Total weighted income = 9*30k + 1*100k = 370k
        # 90% of weight (9 hh) has 270k = 73% of income
        # So top 10% (1 hh with weight 1) has 100k/370k = 27%
        assert abs(inequality.top_10_share - 100000 / 370000) < 0.02
