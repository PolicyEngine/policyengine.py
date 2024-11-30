from huggingface_hub import hf_hub_download
import os


def download(
    repo: str, repo_filename: str, local_folder: str, version: str = None
):
    token = os.environ.get(
        "HUGGING_FACE_TOKEN",
    )
    return hf_hub_download(
        repo_id=repo,
        repo_type="model",
        filename=repo_filename,
        local_dir=local_folder,
        revision=version,
        token=token,
    )
