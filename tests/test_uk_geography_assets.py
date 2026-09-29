"""Tests for UK geography asset resolution."""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from policyengine.outputs.uk_geography_assets import (
    CONSTITUENCY_ASSET_SPEC,
    LOCAL_AUTHORITY_ASSET_SPEC,
    LOCAL_AUTHORITY_LAD22_ASSET_SPEC,
    LOCAL_AUTHORITY_LAD23_ASSET_SPEC,
    GCSUKGeographyAssetStrategy,
    LocalAuthorityVintage,
    LocalUKGeographyAssetStrategy,
    UKGeographyAssetSpec,
    UKGeographyAssetStrategy,
    get_uk_local_authority_lookup_configuration,
    resolve_uk_geography_asset_paths,
    resolve_uk_local_authority_asset_spec,
    resolve_uk_local_authority_vintage,
)
from policyengine.outputs.uk_geography_impact import (
    resolve_uk_geography_lookup_csv_path,
)


def _touch(path: Path) -> None:
    path.write_text("test asset")


EXPECTED_LAD22_DATASETS = {
    "enhanced_frs_2023_24",
    "enhanced_frs_2024_25",
    "enhanced_frs_2024_25_tiny",
    "frs_2023_24",
    "frs_2024_25",
    "frs_2024_25_tiny",
    "populace_uk_2023",
}


def test_local_authority_configuration_maps_only_declared_datasets_to_lad22():
    configuration = get_uk_local_authority_lookup_configuration()

    assert configuration.default_vintage is LocalAuthorityVintage.LAD23
    assert configuration.lad22_dataset_identities == EXPECTED_LAD22_DATASETS
    for dataset_identity in EXPECTED_LAD22_DATASETS:
        assert (
            resolve_uk_local_authority_vintage(dataset_identity)
            is LocalAuthorityVintage.LAD22
        )
        assert (
            resolve_uk_local_authority_asset_spec(dataset_identity)
            == LOCAL_AUTHORITY_LAD22_ASSET_SPEC
        )


@pytest.mark.parametrize("dataset_identity", [None, "", "future_microcosm_release"])
def test_local_authority_configuration_defaults_unknown_datasets_to_lad23(
    dataset_identity,
):
    assert (
        resolve_uk_local_authority_vintage(dataset_identity)
        is LocalAuthorityVintage.LAD23
    )
    assert (
        resolve_uk_local_authority_asset_spec(dataset_identity)
        == LOCAL_AUTHORITY_LAD23_ASSET_SPEC
    )
    assert LOCAL_AUTHORITY_ASSET_SPEC == LOCAL_AUTHORITY_LAD23_ASSET_SPEC


def test_lookup_resolver_rejects_bundle_asset_with_wrong_hash(tmp_path):
    lookup_path = tmp_path / "lookup.csv"
    lookup_path.write_text("code,x,y,name\nLA001,0,0,Authority\n")
    spec = UKGeographyAssetSpec(
        geography_type="test",
        weight_matrix_filename="unused.h5",
        lookup_csv_filename=lookup_path.name,
        lookup_csv_sha256="0" * 64,
    )

    with patch(
        "policyengine.outputs.uk_geography_impact.default_local_search_dirs",
        return_value=[tmp_path],
    ):
        with pytest.raises(ValueError, match="failed its SHA-256 check"):
            resolve_uk_geography_lookup_csv_path(
                spec,
                download_missing_assets=False,
            )


def test_lookup_resolver_accepts_bundle_asset_with_matching_hash(tmp_path):
    lookup_path = tmp_path / "lookup.csv"
    contents = b"code,x,y,name\nLA001,0,0,Authority\n"
    lookup_path.write_bytes(contents)
    spec = UKGeographyAssetSpec(
        geography_type="test",
        weight_matrix_filename="unused.h5",
        lookup_csv_filename=lookup_path.name,
        lookup_csv_sha256=hashlib.sha256(contents).hexdigest(),
    )

    with patch(
        "policyengine.outputs.uk_geography_impact.default_local_search_dirs",
        return_value=[tmp_path],
    ):
        resolved = resolve_uk_geography_lookup_csv_path(
            spec,
            download_missing_assets=False,
        )

    assert resolved == str(lookup_path)


def test_local_strategy_resolves_explicit_paths(tmp_path):
    weight_matrix_path = tmp_path / "custom_weights.h5"
    lookup_csv_path = tmp_path / "custom_lookup.csv"
    _touch(weight_matrix_path)
    _touch(lookup_csv_path)

    paths = resolve_uk_geography_asset_paths(
        CONSTITUENCY_ASSET_SPEC,
        weight_matrix_path=str(weight_matrix_path),
        lookup_csv_path=str(lookup_csv_path),
        asset_strategies=[LocalUKGeographyAssetStrategy(search_dirs=[])],
    )

    assert paths.weight_matrix_path == str(weight_matrix_path)
    assert paths.lookup_csv_path == str(lookup_csv_path)


