"""Fixtures for Region and RegionRegistry tests."""

import pytest

from policyengine.core.region import Region, RegionRegistry


def create_national_region(
    country_code: str = "us",
    label: str = "United States",
    dataset_path: str = "gs://policyengine-us-data/enhanced_cps_2024.h5",
) -> Region:
    """Create a national region."""
    return Region(
        code=country_code,
        label=label,
        region_type="national",
        dataset_path=dataset_path,
    )


def create_state_region(
    state_code: str,
    state_name: str,
    parent_code: str = "us",
    bucket: str = "gs://policyengine-us-data",
) -> Region:
    """Create a state region with dedicated dataset."""
    return Region(
        code=f"state/{state_code.lower()}",
        label=state_name,
        region_type="state",
        parent_code=parent_code,
        dataset_path=f"{bucket}/states/{state_code}.h5",
        state_code=state_code,
        state_name=state_name,
    )


def create_place_region(
    state_code: str,
    fips: str,
    name: str,
    state_name: str,
) -> Region:
    """Create a place region that filters from parent state."""
    return Region(
        code=f"place/{state_code}-{fips}",
        label=name,
        region_type="place",
        parent_code=f"state/{state_code.lower()}",
        requires_filter=True,
        filter_field="place_fips",
        filter_value=fips,
        state_code=state_code,
        state_name=state_name,
    )


def create_sample_us_registry() -> RegionRegistry:
    """Create a minimal US-like registry for testing.

    Contains:
    - 1 national region (US)
    - 2 state regions (CA, NY)
    - 1 place region (Los Angeles)
    """
    return RegionRegistry(
        country_id="us",
        regions=[
            create_national_region(),
            create_state_region("CA", "California"),
            create_state_region("NY", "New York"),
            create_place_region(
                "CA", "44000", "Los Angeles city", "California"
            ),
        ],
    )


# Pre-built fixtures for common test scenarios

NATIONAL_US = create_national_region()

STATE_CALIFORNIA = create_state_region("CA", "California")

STATE_NEW_YORK = create_state_region("NY", "New York")

PLACE_LOS_ANGELES = create_place_region(
    "CA", "44000", "Los Angeles city", "California"
)

SIMPLE_REGION = Region(
    code="state/ca",
    label="California",
    region_type="state",
)

REGION_WITH_DATASET = Region(
    code="state/ca",
    label="California",
    region_type="state",
    parent_code="us",
    dataset_path="gs://policyengine-us-data/states/CA.h5",
    state_code="CA",
    state_name="California",
)

FILTER_REGION = Region(
    code="place/NJ-57000",
    label="Paterson",
    region_type="place",
    parent_code="state/nj",
    requires_filter=True,
    filter_field="place_fips",
    filter_value="57000",
    state_code="NJ",
    state_name="New Jersey",
)


@pytest.fixture
def sample_registry() -> RegionRegistry:
    """Pytest fixture for a sample US-like registry."""
    return create_sample_us_registry()


@pytest.fixture
def empty_registry() -> RegionRegistry:
    """Pytest fixture for an empty registry."""
    return RegionRegistry(country_id="test", regions=[])
