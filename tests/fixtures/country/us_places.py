"""Test fixtures for US place-level filtering tests."""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock


def create_mock_simulation_with_place_fips(
    place_fips_values: list[str],
    household_ids: list[int] | None = None,
) -> Mock:
    """Create a mock simulation with place_fips data.

    Args:
        place_fips_values: List of place FIPS codes for each household.
        household_ids: Optional list of household IDs.

    Returns:
        Mock simulation object with calculate() and to_input_dataframe() configured.
    """
    if household_ids is None:
        household_ids = list(range(len(place_fips_values)))

    mock_sim = Mock()

    # Mock calculate to return place_fips values
    mock_calculate_result = Mock()
    mock_calculate_result.values = np.array(place_fips_values)
    mock_sim.calculate.return_value = mock_calculate_result

    # Mock to_input_dataframe to return a DataFrame
    df = pd.DataFrame(
        {
            "household_id": household_ids,
            "place_fips": place_fips_values,
        }
    )
    mock_sim.to_input_dataframe.return_value = df

    return mock_sim


def create_mock_simulation_with_bytes_place_fips(
    place_fips_values: list[bytes],
    household_ids: list[int] | None = None,
) -> Mock:
    """Create a mock simulation with bytes place_fips data (as from HDF5).

    Args:
        place_fips_values: List of place FIPS codes as bytes.
        household_ids: Optional list of household IDs.

    Returns:
        Mock simulation object with calculate() and to_input_dataframe() configured.
    """
    if household_ids is None:
        household_ids = list(range(len(place_fips_values)))

    mock_sim = Mock()

    mock_calculate_result = Mock()
    mock_calculate_result.values = np.array(place_fips_values)
    mock_sim.calculate.return_value = mock_calculate_result

    df = pd.DataFrame(
        {
            "household_id": household_ids,
            "place_fips": place_fips_values,
        }
    )
    mock_sim.to_input_dataframe.return_value = df

    return mock_sim


@pytest.fixture
def mini_place_dataset() -> pd.DataFrame:
    """Create a mini dataset with place_fips for testing.

    Simulates 10 households across 3 NJ places:
    - Paterson (57000): 4 households (IDs: 0, 1, 4, 7)
    - Newark (51000): 3 households (IDs: 2, 5, 8)
    - Jersey City (36000): 3 households (IDs: 3, 6, 9)

    Returns:
        DataFrame with household_id, place_fips, household_weight,
        and household_net_income columns.
    """
    return pd.DataFrame(
        {
            "household_id": list(range(10)),
            "place_fips": [
                "57000",  # Paterson
                "57000",  # Paterson
                "51000",  # Newark
                "36000",  # Jersey City
                "57000",  # Paterson
                "51000",  # Newark
                "36000",  # Jersey City
                "57000",  # Paterson
                "51000",  # Newark
                "36000",  # Jersey City
            ],
            "household_weight": [
                1000.0,
                1500.0,
                2000.0,
                1200.0,
                800.0,
                1800.0,
                1100.0,
                900.0,
                1400.0,
                1300.0,
            ],
            "household_net_income": [
                50000.0,
                60000.0,
                75000.0,
                45000.0,
                55000.0,
                80000.0,
                40000.0,
                65000.0,
                70000.0,
                48000.0,
            ],
        }
    )


@pytest.fixture
def mini_place_dataset_with_bytes() -> pd.DataFrame:
    """Create a mini dataset with bytes place_fips (as from HDF5).

    Simulates 4 households across 2 NJ places with bytes-encoded FIPS:
    - Paterson (b"57000"): 2 households (IDs: 0, 1)
    - Newark (b"51000"): 2 households (IDs: 2, 3)

    Returns:
        DataFrame with household_id, place_fips (as bytes), and household_weight.
    """
    return pd.DataFrame(
        {
            "household_id": [0, 1, 2, 3],
            "place_fips": [b"57000", b"57000", b"51000", b"51000"],
            "household_weight": [1000.0, 1000.0, 1000.0, 1000.0],
        }
    )
