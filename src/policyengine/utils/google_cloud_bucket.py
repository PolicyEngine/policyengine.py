"""High-level dataset downloads from Google Cloud Storage."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from policyengine.utils.data.caching_google_storage_client import (
    CachingGoogleStorageClient,
)

DATASETS_DIR = Path(".datasets")

_caching_client: Optional[CachingGoogleStorageClient] = None


def _get_client() -> CachingGoogleStorageClient:
    global _caching_client
    if _caching_client is None:
        _caching_client = CachingGoogleStorageClient()
    return _caching_client


def _clear_client() -> None:
    """Reset the singleton client. Intended for tests."""

    global _caching_client
    _caching_client = None


def download_file_from_gcs(
    bucket_name: str,
    gcs_key: str,
    version: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Download a GCS object into `.datasets`, preserving object path."""

    local_path = DATASETS_DIR / gcs_key
    local_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_version = _get_client().download(
        bucket_name,
        gcs_key,
        local_path,
        version=version,
        return_version=True,
    )
    return str(local_path), resolved_version
