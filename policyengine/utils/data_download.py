from pathlib import Path
import logging
import os
from policyengine.utils.huggingface import download_from_hf
from policyengine.utils.google_cloud_bucket import download_file_from_gcs
from pydantic import BaseModel
import json
from typing import Tuple


class DataFile(BaseModel):
    filepath: str
    huggingface_org: str
    huggingface_repo: str | None = None
    gcs_bucket: str | None = None


def download(
    filepath: str,
    huggingface_repo: str = None,
    gcs_bucket: str = None,
    huggingface_org: str = "policyengine",
    return_version: bool = False,
) -> str | Tuple[str, str]:
    data_file = DataFile(
        filepath=filepath,
        huggingface_org=huggingface_org,
        huggingface_repo=huggingface_repo,
        gcs_bucket=gcs_bucket,
    )

    logging.info = print
    # NOTE: tests will break on build if you don't default to huggingface.
    if data_file.huggingface_repo is not None:
        logging.info("Using Hugging Face for download.")
        try:
            data = download_from_hf(
                repo=data_file.huggingface_org
                + "/"
                + data_file.huggingface_repo,
                repo_filename=data_file.filepath,
            )
            if return_version:
                version_file = download_from_hf(
                    repo=data_file.huggingface_org
                    + "/"
                    + data_file.huggingface_repo,
                    repo_filename="version.json",
                    return_version=True,
                )
                with open(version_file, "r") as f:
                    version = json.load(f).get("version")
                return data, version
            return data
        except:
            logging.info("Failed to download from Hugging Face.")

    if data_file.gcs_bucket is not None:
        logging.info("Using Google Cloud Storage for download.")
        download_file_from_gcs(
            bucket_name=data_file.gcs_bucket,
            file_name=filepath,
            destination_path=filepath,
        )
        if return_version:
            download_file_from_gcs(
                bucket_name=data_file.gcs_bucket,
                file_name="version.json",
                destination_path="version.json",
            )
            with open("version.json", "r") as f:
                version = json.load(f).get("version")
            return filepath, version
        return filepath

    raise ValueError(
        "No valid download method specified. Please provide either a Hugging Face repo or a Google Cloud Storage bucket."
    )
