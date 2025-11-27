"""
High-level interface for downloading files from Google Cloud Storage.

This module provides a singleton-based caching client that handles:
- CRC-based cache invalidation (only downloads when content changes)
- Atomic file writes (prevents partial/corrupted files)
- Multiple versioning strategies (generation-based or metadata-based)
"""

from pathlib import Path
from typing import Optional

from .data.caching_google_storage_client import CachingGoogleStorageClient

_caching_client: CachingGoogleStorageClient | None = None


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
    file_name: str,
    destination_path: str,
    version: Optional[str] = None,
) -> str | None:
    """
    Download a file from Google Cloud Storage to a local path.

    Uses a caching layer that only downloads when the file's CRC changes,
    and writes files atomically to prevent corruption.

    Args:
        bucket_name: The name of the GCS bucket.
        file_name: The path to the file within the bucket.
        destination_path: The local path where the file will be saved.
        version: Optional version string. Can be:
            - A GCS generation number (integer string)
            - A metadata version string (e.g., "1.2.3")
            - None to get the latest version

    Returns:
        The version string of the downloaded file, or None if no version
        metadata is available.
    """
    version = _get_client().download(
        bucket_name,
        file_name,
        Path(destination_path),
        version=version,
        return_version=True,
    )
    return version
