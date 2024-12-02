from huggingface_hub import hf_hub_download
import os
from getpass import getpass


def download(
    repo: str, repo_filename: str, local_folder: str, version: str = None
):
    token = os.environ.get("HUGGING_FACE_TOKEN")
    if token is None:
        token = getpass(
            "Enter your Hugging Face token (or set HUGGING_FACE_TOKEN environment variable): "
        )
        # Optionally store in env for subsequent calls in same session
        os.environ["HUGGING_FACE_TOKEN"] = token

    return hf_hub_download(
        repo_id=repo,
        repo_type="model",
        filename=repo_filename,
        local_dir=local_folder,
        revision=version,
        token=token,
    )
