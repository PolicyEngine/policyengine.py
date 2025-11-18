import os
import tempfile

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.tax_benefit_models.us import (
    PolicyEngineUSDataset,
    USYearData,
    us_latest,
)


def test_us_latest_instantiation():
    """Test that us_latest can be instantiated without errors."""
    assert us_latest is not None
    assert us_latest.version is not None
    assert us_latest.model is not None
    assert us_latest.created_at is not None
    assert (
        len(us_latest.variables) > 0
    )  # Should have variables from policyengine-us


def test_save_and_load_us_dataset():
    """Test saving and loading a US dataset."""
    # Create sample data with minimal required columns
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [0, 1, 2],
                "household_id": [0, 0, 1],
                "marital_unit_id": [0, 0, 1],
                "family_id": [0, 0, 1],
                "spm_unit_id": [0, 0, 1],
                "tax_unit_id": [0, 0, 1],
                "age": [30, 35, 25],
                "employment_income": [50000, 60000, 40000],
                "person_weight": [1000.0, 1000.0, 1000.0],
            }
        ),
        weights="person_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [0, 1],
                "household_weight": [1000.0, 1000.0],
            }
        ),
        weights="household_weight",
    )

    marital_unit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "marital_unit_id": [0, 1],
                "marital_unit_weight": [1000.0, 1000.0],
            }
        ),
        weights="marital_unit_weight",
    )

    family_df = MicroDataFrame(
        pd.DataFrame(
            {
                "family_id": [0, 1],
                "family_weight": [1000.0, 1000.0],
            }
        ),
        weights="family_weight",
    )

    spm_unit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "spm_unit_id": [0, 1],
                "spm_unit_weight": [1000.0, 1000.0],
            }
        ),
        weights="spm_unit_weight",
    )

    tax_unit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "tax_unit_id": [0, 1],
                "tax_unit_weight": [1000.0, 1000.0],
            }
        ),
        weights="tax_unit_weight",
    )

    # Create dataset
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_us_dataset.h5")

        dataset = PolicyEngineUSDataset(
            name="Test US Dataset",
            description="A test US dataset",
            filepath=filepath,
            year=2024,
            data=USYearData(
                person=person_df,
                household=household_df,
                marital_unit=marital_unit_df,
                family=family_df,
                spm_unit=spm_unit_df,
                tax_unit=tax_unit_df,
            ),
        )

        # Save to file
        dataset.save()

        # Load it back
        loaded = PolicyEngineUSDataset(
            name="Loaded US Dataset",
            description="Loaded from file",
            filepath=filepath,
            year=2024,
        )
        loaded.load()

        # Verify data
        assert loaded.year == 2024
        pd.testing.assert_frame_equal(
            pd.DataFrame(loaded.data.person), pd.DataFrame(person_df)
        )
        pd.testing.assert_frame_equal(
            pd.DataFrame(loaded.data.household), pd.DataFrame(household_df)
        )


def test_us_simulation_from_dataset():
    """Test running a US simulation from a dataset using PolicyEngine Core pattern."""
    # Create a small test dataset
    person_df = MicroDataFrame(
        pd.DataFrame(
            {
                "person_id": [0, 1],
                "household_id": [0, 0],
                "marital_unit_id": [0, 0],
                "family_id": [0, 0],
                "spm_unit_id": [0, 0],
                "tax_unit_id": [0, 0],
                "age": [30, 35],
                "employment_income": [50000, 60000],
                "person_weight": [1000.0, 1000.0],
            }
        ),
        weights="person_weight",
    )

    household_df = MicroDataFrame(
        pd.DataFrame(
            {
                "household_id": [0],
                "state_name": ["CA"],
                "household_weight": [1000.0],
            }
        ),
        weights="household_weight",
    )

    marital_unit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "marital_unit_id": [0],
                "marital_unit_weight": [1000.0],
            }
        ),
        weights="marital_unit_weight",
    )

    family_df = MicroDataFrame(
        pd.DataFrame(
            {
                "family_id": [0],
                "family_weight": [1000.0],
            }
        ),
        weights="family_weight",
    )

    spm_unit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "spm_unit_id": [0],
                "spm_unit_weight": [1000.0],
            }
        ),
        weights="spm_unit_weight",
    )

    tax_unit_df = MicroDataFrame(
        pd.DataFrame(
            {
                "tax_unit_id": [0],
                "tax_unit_weight": [1000.0],
            }
        ),
        weights="tax_unit_weight",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_simulation.h5")

        dataset = PolicyEngineUSDataset(
            name="Test Simulation Dataset",
            description="Dataset for testing simulation",
            filepath=filepath,
            year=2024,
            data=USYearData(
                person=person_df,
                household=household_df,
                marital_unit=marital_unit_df,
                family=family_df,
                spm_unit=spm_unit_df,
                tax_unit=tax_unit_df,
            ),
        )

        # Create and run simulation
        simulation = Simulation(
            dataset=dataset,
            tax_benefit_model_version=us_latest,
        )

        simulation.run()

        # Verify output dataset was created
        assert simulation.output_dataset is not None
        assert simulation.output_dataset.data is not None

        # Verify person data contains the expected variables
        person_output = pd.DataFrame(simulation.output_dataset.data.person)
        assert "person_id" in person_output.columns
        assert "age" in person_output.columns
        assert "employment_income" in person_output.columns
        assert len(person_output) == 2  # Should have 2 people

        # Verify employment income values match input
        assert person_output["employment_income"].tolist() == [
            50000,
            60000,
        ]
