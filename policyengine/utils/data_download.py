from pathlib import Path
import logging
import os
from policyengine.utils.huggingface import download_from_hf
from policyengine.utils.google_cloud_bucket import download_file_from_gcs
from pydantic import BaseModel


class DataFile(BaseModel):
    filepath: str
    huggingface_org: str
    huggingface_repo: str
    gcs_bucket: str


def download(
    filepath: str,
    huggingface_repo: str,
    gcs_bucket: str,
    huggingface_org: str = "policyengine",
):
    data_file = DataFile(
        filepath=filepath,
        huggingface_org=huggingface_org,
        huggingface_repo=huggingface_repo,
        gcs_bucket=gcs_bucket,
    )

    logging.info = print
    if Path(filepath).exists():
        logging.info(f"File {filepath} already exists. Skipping download.")
        return filepath

    logging.info("Using Hugging Face for download.")
    try:
        raise ValueError()
        return download_from_hf(
            repo=data_file.huggingface_org + "/" + data_file.huggingface_repo,
            repo_filename=data_file.filepath,
        )
    except:
        logging.info(
            "Failed to download from Hugging Face. Retrying with Google Cloud Storage."
        )

    logging.info("Using Google Cloud Storage for download.")
    download_file_from_gcs(
        bucket_name=data_file.gcs_bucket,
        file_name=filepath,
        destination_path=filepath,
    )
    return filepath
