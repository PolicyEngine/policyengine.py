"""Mainly simulation options and parameters."""

from policyengine_core.data import Dataset
from policyengine.utils.data_download import download
from typing import Tuple


def get_default_dataset(country: str, region: str) -> Tuple[Dataset, str]:
    if country == "uk":
        data_file, version = download(
            filepath="enhanced_frs_2022_23.h5",
            gcs_bucket="policyengine-uk-data-private",
            return_version=True,
        )
        time_period = None
    elif country == "us":
        if region is not None and region != "us":
            data_file, version = download(
                filepath="pooled_3_year_cps_2023.h5",
                gcs_bucket="policyengine-us-data",
                return_version=True,
            )
            time_period = 2023
        else:
            data_file, version = download(
                filepath="cps_2023.h5",
                gcs_bucket="policyengine-us-data",
                return_version=True,
            )
            time_period = 2023

    return (
        Dataset.from_file(
            file_path=data_file,
            time_period=time_period,
        ),
        version,
    )
