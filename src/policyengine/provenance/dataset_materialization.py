"""Make bundle-certified datasets available as verified local files."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Union
from urllib.parse import quote

import requests
from pydantic import BaseModel

from .manifest import (
    CountryReleaseManifest,
    _artifact_revision,
    build_hf_uri,
    dataset_logical_name,
    get_release_manifest,
    resolve_local_managed_dataset_source,
    resolve_managed_dataset_reference,
)

DEFAULT_DATA_DIR = Path("./data")
DOWNLOAD_TIMEOUT_SECONDS = 60


class DatasetMaterializationError(ValueError):
    """Raised when a dataset cannot be made available safely."""


class MaterializedDataset(BaseModel):
    """Verified local representation of one bundle-managed dataset."""

    data_package_name: str
    repo_type: Literal["model", "dataset"]
    revision: str
    source_uri: str
    expected_sha256: str
    actual_sha256: str
    path: Path
    cache_hit: bool
    metadata_path: Optional[Path] = None


@dataclass(frozen=True)
class _ResolvedBundleDataset:
    country_id: str
    dataset: str
    data_package_name: str
    repo_id: str
    repo_type: Literal["model", "dataset"]
    path: str
    revision: str
    expected_sha256: str
    destination: Path
    metadata_expected_sha256: Optional[str] = None

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
) -> _ResolvedBundleDataset:
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

    return _ResolvedBundleDataset(
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
        expected_sha256=reference.sha256,
        destination=data_dir / Path(reference.path).name,
        metadata_expected_sha256=reference.metadata_sha256,
    )


def materialize_bundle_dataset(
    country_id: str,
    dataset: Optional[str] = None,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> MaterializedDataset:
    """Return a verified local copy of a dataset from the installed bundle."""

    return _materialize_resolved_dataset(
        _resolve_bundle_dataset(country_id, dataset, data_dir=data_dir)
    )


def _materialize_resolved_dataset(
    resolved: _ResolvedBundleDataset,
    *,
    session=requests,
) -> MaterializedDataset:
    local_source = resolve_local_managed_dataset_source(
        resolved.country_id,
        resolved.source_uri,
    )
    local_path = Path(local_source).expanduser()
    local_sha256 = (
        _matching_sha256(local_path, resolved.expected_sha256)
        if local_source != resolved.source_uri
        else None
    )

    if local_sha256 is not None:
        path = local_path
        actual_sha256 = local_sha256
        cache_hit = True
    else:
        path, actual_sha256, cache_hit = _materialize_verified_file(
            url=_hf_download_url(
                repo_id=resolved.repo_id,
                repo_type=resolved.repo_type,
                path=resolved.path,
                revision=resolved.revision,
            ),
            destination=resolved.destination,
            expected_sha256=resolved.expected_sha256,
            description=(f"{resolved.country_id.upper()} dataset {resolved.dataset!r}"),
            session=session,
        )

    metadata_path = _materialize_metadata(
        resolved,
        dataset_path=path,
        session=session,
    )
    return MaterializedDataset(
        data_package_name=resolved.data_package_name,
        repo_type=resolved.repo_type,
        revision=resolved.revision,
        source_uri=resolved.source_uri,
        expected_sha256=resolved.expected_sha256,
        actual_sha256=actual_sha256,
        path=path,
        cache_hit=cache_hit,
        metadata_path=metadata_path,
    )


def _materialize_metadata(
    resolved: _ResolvedBundleDataset,
    *,
    dataset_path: Path,
    session=requests,
) -> Optional[Path]:
    expected_sha256 = resolved.metadata_expected_sha256
    if expected_sha256 is None:
        return None

    local_path = Path(f"{dataset_path}.metadata.json")
    if _matching_sha256(local_path, expected_sha256) is not None:
        return local_path

    path, _, _ = _materialize_verified_file(
        url=_hf_download_url(
            repo_id=resolved.repo_id,
            repo_type=resolved.repo_type,
            path=f"{resolved.path}.metadata.json",
            revision=resolved.revision,
        ),
        destination=resolved.metadata_destination,
        expected_sha256=expected_sha256,
        description=f"metadata for {resolved.dataset!r}",
        session=session,
    )
    return path


def _materialize_verified_file(
    *,
    url: str,
    destination: Path,
    expected_sha256: str,
    description: str,
    session=requests,
) -> tuple[Path, str, bool]:
    existing_sha256 = _matching_sha256(destination, expected_sha256)
    if existing_sha256 is not None:
        return destination, existing_sha256, True

    downloaded = _download_to_temp(
        url,
        destination=destination,
        description=description,
        session=session,
    )
    try:
        actual_sha256 = _sha256_file(downloaded)
        if actual_sha256 != expected_sha256:
            raise DatasetMaterializationError(
                f"Downloaded {description} has sha256 {actual_sha256}, "
                f"expected {expected_sha256}."
            )
        os.replace(downloaded, destination)
    finally:
        downloaded.unlink(missing_ok=True)
    return destination, actual_sha256, False


def _materialize_dataset_request(
    country_id: str,
    dataset: Optional[str],
    *,
    allow_unmanaged: bool,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> tuple[str, str, Optional[MaterializedDataset]]:
    manifest = get_release_manifest(country_id)
    managed_dataset = None
    if dataset is None:
        managed_dataset = manifest.default_dataset
    elif dataset in manifest.datasets:
        managed_dataset = dataset
    elif dataset == manifest.default_dataset_uri:
        managed_dataset = manifest.default_dataset

    if managed_dataset is not None:
        materialized = _materialize_resolved_dataset(
            _resolve_bundle_dataset(
                country_id,
                managed_dataset,
                data_dir=data_dir,
                manifest=manifest,
            )
        )
        return materialized.source_uri, str(materialized.path), materialized

    source_uri = resolve_managed_dataset_reference(
        country_id,
        dataset,
        allow_unmanaged=allow_unmanaged,
    )
    return (
        source_uri,
        _materialize_unmanaged_dataset_source(source_uri, data_dir=data_dir),
        None,
    )


def _runtime_dataset_provenance(
    source_uri: str,
    local_path: str,
    materialized: Optional[MaterializedDataset],
    *,
    logical_name: Optional[str] = None,
) -> dict[str, object]:
    provenance: dict[str, object] = {
        "managed_by": "policyengine.py",
        "runtime_dataset": logical_name or dataset_logical_name(source_uri),
        "runtime_dataset_uri": source_uri,
        "runtime_dataset_source": local_path,
    }
    if materialized is not None:
        provenance.update(
            {
                "runtime_dataset_data_package": materialized.data_package_name,
                "runtime_dataset_repo_type": materialized.repo_type,
                "runtime_dataset_revision": materialized.revision,
                "runtime_dataset_expected_sha256": materialized.expected_sha256,
                "runtime_dataset_sha256": materialized.actual_sha256,
                "runtime_dataset_cache_hit": materialized.cache_hit,
            }
        )
    return provenance


def _materialize_unmanaged_dataset_source(
    dataset_source: Union[str, Path],
    *,
    version: Optional[str] = None,
    data_dir: Path = DEFAULT_DATA_DIR,
    repo_type: Optional[Literal["model", "dataset"]] = None,
    session=requests,
) -> str:
    """Return a local path for an explicitly unmanaged local or HF source."""

    source = str(dataset_source)
    if not source.startswith("hf://"):
        if "://" in source:
            raise DatasetMaterializationError(
                f"Unsupported unmanaged dataset URI: {source!r}."
            )
        return source

    repo_id, path, revision = _parse_unmanaged_hf_reference(source, version=version)
    destination = data_dir / Path(path).name
    repo_types: list[Literal["model", "dataset"]] = (
        [repo_type] if repo_type is not None else ["model", "dataset"]
    )
    for index, candidate_repo_type in enumerate(repo_types):
        try:
            downloaded = _download_to_temp(
                _hf_download_url(
                    repo_id=repo_id,
                    repo_type=candidate_repo_type,
                    path=path,
                    revision=revision,
                ),
                destination=destination,
                description=f"unmanaged dataset {source!r}",
                session=session,
            )
        except _DatasetNotFoundError:
            if index + 1 < len(repo_types):
                continue
            raise
        try:
            os.replace(downloaded, destination)
        finally:
            downloaded.unlink(missing_ok=True)
        return str(destination)

    raise DatasetMaterializationError(f"Could not materialize dataset {source!r}.")


def _parse_unmanaged_hf_reference(
    uri: str,
    *,
    version: Optional[str],
) -> tuple[str, str, str]:
    path_with_repo, uri_revision = (
        uri[5:].rsplit("@", maxsplit=1) if "@" in uri[5:] else (uri[5:], None)
    )
    if uri_revision is not None and version is not None and uri_revision != version:
        raise DatasetMaterializationError(
            "Conflicting dataset versions: "
            f"URI requests {uri_revision!r} but version is {version!r}."
        )
    parts = path_with_repo.split("/", maxsplit=2)
    if len(parts) != 3 or not all(parts):
        raise DatasetMaterializationError(
            "Invalid Hugging Face dataset URI. Expected format "
            f"'hf://owner/repo/path/to/file[@revision]', got {uri!r}."
        )
    return f"{parts[0]}/{parts[1]}", parts[2], uri_revision or version or "main"


class _DatasetNotFoundError(DatasetMaterializationError):
    pass


def _hf_download_url(
    *,
    repo_id: str,
    repo_type: Literal["model", "dataset"],
    path: str,
    revision: str,
) -> str:
    prefix = "datasets/" if repo_type == "dataset" else ""
    return (
        f"https://huggingface.co/{prefix}{repo_id}/resolve/"
        f"{quote(revision, safe='')}/{quote(path)}"
    )


def _download_to_temp(
    url: str,
    *,
    destination: Path,
    description: str,
    session=requests,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_name = tempfile.mkstemp(
        prefix=".policyengine-download-",
        suffix=destination.suffix or ".download",
        dir=destination.parent,
    )
    os.close(file_descriptor)
    temp_path = Path(temp_name)
    try:
        with session.get(
            url,
            headers=_hugging_face_auth_headers(),
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
                raise _DatasetNotFoundError(f"Could not find {description} at {url}.")
            response.raise_for_status()
            with temp_path.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def _hugging_face_auth_headers() -> dict[str, str]:
    token = (
        os.environ.get("HUGGING_FACE_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    )
    return {"Authorization": f"Bearer {token}"} if token else {}


def _matching_sha256(path: Path, expected_sha256: str) -> Optional[str]:
    if not path.is_file():
        return None
    actual_sha256 = _sha256_file(path)
    return actual_sha256 if actual_sha256 == expected_sha256 else None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
