"""Runtime dataset source materialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from policyengine.utils.google_cloud_bucket import download_file_from_gcs


@dataclass(frozen=True)
class GCSArtifactReference:
    bucket: str
    path: str
    version: Optional[str] = None


@dataclass(frozen=True)
class HFArtifactReference:
    repo_id: str
    path: str
    version: Optional[str] = None


def _select_version(
    uri_version: Optional[str],
    requested_version: Optional[str],
) -> Optional[str]:
    if (
        uri_version is not None
        and requested_version is not None
        and uri_version != requested_version
    ):
        raise ValueError(
            "Conflicting dataset versions: "
            f"URI requests {uri_version!r} but version is {requested_version!r}"
        )
    return uri_version or requested_version


def parse_gs_uri(uri: str) -> GCSArtifactReference:
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS dataset URI: {uri!r}")

    path_with_bucket, version = (
        uri[5:].rsplit("@", maxsplit=1) if "@" in uri[5:] else (uri[5:], None)
    )
    bucket, separator, path = path_with_bucket.partition("/")
    if not bucket or not separator or not path:
        raise ValueError(
            "Invalid GCS dataset URI. Expected format "
            f"'gs://bucket/path/to/file[@version]', got {uri!r}."
        )
    return GCSArtifactReference(bucket=bucket, path=path, version=version)


def parse_hf_uri(uri: str) -> HFArtifactReference:
    if not uri.startswith("hf://"):
        raise ValueError(f"Invalid Hugging Face dataset URI: {uri!r}")

    path_with_repo, version = (
        uri[5:].rsplit("@", maxsplit=1) if "@" in uri[5:] else (uri[5:], None)
    )
    parts = path_with_repo.split("/", maxsplit=2)
    if len(parts) != 3 or not all(parts):
        raise ValueError(
            "Invalid Hugging Face dataset URI. Expected format "
            f"'hf://owner/repo/path/to/file[@revision]', got {uri!r}."
        )
    return HFArtifactReference(
        repo_id=f"{parts[0]}/{parts[1]}",
        path=parts[2],
        version=version,
    )


def materialize_dataset_source(
    dataset_source: str,
    *,
    version: Optional[str] = None,
) -> str:
    """Return a local file path for supported remote dataset URIs."""

    if dataset_source.startswith("gs://"):
        reference = parse_gs_uri(dataset_source)
        local_path, _ = download_file_from_gcs(
            reference.bucket,
            reference.path,
            version=_select_version(reference.version, version),
        )
        return local_path

    if dataset_source.startswith("hf://"):
        from policyengine_core.tools.hugging_face import (
            download_huggingface_dataset,
        )

        reference = parse_hf_uri(dataset_source)
        try:
            return download_huggingface_dataset(
                reference.repo_id,
                reference.path,
                version=_select_version(reference.version, version),
            )
        except Exception:
            # The core helper assumes a model-type repo; certified data
            # releases may live in dataset-type repos (e.g.
            # policyengine/populace-us). Retry with the dataset repo type
            # before surfacing the original failure.
            from huggingface_hub import hf_hub_download

            return hf_hub_download(
                repo_id=reference.repo_id,
                repo_type="dataset",
                filename=reference.path,
                revision=_select_version(reference.version, version),
            )

    return dataset_source
