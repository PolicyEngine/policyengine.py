"""
Download orchestration for GCS-hosted datasets.

Terminology:
- gcs_key: The path to a file within a GCS bucket (e.g., "states/RI.h5")
- local_path: The full local filesystem path where a file is stored
"""

import logging
from typing import Optional, Tuple

from policyengine.utils.google_cloud_bucket import download_file_from_gcs


def download(
    gcs_key: str,
    gcs_bucket: str,
    version: Optional[str] = None,
    return_version: bool = False,
) -> Tuple[str, Optional[str]] | str:
    """
    Download a file from Google Cloud Storage.

    Args:
        gcs_key: The path to the file within the bucket (e.g., "states/RI.h5").
        gcs_bucket: The name of the GCS bucket.
        version: Optional version string. Can be:
            - A GCS generation number (integer string)
            - A metadata version string (e.g., "1.2.3")
            - None to get the latest version
        return_version: If True, return a tuple of (local_path, version).

    Returns:
        If return_version is True: (local_path, version) tuple
        Otherwise: just the local_path string
    """
    logging.info("Using Google Cloud Storage for download.")
    local_path, downloaded_version = download_file_from_gcs(
        bucket_name=gcs_bucket,
        gcs_key=gcs_key,
        version=version,
    )
    if return_version:
        return local_path, downloaded_version
    return local_path
