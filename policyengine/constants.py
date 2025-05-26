"""Mainly simulation options and parameters."""

from policyengine_core.data import Dataset
from policyengine.utils.data_download import download
from typing import Tuple


def get_default_dataset(
    country: str, region: str, version: str | None = None
) -> str:
    if country == "uk":
        return "gcs://policyengine-uk-data-private/enhanced_frs_2022_23.h5"
    elif country == "us":
        if region is not None and region != "us":
            return "gcs://policyengine-us-data/pooled_3_year_cps_2023.h5"
        else:
            return "gcs://policyengine-us-data/cps_2023.h5"

    raise ValueError(
        f"Unable to select a default dataset for country {country} and region {region}."
    )
