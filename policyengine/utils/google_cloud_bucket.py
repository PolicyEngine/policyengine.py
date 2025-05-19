from .data.caching_google_storage_client import CachingGoogleStorageClient
import asyncio
from pathlib import Path

_caching_client: CachingGoogleStorageClient | None = None


def _get_client():
    global _caching_client
    if _caching_client is not None:
        return _caching_client
    _caching_client = CachingGoogleStorageClient()
    return _caching_client


def _clear_client():
    global _caching_client
    _caching_client = None


def download_file_from_gcs(
    bucket_name: str, file_name: str, destination_path: str
) -> None:
    """
    Download a file from Google Cloud Storage to a local path.

    Args:
        bucket_name (str): The name of the GCS bucket.
        file_name (str): The name of the file in the GCS bucket.
        destination_path (str): The local path where the file will be saved.

    Returns:
        None
    """
    _get_client().download(bucket_name, file_name, Path(destination_path))
