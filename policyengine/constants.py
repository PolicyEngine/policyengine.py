"""Mainly simulation options and parameters."""

from policyengine_core.data import Dataset
from policyengine.utils.data_download import download
from typing import Tuple, Optional

EFRS_2022 = "gcs://policyengine-uk-data-private/enhanced_frs_2022_23.h5"
FRS_2022 = "gcs://policyengine-uk-data-private/frs_2022_23.h5"
CPS_2023_POOLED = "gcs://policyengine-us-data/pooled_3_year_cps_2023.h5"
CPS_2023 = "gcs://policyengine-us-data/cps_2023.h5"
ECPS_2024 = "gcs://policyengine-us-data/ecps_2024.h5"


def get_default_dataset(
    country: str, region: str, version: Optional[str] = None
) -> str:
    if country == "uk":
        return EFRS_2022
    elif country == "us":
        if region is not None and region != "us":
            return CPS_2023_POOLED
        else:
            return CPS_2023

    raise ValueError(
        f"Unable to select a default dataset for country {country} and region {region}."
    )
