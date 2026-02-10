"""Fixtures for testing dataset filtering functionality."""

import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.tax_benefit_models.uk.datasets import (
    PolicyEngineUKDataset,
    UKYearData,
)
from policyengine.tax_benefit_models.us.datasets import (
    PolicyEngineUSDataset,
    USYearData,
)


def create_us_test_dataset() -> PolicyEngineUSDataset:
    """Create a minimal US dataset for filtering tests.

    Creates a dataset with 6 persons across 3 households:
    - Household 1 (place_fips="44000"): 2 persons
    - Household 2 (place_fips="44000"): 2 persons
    - Household 3 (place_fips="57000"): 2 persons
    """
    # Person data - 6 persons across 3 households
    person_data = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5, 6],
            "household_id": [1, 1, 2, 2, 3, 3],
            "tax_unit_id": [1, 1, 2, 2, 3, 3],
            "spm_unit_id": [1, 1, 2, 2, 3, 3],
            "family_id": [1, 1, 2, 2, 3, 3],
            "marital_unit_id": [1, 1, 2, 2, 3, 3],
            "person_weight": [1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
            "age": [35, 30, 45, 40, 25, 28],
        }
    )

    # Household data - 3 households, 2 in place 44000, 1 in place 57000
    household_data = pd.DataFrame(
        {
            "household_id": [1, 2, 3],
            "household_weight": [1000.0, 1000.0, 1000.0],
            "place_fips": ["44000", "44000", "57000"],
            "state_fips": [6, 6, 34],  # CA, CA, NJ
        }
    )

    # Tax unit data
    tax_unit_data = pd.DataFrame(
        {
            "tax_unit_id": [1, 2, 3],
            "tax_unit_weight": [1000.0, 1000.0, 1000.0],
        }
    )

    # SPM unit data
    spm_unit_data = pd.DataFrame(
        {
            "spm_unit_id": [1, 2, 3],
            "spm_unit_weight": [1000.0, 1000.0, 1000.0],
        }
    )

    # Family data
    family_data = pd.DataFrame(
        {
            "family_id": [1, 2, 3],
            "family_weight": [1000.0, 1000.0, 1000.0],
        }
    )

    # Marital unit data
    marital_unit_data = pd.DataFrame(
        {
            "marital_unit_id": [1, 2, 3],
            "marital_unit_weight": [1000.0, 1000.0, 1000.0],
        }
    )

    return PolicyEngineUSDataset(
        id="test_us_dataset",
        name="Test US Dataset",
        description="Test dataset for filtering",
        filepath="/tmp/test_us.h5",
        year=2024,
        is_output_dataset=False,
        data=USYearData(
            person=MicroDataFrame(person_data, weights="person_weight"),
            household=MicroDataFrame(
                household_data, weights="household_weight"
            ),
            tax_unit=MicroDataFrame(tax_unit_data, weights="tax_unit_weight"),
            spm_unit=MicroDataFrame(spm_unit_data, weights="spm_unit_weight"),
            family=MicroDataFrame(family_data, weights="family_weight"),
            marital_unit=MicroDataFrame(
                marital_unit_data, weights="marital_unit_weight"
            ),
        ),
    )


def create_uk_test_dataset() -> PolicyEngineUKDataset:
    """Create a minimal UK dataset for filtering tests.

    Creates a dataset with 6 persons across 3 households:
    - Household 1 (country="ENGLAND"): 2 persons
    - Household 2 (country="ENGLAND"): 2 persons
    - Household 3 (country="SCOTLAND"): 2 persons
    """
    # Person data - 6 persons across 3 households
    person_data = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4, 5, 6],
            "benunit_id": [1, 1, 2, 2, 3, 3],
            "household_id": [1, 1, 2, 2, 3, 3],
            "person_weight": [1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
            "age": [35, 30, 45, 40, 25, 28],
        }
    )

    # Benunit data
    benunit_data = pd.DataFrame(
        {
            "benunit_id": [1, 2, 3],
            "benunit_weight": [1000.0, 1000.0, 1000.0],
        }
    )

    # Household data - 3 households, 2 in England, 1 in Scotland
    household_data = pd.DataFrame(
        {
            "household_id": [1, 2, 3],
            "household_weight": [1000.0, 1000.0, 1000.0],
            "country": ["ENGLAND", "ENGLAND", "SCOTLAND"],
        }
    )

    return PolicyEngineUKDataset(
        id="test_uk_dataset",
        name="Test UK Dataset",
        description="Test dataset for filtering",
        filepath="/tmp/test_uk.h5",
        year=2024,
        is_output_dataset=False,
        data=UKYearData(
            person=MicroDataFrame(person_data, weights="person_weight"),
            benunit=MicroDataFrame(benunit_data, weights="benunit_weight"),
            household=MicroDataFrame(
                household_data, weights="household_weight"
            ),
        ),
    )


@pytest.fixture
def us_test_dataset() -> PolicyEngineUSDataset:
    """Pytest fixture for US test dataset."""
    return create_us_test_dataset()


@pytest.fixture
def uk_test_dataset() -> PolicyEngineUKDataset:
    """Pytest fixture for UK test dataset."""
    return create_uk_test_dataset()
