"""UK region definitions.

This module defines all UK geographic regions:
- National (1)
- Countries (4: England, Scotland, Wales, Northern Ireland)
- Constituencies (loaded from CSV at runtime)
- Local Authorities (loaded from CSV at runtime)

Note: Constituencies and local authorities filter from the national dataset
using geography columns carried on each household. This keeps subnational
scoping tied to the dataset rows, not to a separate weight matrix whose
household dimension can drift from the default dataset.
"""

import logging
from typing import TYPE_CHECKING

from policyengine.core.region import Region, RegionRegistry
from policyengine.core.scoping_strategy import RowFilterStrategy
from policyengine.data.uk_geography_assets import (
    CONSTITUENCY_ASSET_SPEC,
    LOCAL_AUTHORITY_ASSET_SPEC,
    UK_GEOGRAPHY_BUCKET_URI,
)
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


def _load_constituencies_from_csv() -> list[dict]:
    """Load UK constituency data from CSV.

    Constituencies are loaded from:
    gs://policyengine-uk-data-private/constituencies_2024.csv

    Returns:
        List of dicts with 'code' and 'name' keys
    """
    try:
        from policyengine_core.tools.google_cloud import download
    except ImportError:
        # If policyengine_core is not available, return empty list
        return []

    try:
        csv_path = download(
            gcs_bucket=CONSTITUENCY_ASSET_SPEC.bucket,
            gcs_key=CONSTITUENCY_ASSET_SPEC.lookup_csv_filename,
        )
        import pandas as pd

        df = pd.read_csv(csv_path)
        return [{"code": row["code"], "name": row["name"]} for _, row in df.iterrows()]
    except (OSError, KeyError, ValueError) as exc:
        logger.warning("Failed to load constituencies CSV: %s", exc)
        return []
    except Exception:
        logger.error("Unexpected error loading constituencies CSV", exc_info=True)
        return []


def _load_local_authorities_from_csv() -> list[dict]:
    """Load UK local authority data from CSV.

    Local authorities are loaded from:
    gs://policyengine-uk-data-private/local_authorities_2021.csv

    Returns:
        List of dicts with 'code' and 'name' keys
    """
    try:
        from policyengine_core.tools.google_cloud import download
    except ImportError:
        # If policyengine_core is not available, return empty list
        return []

    try:
        csv_path = download(
            gcs_bucket=LOCAL_AUTHORITY_ASSET_SPEC.bucket,
            gcs_key=LOCAL_AUTHORITY_ASSET_SPEC.lookup_csv_filename,
        )
        import pandas as pd

        df = pd.read_csv(csv_path)
        return [{"code": row["code"], "name": row["name"]} for _, row in df.iterrows()]
    except (OSError, KeyError, ValueError) as exc:
        logger.warning("Failed to load local authorities CSV: %s", exc)
        return []
    except Exception:
        logger.error("Unexpected error loading local authorities CSV", exc_info=True)
        return []


def build_uk_region_registry(
    include_constituencies: bool = False,
    include_local_authorities: bool = False,
) -> RegionRegistry:
    """Build the UK region registry.

    Args:
        include_constituencies: If True, load and include constituencies from CSV.
            Defaults to False to avoid GCS dependency at import time.
        include_local_authorities: If True, load and include local authorities from CSV.
            Defaults to False to avoid GCS dependency at import time.

    Returns:
        RegionRegistry containing:
        - 1 national region
        - 4 country regions
        - Optionally: constituencies (if include_constituencies=True)
        - Optionally: local authorities (if include_local_authorities=True)
    """
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

    # 2. Country regions (filter from national by 'country' variable)
    for code, name in UK_COUNTRIES.items():
        regions.append(
            Region(
                code=f"country/{code}",
                label=name,
                region_type="country",
                parent_code="uk",
                scoping_strategy=RowFilterStrategy(
                    variable_name="country",
                    variable_value=code.upper(),
                ),
            )
        )

    # 3. Constituencies (optional, loaded from CSV)
    if include_constituencies:
        constituencies = _load_constituencies_from_csv()
        for const in constituencies:
            regions.append(
                Region(
                    code=f"constituency/{const['code']}",
                    label=const["name"],
                    region_type="constituency",
                    parent_code="uk",
                    scoping_strategy=RowFilterStrategy(
                        variable_name="constituency_code_oa",
                        variable_value=const["code"],
                    ),
                )
            )

    # 4. Local Authorities (optional, loaded from CSV)
    if include_local_authorities:
        local_authorities = _load_local_authorities_from_csv()
        for la in local_authorities:
            regions.append(
                Region(
                    code=f"local_authority/{la['code']}",
                    label=la["name"],
                    region_type="local_authority",
                    parent_code="uk",
                    scoping_strategy=RowFilterStrategy(
                        variable_name="la_code_oa",
                        variable_value=la["code"],
                    ),
                )
            )

    return RegionRegistry(country_id="uk", regions=regions)


# Default registry with just core regions (national + countries)
# To get full registry with constituencies/LAs, call:
#   build_uk_region_registry(include_constituencies=True, include_local_authorities=True)
uk_region_registry = build_uk_region_registry()
