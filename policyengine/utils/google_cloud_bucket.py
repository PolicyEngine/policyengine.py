"""
High-level interface for downloading files from Google Cloud Storage.

This module provides a singleton-based caching client that handles:
- CRC-based cache invalidation (only downloads when content changes)
- Atomic file writes (prevents partial/corrupted files)
- Multiple versioning strategies (generation-based or metadata-based)

Terminology:
- gcs_key: The path to a file within a GCS bucket (e.g., "states/RI.h5")
- local_path: The full local filesystem path where a file is stored
- DATASETS_DIR: The local directory where all downloaded datasets are stored
"""

from pathlib import Path
from typing import Optional, Tuple

from .data.caching_google_storage_client import CachingGoogleStorageClient

_caching_client: CachingGoogleStorageClient | None = None

# All downloaded datasets are stored in this directory
DATASETS_DIR = Path(".datasets")


def _get_client() -> CachingGoogleStorageClient:
    """Get or create the singleton caching client."""
    global _caching_client
    if _caching_client is not None:
        return _caching_client
    _caching_client = CachingGoogleStorageClient()
    return _caching_client


def _clear_client() -> None:
    """Clear the singleton caching client (useful for testing)."""
    global _caching_client
    _caching_client = None


def download_file_from_gcs(
    bucket_name: str,
    gcs_key: str,
    version: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Download a file from Google Cloud Storage to a local path.

    Uses a caching layer that only downloads when the file's CRC changes,
    and writes files atomically to prevent corruption.

    Files are stored in the DATASETS_DIR (.datasets/) directory, preserving
    the GCS key structure. For example:
    - gcs_key="enhanced_cps_2024.h5" -> .datasets/enhanced_cps_2024.h5
    - gcs_key="states/RI.h5" -> .datasets/states/RI.h5
    - gcs_key="districts/CA-01.h5" -> .datasets/districts/CA-01.h5

    Args:
        bucket_name: The name of the GCS bucket.
        gcs_key: The path to the file within the bucket.
        version: Optional version string. Can be:
            - A GCS generation number (integer string)
            - A metadata version string (e.g., "1.2.3")
            - None to get the latest version

    Returns:
        A tuple of (local_path, version) where:
        - local_path: The local filesystem path where the file was saved
        - version: The version string of the downloaded file, or None if
          no version metadata is available
    """
    local_path = DATASETS_DIR / gcs_key
    local_path.parent.mkdir(parents=True, exist_ok=True)

    version = _get_client().download(
        bucket_name,
        gcs_key,
        local_path,
        version=version,
        return_version=True,
    )
    return str(local_path), version
