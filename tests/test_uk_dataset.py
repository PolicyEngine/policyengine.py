import pandas as pd
import tempfile
import os
from policyengine.tax_benefit_models.uk import PolicyEngineUKDataset, YearData


def test_save_and_load_single_year():
    """Test saving and loading a dataset with a single year."""
    # Create sample data
    person_df = pd.DataFrame({
        'person_id': [1, 2, 3],
        'age': [25, 30, 35],
        'income': [30000, 45000, 60000]
    })

    benunit_df = pd.DataFrame({
        'benunit_id': [1, 2],
        'size': [2, 1],
        'total_income': [75000, 60000]
    })

    household_df = pd.DataFrame({
        'household_id': [1],
        'num_people': [3],
        'rent': [1200]
    })

    # Create dataset
    dataset = PolicyEngineUKDataset(
        name='Test Dataset',
        description='A test dataset',
        filepath='test.h5',
        data={
            2025: YearData(
                person=person_df,
                benunit=benunit_df,
                household=household_df
            )
        }
    )

    # Save to temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_dataset.h5')
        dataset.save(filepath)

        # Load it back
        loaded = PolicyEngineUKDataset.load(
            filepath,
            name='Loaded Dataset',
            description='Loaded from file'
        )

        # Verify data
        assert 2025 in loaded.data
        pd.testing.assert_frame_equal(loaded.data[2025].person, person_df)
        pd.testing.assert_frame_equal(loaded.data[2025].benunit, benunit_df)
        pd.testing.assert_frame_equal(loaded.data[2025].household, household_df)


def test_save_and_load_multiple_years():
    """Test saving and loading a dataset with multiple years."""
    # Create sample data for 2025
    person_2025 = pd.DataFrame({
        'person_id': [1, 2],
        'age': [25, 30],
        'income': [30000, 45000]
    })

    benunit_2025 = pd.DataFrame({
        'benunit_id': [1],
        'size': [2],
        'total_income': [75000]
    })

    household_2025 = pd.DataFrame({
        'household_id': [1],
        'num_people': [2],
        'rent': [1200]
    })

    # Create sample data for 2026
    person_2026 = pd.DataFrame({
        'person_id': [1, 2, 3],
        'age': [26, 31, 22],
        'income': [32000, 47000, 28000]
    })

    benunit_2026 = pd.DataFrame({
        'benunit_id': [1, 2],
        'size': [2, 1],
        'total_income': [79000, 28000]
    })

    household_2026 = pd.DataFrame({
        'household_id': [1],
        'num_people': [3],
        'rent': [1300]
    })

    # Create dataset with multiple years
    dataset = PolicyEngineUKDataset(
        name='Multi-year Dataset',
        description='Dataset with multiple years',
        filepath='test.h5',
        data={
            2025: YearData(
                person=person_2025,
                benunit=benunit_2025,
                household=household_2025
            ),
            2026: YearData(
                person=person_2026,
                benunit=benunit_2026,
                household=household_2026
            )
        }
    )

    # Save and load
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'multi_year_dataset.h5')
        dataset.save(filepath)

        loaded = PolicyEngineUKDataset.load(
            filepath,
            name='Loaded Multi-year',
            description='Loaded from file'
        )

        # Verify both years exist
        assert 2025 in loaded.data
        assert 2026 in loaded.data

        # Verify 2025 data
        pd.testing.assert_frame_equal(loaded.data[2025].person, person_2025)
        pd.testing.assert_frame_equal(loaded.data[2025].benunit, benunit_2025)
        pd.testing.assert_frame_equal(loaded.data[2025].household, household_2025)

        # Verify 2026 data
        pd.testing.assert_frame_equal(loaded.data[2026].person, person_2026)
        pd.testing.assert_frame_equal(loaded.data[2026].benunit, benunit_2026)
        pd.testing.assert_frame_equal(loaded.data[2026].household, household_2026)


def test_empty_dataset():
    """Test creating and saving an empty dataset."""
    dataset = PolicyEngineUKDataset(
        name='Empty Dataset',
        description='No data yet',
        filepath='empty.h5',
        data={}
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'empty_dataset.h5')
        dataset.save(filepath)

        loaded = PolicyEngineUKDataset.load(
            filepath,
            name='Loaded Empty',
            description='Empty dataset loaded'
        )

        assert len(loaded.data) == 0
