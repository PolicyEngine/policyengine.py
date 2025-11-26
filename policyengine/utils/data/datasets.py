"""Mainly simulation options and parameters."""

from typing import Tuple, Optional

US_DATA_BUCKET = "gs://policyengine-us-data"

EFRS_2023 = "gs://policyengine-uk-data-private/enhanced_frs_2023_24.h5"
FRS_2023 = "gs://policyengine-uk-data-private/frs_2023_24.h5"
CPS_2023 = f"{US_DATA_BUCKET}/cps_2023.h5"
CPS_2023_POOLED = f"{US_DATA_BUCKET}/pooled_3_year_cps_2023.h5"
ECPS_2024 = f"{US_DATA_BUCKET}/enhanced_cps_2024.h5"

POLICYENGINE_DATASETS = [
    EFRS_2023,
    FRS_2023,
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
        return EFRS_2023
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


def get_us_state_dataset_path(state_code: str) -> str:
    """
    Get the GCS path for a US state-level dataset.

    Args:
        state_code: Two-letter US state code (e.g., "CA", "NY").

    Returns:
        GCS path to the state dataset.
    """
    return f"{US_DATA_BUCKET}/states/{state_code.upper()}.h5"


def get_us_congressional_district_dataset_path(
    state_code: str, district_number: int
) -> str:
    """
    Get the GCS path for a US Congressional district-level dataset.

    Note: This is a theorized schema. The exact format of the district
    dataset filenames may change once the actual data is available.

    Args:
        state_code: Two-letter US state code (e.g., "CA", "NY").
        district_number: District number (1-52).

    Returns:
        GCS path to the Congressional district dataset.
    """
    return f"{US_DATA_BUCKET}/districts/{state_code.upper()}-{district_number:02d}.h5"
