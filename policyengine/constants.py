"""Mainly simulation options and parameters."""

from policyengine_core.data import Dataset
from policyengine.utils.data_download import download

SUPPORTED_COUNTRY_IDS = [
    "us",
    "uk",
]

UNSUPPORTED_COUNTRY_IDS = [
    "ca",
    "il",
    "ng",
]

SUPPORTED_COUNTRY_PACKAGES = [
    f"policyengine_{country}" for country in SUPPORTED_COUNTRY_IDS
]
UNSUPPORTED_COUNTRY_PACKAGES = [
    f"policyengine_{country}" if country != "ca" else "policyengine_canada"
    for country in UNSUPPORTED_COUNTRY_IDS
]

ALL_COUNTRY_PACKAGES = (
    SUPPORTED_COUNTRY_PACKAGES + UNSUPPORTED_COUNTRY_PACKAGES
)

# Datasets

ENHANCED_FRS = "hf://policyengine/policyengine-uk-data/enhanced_frs_2022_23.h5"
FRS = "hf://policyengine/policyengine-uk-data/frs_2022_23.h5"
ENHANCED_CPS = "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"
CPS = "hf://policyengine/policyengine-us-data/cps_2023.h5"
POOLED_CPS = "hf://policyengine/policyengine-us-data/pooled_3_year_cps_2023.h5"


def get_default_dataset(country: str, region: str):
    if country == "uk":
        data_file = download(
            filepath="enhanced_frs_2022_23.h5",
            huggingface_repo="policyengine-uk-data",
            gcs_bucket="policyengine-uk-data-private",
        )
        time_period = None
    elif country == "us":
        if region is not None and region != "us":
            data_file = download(
                filepath="pooled_3_year_cps_2023.h5",
                huggingface_repo="policyengine-us-data",
                gcs_bucket="policyengine-us-data",
            )
            time_period = 2023
        else:
            data_file = download(
                filepath="cps_2023.h5",
                huggingface_repo="policyengine-us-data",
                gcs_bucket="policyengine-us-data",
            )
            time_period = 2023

    return Dataset.from_file(
        file_path=data_file,
        time_period=time_period,
    )
