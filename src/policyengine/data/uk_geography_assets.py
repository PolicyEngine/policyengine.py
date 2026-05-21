"""Canonical UK geography asset metadata."""

from dataclasses import dataclass

UK_GEOGRAPHY_BUCKET = "policyengine-uk-data-private"
UK_GEOGRAPHY_BUCKET_URI = f"gs://{UK_GEOGRAPHY_BUCKET}"


@dataclass(frozen=True)
class UKGeographyAssetSpec:
    """The paired files needed to compute one UK geography output."""

    geography_type: str
    weight_matrix_filename: str
    lookup_csv_filename: str
    bucket: str = UK_GEOGRAPHY_BUCKET


CONSTITUENCY_ASSET_SPEC = UKGeographyAssetSpec(
    geography_type="constituency",
    weight_matrix_filename="parliamentary_constituency_weights.h5",
    lookup_csv_filename="constituencies_2024.csv",
)

LOCAL_AUTHORITY_ASSET_SPEC = UKGeographyAssetSpec(
    geography_type="local_authority",
    weight_matrix_filename="local_authority_weights.h5",
    lookup_csv_filename="local_authorities_2021.csv",
)
