"""Canonical UK geography asset metadata and resolution helpers."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union

UK_GEOGRAPHY_BUCKET = "policyengine-uk-data-private"
UK_GEOGRAPHY_BUCKET_URI = f"gs://{UK_GEOGRAPHY_BUCKET}"
UK_GEOGRAPHY_DATA_DIR_ENV = "POLICYENGINE_UK_GEOGRAPHY_DATA_DIR"
POLICYENGINE_DATA_FOLDER_ENV = "POLICYENGINE_DATA_FOLDER"


@dataclass(frozen=True)
class UKGeographyAssetSpec:
    """The paired files needed to compute one UK geography output."""

    geography_type: str
    weight_matrix_filename: str
    lookup_csv_filename: str
    bucket: str = UK_GEOGRAPHY_BUCKET
    weight_matrix_bucket: Optional[str] = None
    lookup_csv_bucket: Optional[str] = None

    @property
    def resolved_weight_matrix_bucket(self) -> str:
        return self.weight_matrix_bucket or self.bucket

    @property
    def resolved_lookup_csv_bucket(self) -> str:
        return self.lookup_csv_bucket or self.bucket


@dataclass(frozen=True)
class UKGeographyAssetPaths:
    """Resolved local paths for a UK geography output."""

    weight_matrix_path: str
    lookup_csv_path: str


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


def _env_path(name: str) -> Optional[Path]:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value).expanduser()


def _dedupe_paths(paths: Sequence[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve()) if path.exists() else str(path.absolute())
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def default_local_search_dirs() -> list[Path]:
    """Return directories searched before downloading UK geography assets."""
    candidates = [
        _env_path(UK_GEOGRAPHY_DATA_DIR_ENV),
        _env_path(POLICYENGINE_DATA_FOLDER_ENV),
        Path.home() / ".policyengine" / "uk-geography",
        Path(".datasets"),
        Path.cwd(),
    ]
    return _dedupe_paths([path for path in candidates if path is not None])


def default_download_dir() -> Path:
    """Return the default GCS download cache for UK geography assets."""
    configured = _env_path(UK_GEOGRAPHY_DATA_DIR_ENV) or _env_path(
        POLICYENGINE_DATA_FOLDER_ENV
    )
    if configured is not None:
        return configured
    return Path.home() / ".policyengine" / "uk-geography"


def _validate_explicit_path(path: Optional[str], *, asset_label: str) -> None:
    if not path:
        return

    candidate = Path(path).expanduser()
    if not candidate.is_file():
        raise FileNotFoundError(
            f"Provided UK geography {asset_label} path does not exist "
            f"or is not a file: {candidate}"
        )


class UKGeographyAssetStrategy:
    """Base class for UK geography asset resolution strategies."""

    downloads_missing_assets = False
    last_error: Optional[str] = None

    def resolve(
        self,
        spec: UKGeographyAssetSpec,
        *,
        weight_matrix_path: Optional[str] = None,
        lookup_csv_path: Optional[str] = None,
    ) -> Optional[UKGeographyAssetPaths]:
        raise NotImplementedError


PathLike = Union[os.PathLike, str]


class LocalUKGeographyAssetStrategy(UKGeographyAssetStrategy):
    """Resolve geography assets from explicit paths or local search dirs."""

    def __init__(self, search_dirs: Optional[Sequence[PathLike]] = None):
        self.search_dirs = [
            Path(path).expanduser()
            for path in (
                search_dirs if search_dirs is not None else default_local_search_dirs()
            )
        ]
        self.last_error = None

    def _resolve_asset(
        self,
        *,
        explicit_path: Optional[str],
        filename: str,
    ) -> Optional[Path]:
        if explicit_path:
            path = Path(explicit_path).expanduser()
            if path.is_file():
                return path

        for search_dir in self.search_dirs:
            path = search_dir / filename
            if path.is_file():
                return path
        return None

    def resolve(
        self,
        spec: UKGeographyAssetSpec,
        *,
        weight_matrix_path: Optional[str] = None,
        lookup_csv_path: Optional[str] = None,
    ) -> Optional[UKGeographyAssetPaths]:
        weight_path = self._resolve_asset(
            explicit_path=weight_matrix_path,
            filename=spec.weight_matrix_filename,
        )
        csv_path = self._resolve_asset(
            explicit_path=lookup_csv_path,
            filename=spec.lookup_csv_filename,
        )

        if weight_path is not None and csv_path is not None:
            self.last_error = None
            return UKGeographyAssetPaths(
                weight_matrix_path=str(weight_path),
                lookup_csv_path=str(csv_path),
            )

        missing = []
        if weight_path is None:
            missing.append(spec.weight_matrix_filename)
        if csv_path is None:
            missing.append(spec.lookup_csv_filename)
        searched = ", ".join(str(path) for path in self.search_dirs)
        self.last_error = (
            "local lookup missing "
            + ", ".join(missing)
            + f"; searched: {searched or '<none>'}"
        )
        return None


class GCSUKGeographyAssetStrategy(UKGeographyAssetStrategy):
    """Download geography assets from the standard PolicyEngine UK GCS bucket."""

    downloads_missing_assets = True

    def __init__(self, download_dir: Optional[PathLike] = None):
        self.download_dir = (
            Path(download_dir).expanduser()
            if download_dir is not None
            else default_download_dir()
        )
        self.last_error = None

    def _download_asset(
        self,
        *,
        bucket: str,
        filename: str,
        explicit_path: Optional[str],
    ) -> Path:
        if explicit_path:
            path = Path(explicit_path).expanduser()
            if path.is_file():
                return path

        target_path = self.download_dir / filename
        if target_path.is_file():
            return target_path

        self.download_dir.mkdir(parents=True, exist_ok=True)

        from policyengine_core.tools.google_cloud import download_gcs_file

        downloaded_path = download_gcs_file(
            bucket=bucket,
            file_path=filename,
            local_path=str(target_path),
        )
        return Path(downloaded_path).expanduser()

    def resolve(
        self,
        spec: UKGeographyAssetSpec,
        *,
        weight_matrix_path: Optional[str] = None,
        lookup_csv_path: Optional[str] = None,
    ) -> Optional[UKGeographyAssetPaths]:
        try:
            resolved_weight_matrix_path = self._download_asset(
                bucket=spec.resolved_weight_matrix_bucket,
                filename=spec.weight_matrix_filename,
                explicit_path=weight_matrix_path,
            )
            resolved_lookup_csv_path = self._download_asset(
                bucket=spec.resolved_lookup_csv_bucket,
                filename=spec.lookup_csv_filename,
                explicit_path=lookup_csv_path,
            )
        except Exception as exc:
            self.last_error = f"GCS download failed for {spec.geography_type}: {exc}"
            return None

        self.last_error = None
        return UKGeographyAssetPaths(
            weight_matrix_path=str(resolved_weight_matrix_path),
            lookup_csv_path=str(resolved_lookup_csv_path),
        )


def default_uk_geography_asset_strategies(
    *,
    download_missing_assets: bool = True,
) -> list[UKGeographyAssetStrategy]:
    """Return the default asset resolution strategy chain."""
    strategies: list[UKGeographyAssetStrategy] = [LocalUKGeographyAssetStrategy()]
    if download_missing_assets:
        strategies.append(GCSUKGeographyAssetStrategy())
    return strategies


def resolve_uk_geography_asset_paths(
    spec: UKGeographyAssetSpec,
    *,
    weight_matrix_path: Optional[str] = None,
    lookup_csv_path: Optional[str] = None,
    asset_strategies: Optional[Sequence[UKGeographyAssetStrategy]] = None,
    download_missing_assets: bool = True,
) -> UKGeographyAssetPaths:
    """Resolve required UK geography files with optional GCS fallback."""
    _validate_explicit_path(
        weight_matrix_path,
        asset_label=f"{spec.geography_type} weight matrix",
    )
    _validate_explicit_path(
        lookup_csv_path,
        asset_label=f"{spec.geography_type} lookup CSV",
    )

    strategies = (
        list(asset_strategies)
        if asset_strategies is not None
        else default_uk_geography_asset_strategies(
            download_missing_assets=download_missing_assets,
        )
    )
    if not download_missing_assets:
        download_strategy_names = [
            strategy.__class__.__name__
            for strategy in strategies
            if strategy.downloads_missing_assets
        ]
        if download_strategy_names:
            raise ValueError(
                "download_missing_assets=False cannot be used with asset "
                "strategies that download missing assets: "
                + ", ".join(download_strategy_names)
            )

    errors = []
    for strategy in strategies:
        paths = strategy.resolve(
            spec,
            weight_matrix_path=weight_matrix_path,
            lookup_csv_path=lookup_csv_path,
        )
        if paths is not None:
            return paths
        if strategy.last_error:
            errors.append(f"{strategy.__class__.__name__}: {strategy.last_error}")

    detail = "; ".join(errors) if errors else "no asset strategies configured"
    if not download_missing_assets:
        detail += "; GCS fallback disabled by download_missing_assets=False"
    raise FileNotFoundError(
        f"Unable to resolve UK {spec.geography_type} geography assets "
        f"({spec.weight_matrix_filename}, {spec.lookup_csv_filename}). {detail}. "
        f"Set {UK_GEOGRAPHY_DATA_DIR_ENV} or provide explicit paths."
    )
