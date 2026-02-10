"""US region registry builder.

This module builds the complete US region registry from the data definitions
in the data/ subdirectory:
- data/states.py: State definitions
- data/districts.py: Congressional district counts
- data/places.py: Census places over 100K population
"""

from policyengine.core.region import Region, RegionRegistry

from .data import AT_LARGE_STATES, DISTRICT_COUNTS, US_PLACES, US_STATES

US_DATA_BUCKET = "gs://policyengine-us-data"


def _ordinal(n: int) -> str:
    """Return ordinal suffix for a number (1st, 2nd, 3rd, etc.)."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def build_us_region_registry() -> RegionRegistry:
    """Build the complete US region registry.

    Returns:
        RegionRegistry containing:
        - 1 national region
        - 51 state regions (50 states + DC)
        - 436 congressional district regions (435 + DC delegate)
        - 333 place/city regions (Census places over 100K population)
    """
    regions: list[Region] = []

    # 1. National region (has dedicated dataset)
    regions.append(
        Region(
            code="us",
            label="United States",
            region_type="national",
            dataset_path=f"{US_DATA_BUCKET}/enhanced_cps_2024.h5",
        )
    )

    # 2. State regions (each has dedicated dataset)
    for abbrev, name in US_STATES.items():
        regions.append(
            Region(
                code=f"state/{abbrev.lower()}",
                label=name,
                region_type="state",
                parent_code="us",
                dataset_path=f"{US_DATA_BUCKET}/states/{abbrev}.h5",
                state_code=abbrev,
                state_name=name,
            )
        )

    # 3. Congressional district regions (each has dedicated dataset)
    for state_abbrev, count in DISTRICT_COUNTS.items():
        state_name = US_STATES[state_abbrev]
        for i in range(1, count + 1):
            district_code = f"{state_abbrev}-{i:02d}"

            # Create appropriate label
            if state_abbrev in AT_LARGE_STATES:
                label = f"{state_name}'s at-large congressional district"
            else:
                label = f"{state_name}'s {_ordinal(i)} congressional district"

            regions.append(
                Region(
                    code=f"congressional_district/{district_code}",
                    label=label,
                    region_type="congressional_district",
                    parent_code=f"state/{state_abbrev.lower()}",
                    dataset_path=f"{US_DATA_BUCKET}/districts/{district_code}.h5",
                    state_code=state_abbrev,
                    state_name=state_name,
                )
            )

    # 4. Place/city regions (filter from state datasets)
    for place in US_PLACES:
        state_abbrev = place["state"]
        fips = place["fips"]
        regions.append(
            Region(
                code=f"place/{state_abbrev}-{fips}",
                label=place["name"],
                region_type="place",
                parent_code=f"state/{state_abbrev.lower()}",
                requires_filter=True,
                filter_field="place_fips",
                filter_value=fips,
                state_code=state_abbrev,
                state_name=place["state_name"],
            )
        )

    return RegionRegistry(country_id="us", regions=regions)


# Singleton instance for import
us_region_registry = build_us_region_registry()
