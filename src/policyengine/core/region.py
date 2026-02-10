"""Region definitions for geographic simulations.

This module provides the Region and RegionRegistry classes for defining
geographic regions that a tax-benefit model supports. Regions can have:
1. A dedicated dataset (e.g., US states, congressional districts)
2. Filter from a parent region's dataset (e.g., US places/cities, UK countries)
"""

from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr

# Region type literals for US and UK
USRegionType = Literal["national", "state", "congressional_district", "place"]
UKRegionType = Literal["national", "country", "constituency", "local_authority"]
RegionType = USRegionType | UKRegionType


class Region(BaseModel):
    """Geographic region for tax-benefit simulations.

    Regions can either have:
    1. A dedicated dataset (dataset_path is set, requires_filter is False)
    2. Filter from a parent region's dataset (requires_filter is True)

    The unique identifier is the code field, which uses a prefixed format:
    - National: "us", "uk"
    - State: "state/ca", "state/ny"
    - Congressional District: "congressional_district/CA-01"
    - Place: "place/NJ-57000"
    - UK Country: "country/england"
    - Constituency: "constituency/Sheffield Central"
    - Local Authority: "local_authority/E09000001"
    """

    # Core identification
    code: str = Field(
        ...,
        description="Unique region code with type prefix (e.g., 'state/ca', 'place/NJ-57000')",
    )
    label: str = Field(..., description="Human-readable label (e.g., 'California')")
    region_type: RegionType = Field(
        ..., description="Type of region (e.g., 'state', 'place')"
    )

    # Hierarchy
    parent_code: str | None = Field(
        default=None,
        description="Code of parent region (e.g., 'us' for states, 'state/nj' for places in New Jersey)",
    )

    # Dataset configuration
    dataset_path: str | None = Field(
        default=None,
        description="GCS path to dedicated dataset (e.g., 'gs://policyengine-us-data/states/CA.h5')",
    )

    # Filtering configuration (for regions that filter from parent datasets)
    requires_filter: bool = Field(
        default=False,
        description="True if this region filters from a parent dataset rather than having its own",
    )
    filter_field: str | None = Field(
        default=None,
        description="Dataset field to filter on (e.g., 'place_fips', 'country')",
    )
    filter_value: str | None = Field(
        default=None,
        description="Value to match when filtering (defaults to code suffix if not set)",
    )

    # Metadata (primarily for US congressional districts)
    state_code: str | None = Field(
        default=None, description="Two-letter state code (e.g., 'CA', 'NJ')"
    )
    state_name: str | None = Field(
        default=None, description="Full state name (e.g., 'California', 'New Jersey')"
    )

    def __hash__(self) -> int:
        """Hash by code for use in sets and dict keys."""
        return hash(self.code)

    def __eq__(self, other: object) -> bool:
        """Equality by code."""
        if not isinstance(other, Region):
            return False
        return self.code == other.code


class RegionRegistry(BaseModel):
    """Registry of all regions for a country model.

    Provides indexed lookups for regions by code and type.
    Indices are rebuilt automatically after initialization.
    """

    country_id: str = Field(..., description="Country identifier (e.g., 'us', 'uk')")
    regions: list[Region] = Field(default_factory=list)

    # Private indexed lookups (excluded from serialization)
    _by_code: dict[str, Region] = PrivateAttr(default_factory=dict)
    _by_type: dict[str, list[Region]] = PrivateAttr(default_factory=dict)

    def model_post_init(self, __context: object) -> None:
        """Build lookup indices after initialization."""
        self._rebuild_indices()

    def _rebuild_indices(self) -> None:
        """Rebuild all lookup indices from the regions list."""
        self._by_code = {}
        self._by_type = {}

        for region in self.regions:
            # Index by code
            self._by_code[region.code] = region

            # Index by type
            if region.region_type not in self._by_type:
                self._by_type[region.region_type] = []
            self._by_type[region.region_type].append(region)

    def add_region(self, region: Region) -> None:
        """Add a region to the registry and update indices."""
        self.regions.append(region)
        self._by_code[region.code] = region
        if region.region_type not in self._by_type:
            self._by_type[region.region_type] = []
        self._by_type[region.region_type].append(region)

    def get(self, code: str) -> Region | None:
        """Get a region by its code.

        Args:
            code: Region code (e.g., 'state/ca', 'place/NJ-57000')

        Returns:
            The Region if found, None otherwise
        """
        return self._by_code.get(code)

    def get_by_type(self, region_type: str) -> list[Region]:
        """Get all regions of a given type.

        Args:
            region_type: Type to filter by (e.g., 'state', 'place')

        Returns:
            List of regions with the given type
        """
        return self._by_type.get(region_type, [])

    def get_national(self) -> Region | None:
        """Get the national-level region.

        Returns:
            The national Region if found, None otherwise
        """
        national = self.get_by_type("national")
        return national[0] if national else None

    def get_children(self, parent_code: str) -> list[Region]:
        """Get all regions with a given parent code.

        Args:
            parent_code: Parent region code to filter by

        Returns:
            List of regions with the given parent
        """
        return [r for r in self.regions if r.parent_code == parent_code]

    def get_dataset_regions(self) -> list[Region]:
        """Get all regions that have dedicated datasets.

        Returns:
            List of regions with dataset_path set and requires_filter False
        """
        return [
            r for r in self.regions if r.dataset_path is not None and not r.requires_filter
        ]

    def get_filter_regions(self) -> list[Region]:
        """Get all regions that require filtering from parent datasets.

        Returns:
            List of regions with requires_filter True
        """
        return [r for r in self.regions if r.requires_filter]

    def __len__(self) -> int:
        """Return the number of regions in the registry."""
        return len(self.regions)

    def __iter__(self):
        """Iterate over regions."""
        return iter(self.regions)

    def __contains__(self, code: str) -> bool:
        """Check if a region code exists in the registry."""
        return code in self._by_code
