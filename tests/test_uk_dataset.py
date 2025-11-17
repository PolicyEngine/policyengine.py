import os
import tempfile

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Dataset, TaxBenefitModel
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
)


def test_imports():
    """Test that basic imports work."""
    # Verify classes are importable
    assert PolicyEngineUKDataset is not None
    assert UKYearData is not None
    assert Dataset is not None
    assert TaxBenefitModel is not None


def test_uk_latest_instantiation():
    """Test that uk_latest can be instantiated without errors."""
    from policyengine.tax_benefit_models.uk import uk_latest

    assert uk_latest is not None
    assert uk_latest.version is not None
    assert uk_latest.model is not None
    assert uk_latest.created_at is not None
    assert (
        len(uk_latest.variables) > 0
    )  # Should have variables from policyengine-uk


def test_save_and_load_single_year():
    """Test saving and loading a dataset with a single year."""
    # Create sample data
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "age": [25, 30, 35],
                "income": [30000, 45000, 60000],
                "person_weight": [1.0, 1.0, 1.0],
            }
        ),
        weights="person_weight",
    )

    benunit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "benunit_id": [1, 2],
                "size": [2, 1],
                "total_income": [75000, 60000],
                "benunit_weight": [1.0, 1.0],
            }
        ),
        weights="benunit_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [1],
                "num_people": [3],
                "rent": [1200],
                "household_weight": [1.0],
            }
        ),
        weights="household_weight",
    )

    # Create dataset
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_dataset.h5")

        dataset = PolicyEngineUKDataset(
            name="Test Dataset",
            description="A test dataset",
            filepath=filepath,
            year=2025,
            data=UKYearData(
                person=person_df, benunit=benunit_df, household=household_df
            ),
        )

        # Save to file
        dataset.save()

        # Load it back
        loaded = PolicyEngineUKDataset(
            name="Loaded Dataset",
            description="Loaded from file",
            filepath=filepath,
            year=2025,
        )
        loaded.load()

        # Verify data
        assert loaded.year == 2025
        # Convert to DataFrame for comparison (MicroDataFrame inherits from DataFrame)
        pd.testing.assert_frame_equal(
            pd.DataFrame(loaded.data.person), pd.DataFrame(person_df)
        )
        pd.testing.assert_frame_equal(
            pd.DataFrame(loaded.data.benunit), pd.DataFrame(benunit_df)
        )
        pd.testing.assert_frame_equal(
            pd.DataFrame(loaded.data.household), pd.DataFrame(household_df)
        )
