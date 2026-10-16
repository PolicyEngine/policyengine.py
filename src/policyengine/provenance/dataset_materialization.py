"""Make bundle-certified datasets available as verified local files."""

from __future__ import annotations

import datetime
import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

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
    downloaded_sha256: Optional[str] = None
    """sha256 of the bytes downloaded for an explicit Hugging Face URI.

    Nothing verifies an explicit URI's contents, but this records what was
    downloaded, so a later check can tell whether the file at ``path`` is
    still those bytes (see :func:`dataset_source_change`). ``None`` for a
    bundle dataset, whose verified sha256 is on ``bundle_dataset``, and for a
    local file.
    """

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


def _parse_hugging_face_uri(dataset_uri: str) -> tuple[str, str, str]:
    """Split ``hf://owner/repo/path[@revision]`` into repo, path and revision.

    The revision defaults to ``main``.
    """
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
    return f"{parts[0]}/{parts[1]}", parts[2], revision


def _download_hugging_face_dataset(
    dataset_uri: str,
    *,
    data_dir: Path,
) -> DatasetSource:
    repo_id, repository_path, revision = _parse_hugging_face_uri(dataset_uri)
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
                digest = hashlib.sha256()
                with temporary_path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)
                            digest.update(chunk)
            os.replace(temporary_path, destination)
            return DatasetSource(
                source_uri=dataset_uri,
                path=str(destination),
                downloaded_sha256=digest.hexdigest(),
            )
        finally:
            temporary_path.unlink(missing_ok=True)

    raise DatasetMaterializationError(
        f"Could not download explicit dataset {dataset_uri!r}."
    )


def _use_local_dataset(dataset_path: str) -> DatasetSource:
    return DatasetSource(source_uri=dataset_path, path=dataset_path)


def dataset_source_identity(source: DatasetSource) -> dict[str, Any]:
    """Return the identity of a dataset source, for files derived from it.

    A file derived from a source (such as a US year file) records this, so a
    later request for the same logical dataset can tell whether the source
    it would use now is the one the file was derived from. The identity has
    one of three shapes:

    - a bundle dataset: ``{"uri": ..., "sha256": ...}``, the
      ``hf://repo/path@revision`` URI the bundle manifest pins and the sha256
      that the materialized file was verified against. This includes a
      request of the certified default dataset's own URI, which selects the
      bundle dataset;
    - any other explicit Hugging Face URI (``allow_unmanaged=True``):
      ``{"uri": ...}``, the URI as given. Nothing verified its contents, so a
      URI that does not pin a revision, or pins a branch, names whatever the
      branch holds;
    - a local file (``allow_unmanaged=True``): ``{"path": ..., "size": ...,
      "mtime_ns": ...}``, its resolved path, and its size in bytes and
      modification time in nanoseconds from one ``stat()``.

    Computing it reads no source contents. See
    :func:`requested_dataset_source_identity` for the identity a request
    gives without materializing it, and :func:`dataset_source_snapshot` and
    :func:`dataset_source_change` to check a materialized source again.
    """
    if source.bundle_dataset is not None:
        return {
            "uri": source.bundle_dataset.source_uri,
            "sha256": source.bundle_dataset.sha256,
        }
    if "://" in source.source_uri:
        return {"uri": source.source_uri}
    return _local_file_identity(source.path)


def requested_dataset_source_identity(
    country_id: str,
    dataset: Optional[str] = None,
    *,
    allow_unmanaged: bool = True,
) -> dict[str, Any]:
    """Return the identity of the source ``materialize_dataset`` would use.

    This is what :func:`dataset_source_identity` gives for
    ``materialize_dataset(country_id, dataset, allow_unmanaged=...)``,
    computed without downloading anything or reading the source's contents:
    the bundle manifest entry for a bundle dataset (or the certified default's
    own URI), the URI for any other explicit Hugging Face URI, and file-system
    metadata for a local file. A name that is neither a bundle dataset nor a
    local file is looked up in the data release manifest, as
    ``materialize_dataset`` does.

    A request ``materialize_dataset`` would refuse with the same
    ``allow_unmanaged`` raises the same error here. The default,
    ``allow_unmanaged=True``, gives an unmanaged request's identity without
    enforcing bundle selection.
    """
    manifest = get_release_manifest(country_id)
    if dataset is None or dataset == manifest.default_dataset_uri:
        dataset = manifest.default_dataset
    if dataset in manifest.datasets:
        bundle_dataset = _resolve_bundle_dataset(country_id, dataset, manifest=manifest)
        return {"uri": bundle_dataset.source_uri, "sha256": bundle_dataset.sha256}
    source_uri = resolve_managed_dataset_reference(
        country_id, dataset, allow_unmanaged=allow_unmanaged
    )
    if source_uri.startswith("hf://"):
        _parse_hugging_face_uri(source_uri)
        return {"uri": source_uri}
    if "://" in source_uri:
        raise DatasetMaterializationError(
            f"Unsupported explicit dataset URI: {source_uri!r}."
        )
    return _local_file_identity(source_uri)


