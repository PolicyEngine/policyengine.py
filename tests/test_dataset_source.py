from pathlib import Path
from unittest.mock import patch

import pytest

import policyengine.tax_benefit_models.common.dataset_source as dataset_source
from policyengine.provenance.dataset_materialization import (
    DatasetMaterializationError,
)
from policyengine.tax_benefit_models.common.dataset_source import download_hf_dataset


class _Response:
    def __init__(self, payload: bytes = b"dataset", status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size):
        yield self.payload


class _Session:
    def __init__(self, *responses: _Response):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _download(uri, tmp_path, session):
    with patch.object(dataset_source.requests, "get", side_effect=session.get):
        return download_hf_dataset(uri, data_dir=tmp_path)


def test_explicit_hf_download_retries_dataset_repository_after_model_404(tmp_path):
    session = _Session(_Response(status_code=404), _Response(b"dataset"))

    result = _download(
        "hf://policyengine/example/data.h5@release",
        tmp_path,
        session,
    )

    assert Path(result).read_bytes() == b"dataset"
    assert "/policyengine/example/" in session.calls[0][0]
    assert "/datasets/policyengine/example/" in session.calls[1][0]


def test_explicit_hf_authentication_failure_does_not_retry(tmp_path):
    session = _Session(_Response(status_code=403))

    with pytest.raises(DatasetMaterializationError, match="credentials"):
        _download(
            "hf://policyengine/example/data.h5@release",
            tmp_path,
            session,
        )

    assert len(session.calls) == 1


def test_explicit_hf_download_rejects_non_hf_uri(tmp_path):
    with pytest.raises(DatasetMaterializationError, match="Expected an hf://"):
        download_hf_dataset("gs://bucket/data.h5@release", data_dir=tmp_path)
