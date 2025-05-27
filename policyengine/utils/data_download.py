from pathlib import Path
import logging
import os
from policyengine.utils.google_cloud_bucket import download_file_from_gcs
from pydantic import BaseModel
import json
from typing import Tuple, Optional


def download(
    filepath: str,
    gcs_bucket: str,
    version: Optional[str] = None,
    return_version: bool = False,
) -> Tuple[str, Optional[str]]:
    logging.info("Using Google Cloud Storage for download.")
    version = download_file_from_gcs(
        bucket_name=gcs_bucket,
        file_name=filepath,
        destination_path=filepath,
        version=version,
    )
    if return_version:
        return filepath, version
    return filepath
