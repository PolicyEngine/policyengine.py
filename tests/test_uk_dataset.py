import pandas as pd
import tempfile
import os
from policyengine.core import *
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
    person_df = pd.DataFrame(
        {
            "person_id": [1, 2, 3],
            "age": [25, 30, 35],
            "income": [30000, 45000, 60000],
        }
    )

    benunit_df = pd.DataFrame(
        {"benunit_id": [1, 2], "size": [2, 1], "total_income": [75000, 60000]}
    )

    household_df = pd.DataFrame(
        {"household_id": [1], "num_people": [3], "rent": [1200]}
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
        pd.testing.assert_frame_equal(loaded.data.person, person_df)
        pd.testing.assert_frame_equal(loaded.data.benunit, benunit_df)
        pd.testing.assert_frame_equal(loaded.data.household, household_df)
