"""Tests for UK geography asset resolution."""

from pathlib import Path
from unittest.mock import patch

import pytest

from policyengine.outputs.uk_geography_assets import (
    CONSTITUENCY_ASSET_SPEC,
    LOCAL_AUTHORITY_ASSET_SPEC,
    GCSUKGeographyAssetStrategy,
    LocalUKGeographyAssetStrategy,
    resolve_uk_geography_asset_paths,
)


def _touch(path: Path) -> None:
    path.write_text("test asset")


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
    weight_matrix_path = tmp_path / LOCAL_AUTHORITY_ASSET_SPEC.weight_matrix_filename
    lookup_csv_path = tmp_path / LOCAL_AUTHORITY_ASSET_SPEC.lookup_csv_filename
    _touch(weight_matrix_path)
    _touch(lookup_csv_path)

    paths = resolve_uk_geography_asset_paths(
        LOCAL_AUTHORITY_ASSET_SPEC,
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
