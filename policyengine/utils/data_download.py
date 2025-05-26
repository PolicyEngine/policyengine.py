from pathlib import Path
import logging
import os
from policyengine.utils.huggingface import download_from_hf
from policyengine.utils.google_cloud_bucket import download_file_from_gcs
from pydantic import BaseModel
import json
from typing import Tuple


def download(
    filepath: str,
    gcs_bucket: str,
    version: str | None = None,
) -> str | Tuple[str, str]:
    logging.info("Using Google Cloud Storage for download.")
    download_file_from_gcs(
        bucket_name=gcs_bucket,
        file_name=filepath,
        destination_path=filepath,
        version=version,
    )
    return filepath
