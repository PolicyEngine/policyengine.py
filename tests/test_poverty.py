"""Tests for poverty analysis output type."""

import os
import tempfile

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.outputs.poverty import (
    UK_POVERTY_VARIABLES,
    US_POVERTY_VARIABLES,
    Poverty,
    UKPovertyType,
    USPovertyType,
)
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest,
)


def test_poverty_basic():
    """Test basic poverty calculation.

    in_poverty_bhc is a household-level variable, so we set it on households
    and then map to persons for the rate calculation.
    """
    # Create test data - 2 people in household 0 (in poverty), 3 in household 1 (not)
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [0, 1, 2, 3, 4],
                "benunit_id": [0, 0, 1, 1, 1],
                "household_id": [0, 0, 1, 1, 1],
                "person_weight": [1.0, 1.0, 1.0, 1.0, 1.0],
                "is_child": [True, False, True, False, False],
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

    # Household 0 is in poverty, household 1 is not
    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [0, 1],
                "household_weight": [1.0, 1.0],
                "in_poverty_bhc": [True, False],
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

        # Calculate poverty at person level (mapping from household)
        poverty = Poverty(
            simulation=simulation,
            poverty_variable="in_poverty_bhc",
            entity="person",
        )
        poverty.run()

        # 2 people (in hh 0) out of 5 total in poverty = 40%
        assert poverty.headcount == 2.0
        assert poverty.total_population == 5.0
        assert poverty.rate == 0.4


def test_poverty_with_filter():
    """Test poverty calculation with demographic filter.

    is_child is person-level, in_poverty_bhc is household-level.
    We test child poverty by filtering to children and mapping household poverty.
    """
    # Household 0: 2 people (1 child, 1 adult), in poverty
    # Household 1: 3 people (2 children, 1 adult), not in poverty
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [0, 1, 2, 3, 4],
                "benunit_id": [0, 0, 1, 1, 1],
                "household_id": [0, 0, 1, 1, 1],
                "person_weight": [1.0, 1.0, 1.0, 1.0, 1.0],
                "is_child": [True, False, True, True, False],
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

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [0, 1],
                "household_weight": [1.0, 1.0],
                "in_poverty_bhc": [True, False],
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

        # Calculate child poverty (filter for is_child == True)
        child_poverty = Poverty(
            simulation=simulation,
            poverty_variable="in_poverty_bhc",
            entity="person",
            filter_variable="is_child",
            filter_variable_eq=True,
        )
        child_poverty.run()

        # 3 children total: 1 in hh 0 (in poverty) + 2 in hh 1 (not in poverty)
        # Child poverty headcount = 1, total children = 3, rate = 33.3%
        assert child_poverty.headcount == 1.0
        assert child_poverty.total_population == 3.0
        assert abs(child_poverty.rate - 1 / 3) < 0.001


def test_poverty_type_enums():
    """Test poverty type enums have correct values."""
    # UK poverty types
    assert UKPovertyType.ABSOLUTE_BHC == "absolute_bhc"
    assert UKPovertyType.ABSOLUTE_AHC == "absolute_ahc"
    assert UKPovertyType.RELATIVE_BHC == "relative_bhc"
    assert UKPovertyType.RELATIVE_AHC == "relative_ahc"

    # US poverty types
    assert USPovertyType.SPM == "spm"
    assert USPovertyType.SPM_DEEP == "spm_deep"


def test_poverty_variable_mappings():
    """Test poverty variable mappings are correct."""
    # UK mappings
    assert UK_POVERTY_VARIABLES[UKPovertyType.ABSOLUTE_BHC] == "in_poverty_bhc"
    assert UK_POVERTY_VARIABLES[UKPovertyType.ABSOLUTE_AHC] == "in_poverty_ahc"
    assert (
        UK_POVERTY_VARIABLES[UKPovertyType.RELATIVE_BHC]
        == "in_relative_poverty_bhc"
    )
    assert (
        UK_POVERTY_VARIABLES[UKPovertyType.RELATIVE_AHC]
        == "in_relative_poverty_ahc"
    )

    # US mappings
    assert (
        US_POVERTY_VARIABLES[USPovertyType.SPM] == "spm_unit_is_in_spm_poverty"
    )
    assert (
        US_POVERTY_VARIABLES[USPovertyType.SPM_DEEP]
        == "spm_unit_is_in_deep_spm_poverty"
    )


def test_poverty_weighted():
    """Test poverty calculation with weights.

    Household 0 is in poverty (2 people, weights 1+2=3),
    Household 1 is not in poverty (2 people, weights 3+4=7).
    """
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [0, 1, 2, 3],
                "benunit_id": [0, 0, 1, 1],
                "household_id": [0, 0, 1, 1],
                "person_weight": [1.0, 2.0, 3.0, 4.0],  # Total weight = 10
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

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [0, 1],
                "household_weight": [1.0, 1.0],
                "in_poverty_bhc": [True, False],
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

        # Calculate poverty
        poverty = Poverty(
            simulation=simulation,
            poverty_variable="in_poverty_bhc",
            entity="person",
        )
        poverty.run()

        # Weighted: 1 + 2 = 3 in poverty (hh 0), total = 10, rate = 30%
        assert poverty.headcount == 3.0
        assert poverty.total_population == 10.0
        assert poverty.rate == 0.3
