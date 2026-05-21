"""Re-export UK geography asset resolution helpers for output callers."""

from policyengine.data.uk_geography_assets import (
    CONSTITUENCY_ASSET_SPEC,
    LOCAL_AUTHORITY_ASSET_SPEC,
    UK_GEOGRAPHY_BUCKET,
    GCSUKGeographyAssetStrategy,
    LocalUKGeographyAssetStrategy,
    UKGeographyAssetPaths,
    UKGeographyAssetSpec,
    UKGeographyAssetStrategy,
    default_uk_geography_asset_strategies,
    resolve_uk_geography_asset_paths,
)

__all__ = [
    "CONSTITUENCY_ASSET_SPEC",
    "LOCAL_AUTHORITY_ASSET_SPEC",
    "UK_GEOGRAPHY_BUCKET",
    "UKGeographyAssetPaths",
    "UKGeographyAssetSpec",
    "UKGeographyAssetStrategy",
    "LocalUKGeographyAssetStrategy",
    "GCSUKGeographyAssetStrategy",
    "default_uk_geography_asset_strategies",
    "resolve_uk_geography_asset_paths",
]
