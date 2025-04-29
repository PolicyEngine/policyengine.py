from huggingface_hub import hf_hub_download
import os
from getpass import getpass
import time


def download_from_hf(
    repo: str,
    repo_filename: str,
    local_folder: str | None = None,
    version: str | None = None,
):
    token = os.environ.get("HUGGING_FACE_TOKEN")
    if token is None:
        token = getpass(
            "Enter your Hugging Face token (or set HUGGING_FACE_TOKEN environment variable): "
        )
        # Optionally store in env for subsequent calls in same session
        os.environ["HUGGING_FACE_TOKEN"] = token
    try:
        result = hf_hub_download(
            repo_id=repo,
            repo_type="model",
            filename=repo_filename,
            local_dir=local_folder,
            revision=version,
            token=token,
        )
    except:
        # In the case of a 429 Too Many Requests error, retry up to 5 times, waiting 30 seconds
        # between attempts
        for i in range(5):
            try:
                result = hf_hub_download(
                    repo_id=repo,
                    repo_type="model",
                    filename=repo_filename,
                    local_dir=local_folder,
                    revision=version,
                    token=token,
                )
                break
            except Exception as e:
                if i == 4:
                    raise e
                print(f"Error downloading {repo_filename} from {repo}: {e}")
                print("Retrying in 30 seconds...")
                time.sleep(30)
    return result
