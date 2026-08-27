"""Resolve and materialize datasets certified by a PolicyEngine.py bundle."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional, Union, cast
from urllib.parse import quote

import requests
from pydantic import BaseModel

from .manifest import (
    CountryReleaseManifest,
    _artifact_revision,
    build_hf_uri,
    get_release_manifest,
    resolve_local_managed_dataset_source,
)

DEFAULT_DATA_DIR = Path("./data")
BACKUP_DIR_NAME = ".policyengine-bundle-backups"
DOWNLOAD_TIMEOUT_SECONDS = 60


class DatasetMaterializationError(ValueError):
    """Raised when a dataset cannot be resolved or materialized safely."""


class BundleDatasetPlan(BaseModel):
    """Exact bundle metadata needed to materialize one managed dataset."""

    country_id: str
    dataset: str
    data_package_name: str
    repo_id: str
    repo_type: Literal["model", "dataset"]
    path: str
    revision: str
    expected_sha256: str
    source_uri: str
    destination: Path
    build_id: Optional[str] = None
    metadata_expected_sha256: Optional[str] = None
    metadata_source_uri: Optional[str] = None
    metadata_destination: Optional[Path] = None


class MaterializedDataset(BaseModel):
    """Verified local representation of one bundle-managed dataset."""

    country_id: str
    dataset: str
    data_package_name: str
    repo_id: str
    repo_type: Literal["model", "dataset"]
    revision: str
    source_uri: str
    expected_sha256: str
    actual_sha256: str
    path: Path
    cache_hit: bool
    build_id: Optional[str] = None
    metadata_expected_sha256: Optional[str] = None
    metadata_actual_sha256: Optional[str] = None
    metadata_path: Optional[Path] = None


class _DatasetPackageStrategy:
    """Package-specific behavior for a bundle dataset source."""

    def validate(self, plan: BundleDatasetPlan) -> None:
        raise NotImplementedError

    def materialize(
        self,
        plan: BundleDatasetPlan,
        *,
        session=requests,
    ) -> MaterializedDataset:
        raise NotImplementedError


class _CountryDataPackageStrategy(_DatasetPackageStrategy):
    def validate(self, plan: BundleDatasetPlan) -> None:
        package_name = plan.data_package_name
        if not (
            package_name.startswith("policyengine-") and package_name.endswith("-data")
        ):
            raise DatasetMaterializationError(
                f"Unsupported country data package: {package_name!r}."
            )

    def materialize(
        self,
        plan: BundleDatasetPlan,
        *,
        session=requests,
    ) -> MaterializedDataset:
        return _materialize_country_data_package(plan, session=session)


class _PopulaceDataPackageStrategy(_DatasetPackageStrategy):
    def validate(self, plan: BundleDatasetPlan) -> None:
        if plan.data_package_name != "populace-data":
            raise DatasetMaterializationError(
                f"Unsupported Populace data package: {plan.data_package_name!r}."
            )

    def materialize(
        self,
        plan: BundleDatasetPlan,
        *,
        session=requests,
    ) -> MaterializedDataset:
        return _materialize_populace_data_package(plan, session=session)


def _dataset_package_strategy(data_package_name: str) -> _DatasetPackageStrategy:
    if data_package_name == "populace-data":
        return _PopulaceDataPackageStrategy()
    if data_package_name.startswith("policyengine-") and data_package_name.endswith(
        "-data"
    ):
        return _CountryDataPackageStrategy()
    raise DatasetMaterializationError(
        "Unsupported bundle data package "
        f"{data_package_name!r}; expected 'populace-data' or "
        "'policyengine-<country>-data'."
    )


def resolve_bundle_dataset_plan(
    country_id: str,
    dataset: Optional[str] = None,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    manifest: Optional[CountryReleaseManifest] = None,
) -> BundleDatasetPlan:
    """Resolve one logical dataset to its exact bundle-certified source."""

    country_manifest = manifest or get_release_manifest(country_id)
    dataset_name = dataset or country_manifest.default_dataset
    reference = country_manifest.datasets.get(dataset_name)
    if reference is None:
        raise DatasetMaterializationError(
            f"Unknown managed dataset {dataset_name!r} for country "
            f"{country_id!r}. Known datasets: "
            f"{sorted(country_manifest.datasets)}"
        )

    data_package_name = (
        reference.data_package_name or country_manifest.data_package.name
    )
    repo_id = reference.repo_id or country_manifest.data_package.repo_id
    repo_type = reference.repo_type or country_manifest.data_package.repo_type
    revision = reference.revision or _artifact_revision(country_manifest.data_package)
    if repo_type not in {"model", "dataset"}:
        raise DatasetMaterializationError(
            f"Dataset {dataset_name!r} has unsupported Hugging Face repository "
            f"type {repo_type!r}."
        )
    validated_repo_type = cast(Literal["model", "dataset"], repo_type)
    if not reference.sha256:
        raise DatasetMaterializationError(
            f"Managed dataset {dataset_name!r} is missing a certified sha256."
        )

    plan = BundleDatasetPlan(
        country_id=country_id,
        dataset=dataset_name,
        data_package_name=data_package_name,
        repo_id=repo_id,
        repo_type=validated_repo_type,
        path=reference.path,
        revision=revision,
        expected_sha256=reference.sha256,
        source_uri=build_hf_uri(repo_id, reference.path, revision),
        destination=data_dir / Path(reference.path).name,
        build_id=(
            country_manifest.certified_data_artifact.build_id
            if country_manifest.certified_data_artifact is not None
            else None
        ),
        metadata_expected_sha256=reference.metadata_sha256,
        metadata_source_uri=(
            build_hf_uri(repo_id, f"{reference.path}.metadata.json", revision)
            if reference.metadata_sha256
            else None
        ),
        metadata_destination=(
            data_dir / f"{Path(reference.path).name}.metadata.json"
            if reference.metadata_sha256
            else None
        ),
    )
    _dataset_package_strategy(data_package_name).validate(plan)
    return plan


def materialize_bundle_dataset(
    country_id: str,
    dataset: Optional[str] = None,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    manifest: Optional[CountryReleaseManifest] = None,
    allow_local_mirror: bool = True,
    session=requests,
) -> MaterializedDataset:
    """Download and verify one dataset certified by the release bundle."""

    plan = resolve_bundle_dataset_plan(
        country_id,
        dataset,
        data_dir=data_dir,
        manifest=manifest,
    )
    local_source = resolve_local_managed_dataset_source(
        country_id,
        plan.source_uri,
        allow_local_mirror=allow_local_mirror,
    )
    if local_source != plan.source_uri:
        local_path = Path(local_source).expanduser()
        if local_path.is_file():
            actual_sha256 = _sha256_file(local_path)
            if actual_sha256 == plan.expected_sha256:
                metadata_path = Path(f"{local_path}.metadata.json")
                if plan.metadata_expected_sha256 is None:
                    return _materialized_result(
                        plan,
                        actual_sha256=actual_sha256,
                        cache_hit=True,
                        path=local_path,
                    )
                if metadata_path.is_file():
                    metadata_actual_sha256 = _sha256_file(metadata_path)
                    if metadata_actual_sha256 == plan.metadata_expected_sha256:
                        return _materialized_result(
                            plan,
                            actual_sha256=actual_sha256,
                            cache_hit=True,
                            path=local_path,
                            metadata_actual_sha256=metadata_actual_sha256,
                            metadata_path=metadata_path,
                        )
    strategy = _dataset_package_strategy(plan.data_package_name)
    return strategy.materialize(plan, session=session)


def _materialize_country_data_package(
    plan: BundleDatasetPlan,
    *,
    session=requests,
) -> MaterializedDataset:
    return _materialize_managed_hf_dataset(plan, session=session)


def _materialize_populace_data_package(
    plan: BundleDatasetPlan,
    *,
    session=requests,
) -> MaterializedDataset:
    return _materialize_managed_hf_dataset(plan, session=session)


def _materialize_managed_hf_dataset(
    plan: BundleDatasetPlan,
    *,
    session=requests,
) -> MaterializedDataset:
    destination = plan.destination
    if destination.is_file():
        actual_sha256 = _sha256_file(destination)
        if actual_sha256 == plan.expected_sha256:
            metadata_actual_sha256, metadata_path = _materialize_metadata(
                plan,
                session=session,
            )
            return _materialized_result(
                plan,
                actual_sha256=actual_sha256,
                cache_hit=True,
                metadata_actual_sha256=metadata_actual_sha256,
                metadata_path=metadata_path,
            )

    url = _hf_download_url(
        repo_id=plan.repo_id,
        repo_type=plan.repo_type,
        path=plan.path,
        revision=plan.revision,
    )
    downloaded = _download_to_temp(
        url,
        destination=destination,
        source_description=(f"{plan.country_id.upper()} dataset {plan.dataset!r}"),
        session=session,
    )
    try:
        actual_sha256 = _sha256_file(downloaded)
        if actual_sha256 != plan.expected_sha256:
            raise DatasetMaterializationError(
                f"Downloaded {plan.country_id.upper()} dataset {plan.dataset!r} "
                f"has sha256 {actual_sha256}, expected {plan.expected_sha256}."
            )
        _backup_existing(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(downloaded, destination)
    finally:
        downloaded.unlink(missing_ok=True)

    metadata_actual_sha256, metadata_path = _materialize_metadata(
        plan,
        session=session,
    )
    return _materialized_result(
        plan,
        actual_sha256=actual_sha256,
        cache_hit=False,
        metadata_actual_sha256=metadata_actual_sha256,
        metadata_path=metadata_path,
    )


def _materialized_result(
    plan: BundleDatasetPlan,
    *,
    actual_sha256: str,
    cache_hit: bool,
    path: Optional[Path] = None,
    metadata_actual_sha256: Optional[str] = None,
    metadata_path: Optional[Path] = None,
) -> MaterializedDataset:
    return MaterializedDataset(
        country_id=plan.country_id,
        dataset=plan.dataset,
        data_package_name=plan.data_package_name,
        repo_id=plan.repo_id,
        repo_type=plan.repo_type,
        revision=plan.revision,
        source_uri=plan.source_uri,
        expected_sha256=plan.expected_sha256,
        actual_sha256=actual_sha256,
        path=path or plan.destination,
        cache_hit=cache_hit,
        build_id=plan.build_id,
        metadata_expected_sha256=plan.metadata_expected_sha256,
        metadata_actual_sha256=metadata_actual_sha256,
        metadata_path=metadata_path,
    )


def _materialize_metadata(
    plan: BundleDatasetPlan,
    *,
    session=requests,
) -> tuple[Optional[str], Optional[Path]]:
    if plan.metadata_expected_sha256 is None:
        return None, None
    if plan.metadata_destination is None:
        raise DatasetMaterializationError(
            f"Managed dataset {plan.dataset!r} has a metadata hash but no "
            "metadata destination."
        )

    destination = plan.metadata_destination
    if destination.is_file():
        actual_sha256 = _sha256_file(destination)
        if actual_sha256 == plan.metadata_expected_sha256:
            return actual_sha256, destination

    url = _hf_download_url(
        repo_id=plan.repo_id,
        repo_type=plan.repo_type,
        path=f"{plan.path}.metadata.json",
        revision=plan.revision,
    )
    downloaded = _download_to_temp(
        url,
        destination=destination,
        source_description=f"metadata for {plan.dataset!r}",
        session=session,
    )
    try:
        actual_sha256 = _sha256_file(downloaded)
        if actual_sha256 != plan.metadata_expected_sha256:
            raise DatasetMaterializationError(
                f"Downloaded metadata for dataset {plan.dataset!r} has sha256 "
                f"{actual_sha256}, expected {plan.metadata_expected_sha256}."
            )
        _backup_existing(destination)
        os.replace(downloaded, destination)
    finally:
        downloaded.unlink(missing_ok=True)
    return actual_sha256, destination


class _UnmanagedHFReference(BaseModel):
    repo_id: str
    path: str
    revision: str


class _DatasetNotFoundError(DatasetMaterializationError):
    pass


def materialize_unmanaged_dataset_source(
    dataset_source: Union[str, Path],
    *,
    version: Optional[str] = None,
    data_dir: Path = DEFAULT_DATA_DIR,
    repo_type: Optional[Literal["model", "dataset"]] = None,
    session=requests,
) -> str:
    """Return a local path for an explicitly unmanaged local or HF source."""

    source = str(dataset_source)
    if source.startswith("gs://"):
        raise DatasetMaterializationError(
            "GCS dataset sources are no longer supported. Publish the dataset "
            "on Hugging Face and reference that artifact instead."
        )
    if not source.startswith("hf://"):
        if "://" in source:
            raise DatasetMaterializationError(
                f"Unsupported unmanaged dataset URI: {source!r}."
            )
        return source

    reference = _parse_unmanaged_hf_reference(source, version=version)
    destination = data_dir / Path(reference.path).name
    repo_types: list[Literal["model", "dataset"]] = (
        [repo_type] if repo_type is not None else ["model", "dataset"]
    )
    for index, candidate_repo_type in enumerate(repo_types):
        try:
            downloaded = _download_to_temp(
                _hf_download_url(
                    repo_id=reference.repo_id,
                    repo_type=candidate_repo_type,
                    path=reference.path,
                    revision=reference.revision,
                ),
                destination=destination,
                source_description=f"unmanaged dataset {source!r}",
                session=session,
            )
        except _DatasetNotFoundError:
            if index + 1 < len(repo_types):
                continue
            raise
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(downloaded, destination)
        return str(destination)

    raise DatasetMaterializationError(f"Could not materialize dataset {source!r}.")


def _parse_unmanaged_hf_reference(
    uri: str,
    *,
    version: Optional[str],
) -> _UnmanagedHFReference:
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
    return _UnmanagedHFReference(
        repo_id=f"{parts[0]}/{parts[1]}",
        path=parts[2],
        revision=uri_revision or version or "main",
    )


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
    source_description: str,
    session=requests,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    suffix = destination.suffix or ".download"
    file_descriptor, temp_name = tempfile.mkstemp(
        prefix=".policyengine-download-",
        suffix=suffix,
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
                    f"Could not download {source_description}: Hugging Face "
                    "rejected the configured credentials. Set HUGGING_FACE_TOKEN "
                    "to a token with access to the certified repository."
                )
            if response.status_code == 404:
                raise _DatasetNotFoundError(
                    f"Could not find {source_description} at {url}."
                )
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


def _backup_existing(path: Path) -> None:
    if not path.exists():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_dir = path.parent / BACKUP_DIR_NAME / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(backup_dir / path.name))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