def test_local_strategy_resolves_standard_files_from_search_dir(tmp_path):
    spec = UKGeographyAssetSpec(
        geography_type="local_authority",
        weight_matrix_filename="local_authority_weights.h5",
        lookup_csv_filename="local_authorities.csv",
    )
    weight_matrix_path = tmp_path / spec.weight_matrix_filename
    lookup_csv_path = tmp_path / spec.lookup_csv_filename
    _touch(weight_matrix_path)
    _touch(lookup_csv_path)

    paths = resolve_uk_geography_asset_paths(
        spec,
        asset_strategies=[LocalUKGeographyAssetStrategy(search_dirs=[tmp_path])],
    )

    assert paths.weight_matrix_path == str(weight_matrix_path)
    assert paths.lookup_csv_path == str(lookup_csv_path)


def test_gcs_strategy_downloads_missing_standard_files(tmp_path):
    download_dir = tmp_path / "downloads"

    def fake_download_gcs_file(*, bucket, file_path, local_path, version=None):
        del version
        assert bucket == CONSTITUENCY_ASSET_SPEC.bucket
        Path(local_path).write_text(file_path)
        return local_path

    with patch(
        "policyengine_core.tools.google_cloud.download_gcs_file",
        side_effect=fake_download_gcs_file,
    ) as download_gcs_file:
        paths = resolve_uk_geography_asset_paths(
            CONSTITUENCY_ASSET_SPEC,
            asset_strategies=[
                LocalUKGeographyAssetStrategy(search_dirs=[tmp_path / "missing"]),
                GCSUKGeographyAssetStrategy(download_dir=download_dir),
            ],
        )

    assert paths.weight_matrix_path == str(
        download_dir / CONSTITUENCY_ASSET_SPEC.weight_matrix_filename
    )
    assert paths.lookup_csv_path == str(
        download_dir / CONSTITUENCY_ASSET_SPEC.lookup_csv_filename
    )
    assert download_gcs_file.call_count == 2
    assert {call.kwargs["file_path"] for call in download_gcs_file.call_args_list} == {
        CONSTITUENCY_ASSET_SPEC.weight_matrix_filename,
        CONSTITUENCY_ASSET_SPEC.lookup_csv_filename,
    }


def test_resolver_local_only_does_not_download_missing_standard_files():
    spec = UKGeographyAssetSpec(
        geography_type="test",
        weight_matrix_filename="missing-test-weights.h5",
        lookup_csv_filename="missing-test-lookup.csv",
    )

    with patch("policyengine_core.tools.google_cloud.download_gcs_file") as download:
        with pytest.raises(FileNotFoundError) as exc_info:
            resolve_uk_geography_asset_paths(
                spec,
                download_missing_assets=False,
            )

    download.assert_not_called()
    assert "Unable to resolve UK test geography assets" in str(exc_info.value)
    assert spec.weight_matrix_filename in str(exc_info.value)


def test_resolver_rejects_downloading_strategy_when_downloads_disabled(tmp_path):
    with pytest.raises(ValueError) as exc_info:
        resolve_uk_geography_asset_paths(
            CONSTITUENCY_ASSET_SPEC,
            asset_strategies=[GCSUKGeographyAssetStrategy(download_dir=tmp_path)],
            download_missing_assets=False,
        )

    assert "download_missing_assets=False" in str(exc_info.value)
    assert "GCSUKGeographyAssetStrategy" in str(exc_info.value)


def test_resolver_rejects_missing_explicit_path_before_strategies(tmp_path):
    class ShouldNotRunStrategy(UKGeographyAssetStrategy):
        def resolve(self, *args, **kwargs):
            raise AssertionError("Strategy should not run for a missing explicit path")

    missing_weight_matrix_path = tmp_path / "missing_weights.h5"
    lookup_csv_path = tmp_path / "lookup.csv"
    _touch(lookup_csv_path)

    with pytest.raises(FileNotFoundError) as exc_info:
        resolve_uk_geography_asset_paths(
            CONSTITUENCY_ASSET_SPEC,
            weight_matrix_path=str(missing_weight_matrix_path),
            lookup_csv_path=str(lookup_csv_path),
            asset_strategies=[ShouldNotRunStrategy()],
        )

    assert "constituency weight matrix" in str(exc_info.value)
    assert str(missing_weight_matrix_path) in str(exc_info.value)


def test_resolver_raises_clear_error_when_no_strategy_succeeds():
    class MissingStrategy(LocalUKGeographyAssetStrategy):
        def __init__(self):
            super().__init__(search_dirs=[])

    with pytest.raises(FileNotFoundError) as exc_info:
        resolve_uk_geography_asset_paths(
            CONSTITUENCY_ASSET_SPEC,
            asset_strategies=[MissingStrategy()],
        )

    message = str(exc_info.value)
    assert "Unable to resolve UK constituency geography assets" in message
    assert CONSTITUENCY_ASSET_SPEC.weight_matrix_filename in message
    assert CONSTITUENCY_ASSET_SPEC.lookup_csv_filename in message
    assert "POLICYENGINE_UK_GEOGRAPHY_DATA_DIR" in message
