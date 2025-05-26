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
) -> str | Tuple[str, str]:
    logging.info("Using Google Cloud Storage for download.")
    download_file_from_gcs(
        bucket_name=gcs_bucket,
        file_name=filepath,
        destination_path=filepath,
    )
    if return_version:
        download_file_from_gcs(
            bucket_name=gcs_bucket,
            file_name="version.json",
            destination_path="version.json",
        )
        with open("version.json", "r") as f:
            version = json.load(f).get("version")
        return filepath, version
    return filepath
