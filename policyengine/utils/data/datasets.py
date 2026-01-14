"""Mainly simulation options and parameters."""

from typing import Tuple, Optional, Literal

from policyengine_core.tools.google_cloud import parse_gs_url

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
    country: str, region: str | None, version: Optional[str] = None
) -> str:
    if country == "uk":
        return EFRS_2023
    elif country == "us":
        return _get_default_us_dataset(region)

    raise ValueError(
        f"Unable to select a default dataset for country {country} and region {region}."
    )


def _get_default_us_dataset(region: str | None) -> str:
    """Get the default dataset for a US region."""
    region_type = determine_us_region_type(region)

    if region_type == "nationwide":
        return ECPS_2024
    elif region_type == "city":
        # TODO: Implement a better approach to this for our one
        # city, New York City.
        # Cities use the pooled CPS dataset
        return CPS_2023_POOLED

    # For state and congressional_district, region is guaranteed to be non-None
    assert region is not None

    if region_type == "state":
        state_code = region.split("/")[1]
        return get_us_state_dataset_path(state_code)
    elif region_type == "congressional_district":
        # Expected format: "congressional_district/CA-01"
        district_str = region.split("/")[1]
        state_code, district_num_str = district_str.split("-")
        district_number = int(district_num_str)
        return get_us_congressional_district_dataset_path(
            state_code, district_number
        )

    raise ValueError(f"Unhandled US region type: {region_type}")


def process_gs_path(path: str) -> Tuple[str, str, Optional[str]]:
    """
    Process a GS path to return bucket, object, and optional version.

    Supports:
      - gs://bucket/path/file.h5
      - gs://bucket/path/file.h5@1.2.3

    Args:
        path: A GCS URL in the format gs://bucket/path/to/file[@version]

    Returns:
        A tuple of (bucket, object_path, version) where version may be None.

    Raises:
        ValueError: If the path is not a valid gs:// URL.
    """
    return parse_gs_url(path)


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
    print(f"US_DATA_BUCKET in GET_DATASET_PATH: {US_DATA_BUCKET}")
    return f"{US_DATA_BUCKET}/districts/{state_code.upper()}-{district_number:02d}.h5"


USRegionType = Literal["nationwide", "city", "state", "congressional_district"]

US_REGION_PREFIXES = ("city", "state", "congressional_district")


def determine_us_region_type(region: str | None) -> USRegionType:
    """
    Determine the type of US region from a region string.

    Args:
        region: A region string (e.g., "us", "city/nyc", "state/CA",
                "congressional_district/CA-01") or None.

    Returns:
        One of "nationwide", "city", "state", or "congressional_district".

    Raises:
        ValueError: If the region string has an unrecognized prefix.
    """
    if region is None or region == "us":
        return "nationwide"

    for prefix in US_REGION_PREFIXES:
        if region.startswith(f"{prefix}/"):
            return prefix

    raise ValueError(
        f"Unrecognized US region format: '{region}'. "
        f"Expected 'us', or one of the following prefixes: {list(US_REGION_PREFIXES)}"
    )
