"""Downloads for explicit Hugging Face dataset inputs."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import requests

from policyengine.provenance.dataset_materialization import (
    DatasetMaterializationError,
)
from policyengine.provenance.manifest import (
    https_dataset_uri,
    hugging_face_auth_headers,
)

DEFAULT_DATA_DIR = Path("./data")
DOWNLOAD_TIMEOUT_SECONDS = 60


def download_hf_dataset(
    dataset_uri: str,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> str:
    """Download an explicit Hugging Face dataset URI and return its local path."""

    if not dataset_uri.startswith("hf://"):
        raise DatasetMaterializationError(
            f"Expected an hf:// dataset URI, got {dataset_uri!r}."
        )

    path_with_repo, revision = (
        dataset_uri[5:].rsplit("@", maxsplit=1)
        if "@" in dataset_uri[5:]
        else (dataset_uri[5:], "main")
    )
    parts = path_with_repo.split("/", maxsplit=2)
    if len(parts) != 3 or not all(parts):
        raise DatasetMaterializationError(
            "Invalid Hugging Face dataset URI. Expected format "
            f"'hf://owner/repo/path/to/file[@revision]', got {dataset_uri!r}."
        )

    repo_id = f"{parts[0]}/{parts[1]}"
    repository_path = parts[2]
    destination = data_dir / Path(repository_path).name
    destination.parent.mkdir(parents=True, exist_ok=True)

    for repo_type in ("model", "dataset"):
        file_descriptor, temp_name = tempfile.mkstemp(
            prefix=".policyengine-download-",
            suffix=destination.suffix or ".download",
            dir=destination.parent,
        )
        os.close(file_descriptor)
        temporary_path = Path(temp_name)
        url = https_dataset_uri(
            repo_id,
            repository_path,
            revision,
            repo_type=repo_type,
        )
        try:
            with requests.get(
                url,
                headers=hugging_face_auth_headers(),
                stream=True,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            ) as response:
                if response.status_code in {401, 403}:
                    raise DatasetMaterializationError(
                        "Could not download explicit dataset "
                        f"{dataset_uri!r}: Hugging Face rejected the configured "
                        "credentials. Set HUGGING_FACE_TOKEN to a token with "
                        "access to the repository."
                    )
                if response.status_code == 404:
                    if repo_type == "model":
                        continue
                    raise DatasetMaterializationError(
                        f"Could not find explicit dataset {dataset_uri!r}."
                    )
                response.raise_for_status()
                with temporary_path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)
            os.replace(temporary_path, destination)
            return str(destination)
        finally:
            temporary_path.unlink(missing_ok=True)

    raise DatasetMaterializationError(
        f"Could not download explicit dataset {dataset_uri!r}."
    )
