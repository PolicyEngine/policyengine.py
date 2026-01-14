from policyengine.simulation import SimulationOptions
from unittest.mock import patch, Mock
import pytest
from policyengine.utils.data.datasets import CPS_2023

non_data_uk_sim_options = {
    "country": "uk",
    "scope": "macro",
    "region": "uk",
    "time_period": 2025,
    "reform": None,
    "baseline": None,
}

non_data_us_sim_options = {
    "country": "us",
    "scope": "macro",
    "region": "us",
    "time_period": 2025,
    "reform": None,
    "baseline": None,
}

uk_sim_options_no_data = SimulationOptions.model_validate(
    {
        **non_data_uk_sim_options,
        "data": None,
    }
)

us_sim_options_cps_dataset = SimulationOptions.model_validate(
    {**non_data_us_sim_options, "data": CPS_2023}
)

SAMPLE_DATASET_FILENAME = "frs_2023_24.h5"
SAMPLE_DATASET_BUCKET_NAME = "policyengine-uk-data-private"
SAMPLE_DATASET_URI_PREFIX = "gs://"
SAMPLE_DATASET_FILE_ADDRESS = f"{SAMPLE_DATASET_URI_PREFIX}{SAMPLE_DATASET_BUCKET_NAME}/{SAMPLE_DATASET_FILENAME}"

uk_sim_options_pe_dataset = SimulationOptions.model_validate(
    {**non_data_uk_sim_options, "data": SAMPLE_DATASET_FILE_ADDRESS}
)


@pytest.fixture
def mock_get_default_dataset():
    with patch(
        "policyengine.simulation.get_default_dataset",
        return_value=SAMPLE_DATASET_FILE_ADDRESS,
    ) as mock_get_default_dataset:
        yield mock_get_default_dataset


@pytest.fixture
def mock_dataset():
    """Simple Dataset mock fixture"""
    with patch("policyengine.simulation.Dataset") as mock_dataset_class:
        mock_instance = Mock()
        # Set file_path to mimic Dataset's behavior of clipping URI and bucket name from GCS paths
        mock_instance.from_file = Mock()
        mock_instance.file_path = SAMPLE_DATASET_FILENAME
        mock_dataset_class.from_file.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_simulation_with_cliff_vars():

    mock_sim = Mock()
    mock_sim.calculate.side_effect = lambda var: {
        "cliff_gap": Mock(sum=Mock(return_value=100.0)),
        "is_on_cliff": Mock(sum=Mock(return_value=40.0)),
        "is_adult": Mock(sum=Mock(return_value=80.0)),
    }[var]
    return mock_sim


def create_mock_single_economy(
    household_net_income: list[float],
    household_weight: list[float],
    congressional_district_geoid: list[int] | None = None,
):
    """Create a mock SingleEconomy with specified household data.

    Args:
        household_net_income: List of household net incomes
        household_weight: List of household weights
        congressional_district_geoid: List of district geoids (SSDD format) or None

    Returns:
        Mock SingleEconomy object with the specified data
    """
    mock_economy = Mock()
    mock_economy.household_net_income = household_net_income
    mock_economy.household_weight = household_weight
    mock_economy.congressional_district_geoid = congressional_district_geoid
    return mock_economy


@pytest.fixture
def mock_single_economy_with_ga_districts():
    """Mock SingleEconomy with Georgia congressional district data.

    Creates 6 households across 2 districts:
    - GA-05 (geoid 1305): 3 households
    - GA-06 (geoid 1306): 3 households
    """
    return create_mock_single_economy(
        household_net_income=[
            50000.0,
            60000.0,
            70000.0,
            80000.0,
            90000.0,
            100000.0,
        ],
        household_weight=[1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
        congressional_district_geoid=[1305, 1305, 1305, 1306, 1306, 1306],
    )


@pytest.fixture
def mock_single_economy_with_multi_state_districts():
    """Mock SingleEconomy with districts from multiple states.

    Creates 8 households across 4 districts in 2 states:
    - GA-05 (geoid 1305): 2 households
    - GA-06 (geoid 1306): 2 households
    - NC-04 (geoid 3704): 2 households
    - NC-12 (geoid 3712): 2 households
    """
    return create_mock_single_economy(
        household_net_income=[
            50000.0,
            60000.0,
            70000.0,
            80000.0,
            40000.0,
            45000.0,
            55000.0,
            65000.0,
        ],
        household_weight=[
            1000.0,
            1000.0,
            1000.0,
            1000.0,
            1000.0,
            1000.0,
            1000.0,
            1000.0,
        ],
        congressional_district_geoid=[
            1305,
            1305,
            1306,
            1306,
            3704,
            3704,
            3712,
            3712,
        ],
    )


@pytest.fixture
def mock_single_economy_without_districts():
    """Mock SingleEconomy with no congressional district data (all zeros)."""
    return create_mock_single_economy(
        household_net_income=[50000.0, 60000.0, 70000.0],
        household_weight=[1000.0, 1000.0, 1000.0],
        congressional_district_geoid=[0, 0, 0],
    )


@pytest.fixture
def mock_single_economy_with_null_districts():
    """Mock SingleEconomy with None congressional district data."""
    return create_mock_single_economy(
        household_net_income=[50000.0, 60000.0, 70000.0],
        household_weight=[1000.0, 1000.0, 1000.0],
        congressional_district_geoid=None,
    )
