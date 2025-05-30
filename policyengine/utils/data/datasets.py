"""Mainly simulation options and parameters."""

from typing import Tuple, Optional

EFRS_2022 = "gs://policyengine-uk-data-private/enhanced_frs_2022_23.h5"
FRS_2022 = "gs://policyengine-uk-data-private/frs_2022_23.h5"
CPS_2023 = "gs://policyengine-us-data/cps_2023.h5"
CPS_2023_POOLED = "gs://policyengine-us-data/pooled_3_year_cps_2023.h5"
ECPS_2024 = "gs://policyengine-us-data/ecps_2024.h5"

POLICYENGINE_DATASETS = [
    EFRS_2022,
    FRS_2022,
    CPS_2023,
    CPS_2023_POOLED,
    ECPS_2024,
]

# Contains datasets that map to particular time_period values
DATASET_TIME_PERIODS = {
    CPS_2023: 2023,
    CPS_2023_POOLED: 2023,
    ECPS_2024: 2023,
}


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


def process_gs_path(path: str) -> Tuple[str, str]:
    """Process a GS path to return bucket and object."""
    if not path.startswith("gs://"):
        raise ValueError(f"Invalid GS path: {path}")

    path = path[5:]  # Remove 'gs://'
    bucket, obj = path.split("/", 1)
    return bucket, obj
