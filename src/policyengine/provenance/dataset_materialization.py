"""Make bundle-certified datasets available as verified local files."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import requests
from pydantic import BaseModel, ConfigDict

from policyengine.utils.hashing import sha256_file

from .manifest import (
    CountryReleaseManifest,
    _artifact_revision,
    build_hf_uri,
    dataset_logical_name,
    get_release_manifest,
    https_dataset_uri,
    hugging_face_auth_headers,
    resolve_managed_dataset_reference,
)

DEFAULT_DATA_DIR = Path("./data")
DOWNLOAD_TIMEOUT_SECONDS = 60


class DatasetMaterializationError(ValueError):
    """Raised when a requested dataset cannot be made available safely."""


class MaterializedDataset(BaseModel):
    """Local file and provenance values for a verified bundle dataset."""

    model_config = ConfigDict(frozen=True)

    data_package_name: str
    repo_type: Literal["model", "dataset"]
    revision: str
    source_uri: str
    sha256: str
    path: Path
    metadata_path: Optional[Path] = None


class DatasetSource(BaseModel):
    """Dataset source selected for a country-package calculation."""

    model_config = ConfigDict(frozen=True)

    source_uri: str
    path: str
    bundle_dataset: Optional[MaterializedDataset] = None

    @property
    def name(self) -> str:
        return dataset_logical_name(self.source_uri)


@dataclass(frozen=True)
class _BundleDatasetSpec:
    """Manifest values required to inspect or download one bundle dataset."""

    country_id: str
    dataset: str
    data_package_name: str
    repo_id: str
    repo_type: Literal["model", "dataset"]
    path: str
    revision: str
    sha256: str
    destination: Path
    metadata_sha256: Optional[str] = None

    @property
    def source_uri(self) -> str:
        return build_hf_uri(self.repo_id, self.path, self.revision)

    @property
    def metadata_destination(self) -> Path:
        return Path(f"{self.destination}.metadata.json")


def _resolve_bundle_dataset(
    country_id: str,
    dataset: Optional[str] = None,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    manifest: Optional[CountryReleaseManifest] = None,
) -> _BundleDatasetSpec:
    country_manifest = manifest or get_release_manifest(country_id)
    dataset_name = dataset or country_manifest.default_dataset
    reference = country_manifest.datasets.get(dataset_name)
    if reference is None:
        raise DatasetMaterializationError(
            f"Unknown managed dataset {dataset_name!r} for country "
            f"{country_id!r}. Known datasets: {sorted(country_manifest.datasets)}"
        )
    if not reference.sha256:
        raise DatasetMaterializationError(
            f"Managed dataset {dataset_name!r} is missing a certified sha256."
        )

    return _BundleDatasetSpec(
        country_id=country_id,
        dataset=dataset_name,
        data_package_name=(
            reference.data_package_name or country_manifest.data_package.name
        ),
        repo_id=reference.repo_id or country_manifest.data_package.repo_id,
        repo_type=reference.repo_type or country_manifest.data_package.repo_type,
        path=reference.path,
        revision=reference.revision
        or _artifact_revision(country_manifest.data_package),
        sha256=reference.sha256,
        destination=data_dir / Path(reference.path).name,
        metadata_sha256=reference.metadata_sha256,
    )


def materialize_dataset(
    country_id: str,
    dataset: Optional[str] = None,
    *,
    allow_unmanaged: bool = False,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> DatasetSource:
    """Select a dataset source and return the local file used for calculation."""

    manifest = get_release_manifest(country_id)
    if dataset is None or dataset == manifest.default_dataset_uri:
        return _use_bundle_dataset(
            country_id,
            manifest.default_dataset,
            data_dir=data_dir,
            manifest=manifest,
        )
    if dataset in manifest.datasets:
        return _use_bundle_dataset(
            country_id,
            dataset,
            data_dir=data_dir,
            manifest=manifest,
        )

    source_uri = resolve_managed_dataset_reference(
        country_id,
        dataset,
        allow_unmanaged=allow_unmanaged,
    )
    if source_uri.startswith("hf://"):
        return _download_hugging_face_dataset(source_uri, data_dir=data_dir)
    if "://" in source_uri:
        raise DatasetMaterializationError(
            f"Unsupported explicit dataset URI: {source_uri!r}."
        )
    return _use_local_dataset(source_uri)


def _use_bundle_dataset(
    country_id: str,
    dataset: str,
    *,
    data_dir: Path,
    manifest: CountryReleaseManifest,
) -> DatasetSource:
    bundle_dataset = _reuse_or_download_bundle_files(
        _resolve_bundle_dataset(
            country_id,
            dataset,
            data_dir=data_dir,
            manifest=manifest,
        )
    )
    return DatasetSource(
        source_uri=bundle_dataset.source_uri,
        path=str(bundle_dataset.path),
        bundle_dataset=bundle_dataset,
    )


def _download_hugging_face_dataset(
    dataset_uri: str,
    *,
    data_dir: Path,
) -> DatasetSource:
    path_with_repo, revision = (
        dataset_uri[5:].rsplit("@", maxsplit=1)
        if "@" in dataset_uri[5:]
        else (dataset_uri[5:], "main")
    )
    parts = path_with_repo.split("/", maxsplit=2)
    if len(parts) != 3 or not all(parts):
        raise DatasetMaterializationError(
            "Invalid Hugging Face dataset URI. Expected format "
            f"'hf://owner/repo/path/to/file[@revision]', got {dataset_uri!r}."
        )

    repo_id = f"{parts[0]}/{parts[1]}"
    repository_path = parts[2]
    destination = data_dir / Path(repository_path).name
    destination.parent.mkdir(parents=True, exist_ok=True)

    for repo_type in ("model", "dataset"):
        file_descriptor, temp_name = tempfile.mkstemp(
            prefix=".policyengine-download-",
            suffix=destination.suffix or ".download",
            dir=destination.parent,
        )
        os.close(file_descriptor)
        temporary_path = Path(temp_name)
        url = https_dataset_uri(
            repo_id,
            repository_path,
            revision,
            repo_type=repo_type,
        )
        try:
            with requests.get(
                url,
                headers=hugging_face_auth_headers(),
                stream=True,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            ) as response:
                if response.status_code in {401, 403}:
                    raise DatasetMaterializationError(
                        "Could not download explicit dataset "
                        f"{dataset_uri!r}: Hugging Face rejected the configured "
                        "credentials. Set HUGGING_FACE_TOKEN to a token with "
                        "access to the repository."
                    )
                if response.status_code == 404:
                    if repo_type == "model":
                        continue
                    raise DatasetMaterializationError(
                        f"Could not find explicit dataset {dataset_uri!r}."
                    )
                response.raise_for_status()
                with temporary_path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)
            os.replace(temporary_path, destination)
            return DatasetSource(source_uri=dataset_uri, path=str(destination))
        finally:
            temporary_path.unlink(missing_ok=True)

    raise DatasetMaterializationError(
        f"Could not download explicit dataset {dataset_uri!r}."
    )


def _use_local_dataset(dataset_path: str) -> DatasetSource:
    return DatasetSource(source_uri=dataset_path, path=dataset_path)


def _reuse_or_download_bundle_files(
    dataset: _BundleDatasetSpec,
) -> MaterializedDataset:
    files = [
        (
            dataset.path,
            dataset.destination,
            dataset.sha256,
            f"{dataset.country_id.upper()} dataset {dataset.dataset!r}",
        )
    ]
    if dataset.metadata_sha256 is not None:
        files.append(
            (
                f"{dataset.path}.metadata.json",
                dataset.metadata_destination,
                dataset.metadata_sha256,
                f"metadata for {dataset.dataset!r}",
            )
        )

    for repository_path, destination, expected_sha256, description in files:
        if destination.is_file() and sha256_file(destination) == expected_sha256:
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temp_name = tempfile.mkstemp(
            prefix=".policyengine-download-",
            suffix=destination.suffix or ".download",
            dir=destination.parent,
        )
        os.close(file_descriptor)
        temporary_path = Path(temp_name)
        url = https_dataset_uri(
            dataset.repo_id,
            repository_path,
            dataset.revision,
            repo_type=dataset.repo_type,
        )
        try:
            with requests.get(
                url,
                headers=hugging_face_auth_headers(),
                stream=True,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            ) as response:
                if response.status_code in {401, 403}:
                    raise DatasetMaterializationError(
                        f"Could not download {description}: Hugging Face rejected "
                        "the configured credentials. Set HUGGING_FACE_TOKEN to a "
                        "token with access to the repository."
                    )
                if response.status_code == 404:
                    raise DatasetMaterializationError(
                        f"Could not find {description} at {url}."
                    )
                response.raise_for_status()
                with temporary_path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)

            actual_sha256 = sha256_file(temporary_path)
            if actual_sha256 != expected_sha256:
                raise DatasetMaterializationError(
                    f"Downloaded {description} has sha256 {actual_sha256}, "
                    f"expected {expected_sha256}."
                )
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)

    return MaterializedDataset(
        data_package_name=dataset.data_package_name,
        repo_type=dataset.repo_type,
        revision=dataset.revision,
        source_uri=dataset.source_uri,
        sha256=dataset.sha256,
        path=dataset.destination,
        metadata_path=(
            dataset.metadata_destination
            if dataset.metadata_sha256 is not None
            else None
        ),
    )
