"""Tests for US dataset creation from HuggingFace paths."""

import shutil
from pathlib import Path

import pandas as pd

from policyengine.tax_benefit_models.us import (
    PolicyEngineUSDataset,
    create_datasets,
)


def test_create_datasets_from_enhanced_cps():
    """Test creating datasets from enhanced CPS HuggingFace path."""
    # Clean up data directory if it exists
    data_dir = Path("./data")
    if data_dir.exists():
        shutil.rmtree(data_dir)

    # Create datasets for a single year to test
    datasets = ["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"]
    years = [2024]

    create_datasets(datasets=datasets, years=years)

    # Verify the dataset was created
    dataset_file = data_dir / "enhanced_cps_2024_year_2024.h5"
    assert dataset_file.exists(), f"Dataset file {dataset_file} should exist"

    # Load and verify dataset structure
    dataset = PolicyEngineUSDataset(
        name="test",
        description="test",
        filepath=str(dataset_file),
        year=2024,
    )
    dataset.load()

    # Check all entity types exist
    assert dataset.data is not None
    assert dataset.data.person is not None
    assert dataset.data.household is not None
    assert dataset.data.marital_unit is not None
    assert dataset.data.family is not None
    assert dataset.data.spm_unit is not None
    assert dataset.data.tax_unit is not None

    # Check person data has required columns
    person_df = pd.DataFrame(dataset.data.person)
    assert "person_id" in person_df.columns
    assert "person_household_id" in person_df.columns
    assert "person_weight" in person_df.columns
    assert len(person_df) > 0

    # Check household data
    household_df = pd.DataFrame(dataset.data.household)
    assert "household_id" in household_df.columns
    assert "household_weight" in household_df.columns
    assert len(household_df) > 0

    # Check all group entities have weight columns
    for entity_name in [
        "marital_unit",
        "family",
        "spm_unit",
        "tax_unit",
    ]:
        entity_df = pd.DataFrame(getattr(dataset.data, entity_name))
        assert f"{entity_name}_id" in entity_df.columns
        assert f"{entity_name}_weight" in entity_df.columns
        assert len(entity_df) > 0

    # Clean up
    shutil.rmtree(data_dir)


def test_create_datasets_multiple_years():
    """Test creating datasets for multiple years."""
    # Clean up data directory if it exists
    data_dir = Path("./data")
    if data_dir.exists():
        shutil.rmtree(data_dir)

    datasets = ["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"]
    years = [2024, 2025]

    create_datasets(datasets=datasets, years=years)

    # Verify both year datasets were created
    for year in years:
        dataset_file = data_dir / f"enhanced_cps_2024_year_{year}.h5"
        assert dataset_file.exists(), (
            f"Dataset file for year {year} should exist"
        )

        # Load and verify
        dataset = PolicyEngineUSDataset(
            name=f"test-{year}",
            description=f"test {year}",
            filepath=str(dataset_file),
            year=year,
        )
        dataset.load()
        assert dataset.data is not None
        assert len(pd.DataFrame(dataset.data.person)) > 0

    # Clean up
    shutil.rmtree(data_dir)
