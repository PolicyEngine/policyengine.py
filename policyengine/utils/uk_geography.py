"""Utilities for UK geographic region filtering."""

from typing import Literal

UKRegionType = Literal["uk", "country", "constituency", "local_authority"]

UK_REGION_TYPES: tuple[UKRegionType, ...] = (
    "uk",
    "country",
    "constituency",
    "local_authority",
)


def determine_uk_region_type(region: str | None) -> UKRegionType:
    """
    Determine the type of UK region from a region string.

    Args:
        region: A region string (e.g., "country/scotland", "constituency/Aberdeen North",
                "local_authority/leicester") or None.

    Returns:
        One of "uk", "country", "constituency", or "local_authority".

    Raises:
        ValueError: If the region prefix is not a valid UK region type.
    """
    if region is None:
        return "uk"

    prefix = region.split("/")[0]
    if prefix not in UK_REGION_TYPES:
        raise ValueError(
            f"Invalid UK region type: '{prefix}'. "
            f"Expected one of: {list(UK_REGION_TYPES)}"
        )

    return prefix


def get_country_from_code(code: str) -> str | None:
    """Get country name from geographic code prefix (E, S, W, N)."""
    prefix_map = {
        "E": "england",
        "S": "scotland",
        "W": "wales",
        "N": "northern_ireland",
    }
    return prefix_map.get(code[0])


def should_zero_constituency(region: str | None, code: str, name: str) -> bool:
    """Return True if this constituency's impacts should be zeroed out."""
    region_type = determine_uk_region_type(region)

    if region_type == "uk":
        return False
    if region_type == "country":
        target = region.split("/")[1]
        return get_country_from_code(code) != target
    if region_type == "constituency":
        target = region.split("/")[1]
        return code != target and name != target
    if region_type == "local_authority":
        return True
    return False


def should_zero_local_authority(region: str | None, code: str, name: str) -> bool:
    """Return True if this local authority's impacts should be zeroed out."""
    region_type = determine_uk_region_type(region)

    if region_type == "uk":
        return False
    if region_type == "country":
        target = region.split("/")[1]
        return get_country_from_code(code) != target
    if region_type == "local_authority":
        target = region.split("/")[1]
        return code != target and name != target
    if region_type == "constituency":
        return True
    return False
