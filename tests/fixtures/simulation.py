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
