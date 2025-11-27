"""
Download orchestration for GCS-hosted datasets.
"""

import logging
from typing import Optional, Tuple

from policyengine.utils.google_cloud_bucket import download_file_from_gcs


def download(
    filepath: str,
    gcs_bucket: str,
    version: Optional[str] = None,
    return_version: bool = False,
) -> Tuple[str, Optional[str]] | str:
    """
    Download a file from Google Cloud Storage.

    Args:
        filepath: The path to the file within the bucket. Also used as the
            local destination path.
        gcs_bucket: The name of the GCS bucket.
        version: Optional version string. Can be:
            - A GCS generation number (integer string)
            - A metadata version string (e.g., "1.2.3")
            - None to get the latest version
        return_version: If True, return a tuple of (filepath, version).

    Returns:
        If return_version is True: (filepath, version) tuple
        Otherwise: just the filepath string
    """
    logging.info("Using Google Cloud Storage for download.")
    downloaded_version = download_file_from_gcs(
        bucket_name=gcs_bucket,
        file_name=filepath,
        destination_path=filepath,
        version=version,
    )
    if return_version:
        return filepath, downloaded_version
    return filepath
