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

SAMPLE_DATASET_FILENAME = "sample_value.h5"
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
