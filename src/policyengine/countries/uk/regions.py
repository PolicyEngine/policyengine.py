"""UK region definitions.

This module defines all UK geographic regions:
- National (1)
- Countries (4: England, Scotland, Wales, Northern Ireland)
- Constituencies (650, from the packaged 2024 list)
- Local Authorities (361, from the packaged April 2023 list)

Note: Constituencies and local authorities filter household rows on the
geography columns each household carries (``constituency_code_oa`` and
``la_code_oa``). This keeps subnational scoping tied to the dataset rows, not
to a separate weight matrix whose household dimension can drift from the
default dataset. They load the dataset the certified bundle routes them to
(``region_datasets``), and the national dataset when it routes none.

Their codes, names and hex positions come from the area lists shipped with the
package (``data/uk_geography``), so building them needs no network access.
"""

import csv
import logging
from typing import TYPE_CHECKING, Optional

from policyengine.core.region import Region, RegionRegistry
from policyengine.core.scoping_strategy import RowFilterStrategy
from policyengine.data.uk_geography_assets import (
    UK_GEOGRAPHY_BUCKET_URI,
    packaged_uk_area_list_path,
)
from policyengine.provenance import manifest as release_manifest
from policyengine.provenance.manifest import resolve_region_dataset_path

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

UK_DATA_BUCKET = UK_GEOGRAPHY_BUCKET_URI

# UK countries
UK_COUNTRIES = {
    "england": "England",
    "scotland": "Scotland",
    "wales": "Wales",
    "northern_ireland": "Northern Ireland",
}

# Stored names from policyengine_uk's Region enum. England spans nine ITL1
# regions; each other UK country is itself one ITL1 region.
# https://www.ons.gov.uk/methodology/geography/ukgeographies/eurostat
ENGLISH_REGIONS = (
    "NORTH_EAST",
    "NORTH_WEST",
    "YORKSHIRE",
    "EAST_MIDLANDS",
    "WEST_MIDLANDS",
    "EAST_OF_ENGLAND",
    "LONDON",
    "SOUTH_EAST",
    "SOUTH_WEST",
)


def _load_area_list(geography_type: str) -> list[dict]:
    with open(packaged_uk_area_list_path(geography_type), encoding="utf-8") as file:
        return [
            {"code": row["code"], "name": row["name"]} for row in csv.DictReader(file)
        ]


def _load_constituencies_from_csv() -> list[dict]:
    """Load the 650 UK parliamentary constituencies (2024 boundaries).

    Read from the packaged ``data/uk_geography/constituencies_2024.csv``.

    Returns:
        List of dicts with 'code' and 'name' keys
    """
    return _load_area_list("constituency")


def _load_local_authorities_from_csv() -> list[dict]:
    """Load the 361 UK local authority districts (April 2023).

    Read from the packaged ``data/uk_geography/local_authorities_2023.csv``.

    Returns:
        List of dicts with 'code' and 'name' keys
    """
    return _load_area_list("local_authority")


def area_regions_routed_to_local_release() -> bool:
    """Whether the bundle routes UK area regions to a local-area release.

    Constituency and local-authority regions join the default registry only
    then. A national-first bundle routes them to an area-coded national
    release instead, whose consumers keep their own area handling.
    """
    manifest = release_manifest.get_release_manifest("uk")
    return manifest.regional_release_kind == "local_area"


def build_uk_region_registry(
    include_constituencies: Optional[bool] = None,
    include_local_authorities: Optional[bool] = None,
) -> RegionRegistry:
    """Build the UK region registry.

    Args:
        include_constituencies: Whether to include the 650 constituencies.
            ``None`` includes them only when the bundle routes area regions
            to a local-area release.
        include_local_authorities: Whether to include the 361 local
            authorities. ``None`` follows the same rule.

    Returns:
        RegionRegistry containing:
        - 1 national region
        - 4 country regions
        - Optionally: constituencies (if include_constituencies=True)
        - Optionally: local authorities (if include_local_authorities=True)
    """
    if include_constituencies is None or include_local_authorities is None:
        routed_to_local = area_regions_routed_to_local_release()
        if include_constituencies is None:
            include_constituencies = routed_to_local
        if include_local_authorities is None:
            include_local_authorities = routed_to_local

    regions: list[Region] = []

    # 1. National region (has dedicated dataset)
    regions.append(
        Region(
            code="uk",
            label="United Kingdom",
            region_type="national",
            dataset_path=resolve_region_dataset_path("uk", "national"),
        )
    )

    # 2. Countries scope the stored region input; country is a derived variable.
    for code, name in UK_COUNTRIES.items():
        scoping_strategy = RowFilterStrategy(
            variable_name="region",
            variable_value=list(ENGLISH_REGIONS) if code == "england" else code.upper(),
        )
        regions.append(
            Region(
                code=f"country/{code}",
                label=name,
                region_type="country",
                parent_code="uk",
                scoping_strategy=scoping_strategy,
            )
        )

    # 3. Constituencies (packaged list)
    if include_constituencies:
        constituencies = _load_constituencies_from_csv()
        constituency_dataset_path = resolve_region_dataset_path("uk", "constituency")
        for const in constituencies:
            regions.append(
                Region(
                    code=f"constituency/{const['code']}",
                    label=const["name"],
                    region_type="constituency",
                    parent_code="uk",
                    dataset_path=constituency_dataset_path,
                    scoping_strategy=RowFilterStrategy(
                        variable_name="constituency_code_oa",
                        variable_value=const["code"],
                    ),
                )
            )

    # 4. Local authorities (packaged list)
    if include_local_authorities:
        local_authorities = _load_local_authorities_from_csv()
        local_authority_dataset_path = resolve_region_dataset_path(
            "uk", "local_authority"
        )
        for la in local_authorities:
            regions.append(
                Region(
                    code=f"local_authority/{la['code']}",
                    label=la["name"],
                    region_type="local_authority",
                    parent_code="uk",
                    dataset_path=local_authority_dataset_path,
                    scoping_strategy=RowFilterStrategy(
                        variable_name="la_code_oa",
                        variable_value=la["code"],
                    ),
                )
            )

    return RegionRegistry(country_id="uk", regions=regions)


# Default registry: national and countries, plus constituencies and local
# authorities when the bundle routes them to a local-area release. To include
# them regardless, call:
#   build_uk_region_registry(include_constituencies=True, include_local_authorities=True)
uk_region_registry = build_uk_region_registry()