def dataset_source_snapshot(source: DatasetSource) -> dict[str, int]:
    """Return the materialized file's size and modification time.

    Taken right after ``materialize_dataset`` returns, it lets
    :func:`dataset_source_change` tell whether the file at ``source.path`` has
    been modified or replaced since. Device and inode numbers are left out,
    since some file systems (FUSE mounts such as sshfs without
    ``-o use_ino``) do not keep them stable. A downloaded file is also checked
    by its sha256, so the snapshot matters most for a local file.
    """
    status = os.stat(source.path)
    return {"size": status.st_size, "mtime_ns": status.st_mtime_ns}


def dataset_source_change(
    source: DatasetSource,
    identity: dict[str, Any],
    snapshot: dict[str, int],
) -> Optional[str]:
    """Return how a materialized source has changed, or ``None``.

    ``identity`` is what :func:`dataset_source_identity` gave for ``source``,
    and ``snapshot`` what :func:`dataset_source_snapshot` gave right after it
    was materialized. Another process can replace a file in a shared data
    folder, for example by materializing another release of the same
    dataset, or another file with the same name, there.

    The file must still have the snapshot's size and modification time,
    whatever the kind of source. A downloaded file must also still hash to
    the sha256 it was verified against (a bundle dataset) or downloaded with
    (an explicit URI), so a replacement is caught even when it lands within
    one timestamp tick, or before the snapshot. A local file must still have
    its identity.

    Two gaps remain. Whatever the source, a file swapped out while it is
    loaded and then restored (renamed aside and back, or copied back with its
    times kept) is not noticed: it is checked when the year files are
    stamped, not as it is read. And a local file modified, or replaced by a
    file of the same size, within one tick of the file system's timestamp
    resolution is not noticed either; a downloaded file's bytes would not
    hash to its sha256.

    Returns:
        ``None`` when the source still matches; otherwise a clause saying
        what changed.
    """
    try:
        now = dataset_source_snapshot(source)
    except FileNotFoundError:
        return f"{source.path} no longer exists"
    if now != snapshot:
        return (
            f"{source.path} was replaced or modified (its size or modification "
            "time changed)"
        )
    expected: Optional[tuple[str, str]] = None
    if "sha256" in identity:
        expected = ("verified", identity["sha256"])
    elif source.downloaded_sha256 is not None:
        expected = ("downloaded", source.downloaded_sha256)
    if expected is not None:
        kind, sha256 = expected
        try:
            actual = sha256_file(source.path)
        except FileNotFoundError:
            return f"{source.path} no longer exists"
        if actual != sha256:
            return f"{source.path} has sha256 {actual}, not the {kind} {sha256}"
    if "path" in identity:
        try:
            local = _local_file_identity(source.path)
        except FileNotFoundError:
            return f"{identity['path']} no longer exists"
        if local != identity:
            return (
                f"{describe_dataset_source_identity(identity)} is now "
                f"{describe_dataset_source_identity(local)}"
            )
    return None


def _local_file_identity(path: str | Path) -> dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    status = resolved.stat()
    return {
        "path": str(resolved),
        "size": status.st_size,
        "mtime_ns": status.st_mtime_ns,
    }


def is_dataset_source_identity(value: Any) -> bool:
    """Return whether ``value`` has a shape :func:`dataset_source_identity` gives."""
    if not isinstance(value, dict):
        return False
    if set(value) == {"uri", "sha256"}:
        return isinstance(value["uri"], str) and isinstance(value["sha256"], str)
    if set(value) == {"uri"}:
        return isinstance(value["uri"], str)
    if set(value) == {"path", "size", "mtime_ns"}:
        # ``type(...) is int``: JSON ``true`` loads as ``True``, which equals 1.
        return (
            isinstance(value["path"], str)
            and type(value["size"]) is int
            and type(value["mtime_ns"]) is int
        )
    return False


def describe_dataset_source_identity(identity: dict[str, Any]) -> str:
    """Describe a well-formed source identity in words (see
    :func:`is_dataset_source_identity`)."""
    if "uri" in identity:
        uri: str = identity["uri"]
        if "sha256" in identity:
            return f"{uri} (sha256 {identity['sha256']})"
        return uri
    return (
        f"{identity['path']} ({identity['size']} bytes, modified "
        f"{_describe_mtime_ns(identity['mtime_ns'])})"
    )


def _describe_mtime_ns(mtime_ns: int) -> str:
    """Format a modification time as UTC ISO 8601, to the nanosecond."""
    seconds, nanoseconds = divmod(mtime_ns, 1_000_000_000)
    try:
        moment = datetime.datetime.fromtimestamp(seconds, datetime.UTC)
    except (OverflowError, OSError, ValueError):
        return f"at {mtime_ns} ns since the epoch"
    return f"{moment:%Y-%m-%dT%H:%M:%S}.{nanoseconds:09d}Z"


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
