from pathlib import Path
from unittest.mock import patch

import pytest

import policyengine.provenance.dataset_materialization as dataset_source
from policyengine.provenance.dataset_materialization import (
    DatasetMaterializationError,
    DatasetSource,
    materialize_dataset,
)


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
        return materialize_dataset(
            "us",
            uri,
            allow_unmanaged=True,
            data_dir=tmp_path,
        )


def test_explicit_hf_download_retries_dataset_repository_after_model_404(tmp_path):
    session = _Session(_Response(status_code=404), _Response(b"dataset"))

    result = _download(
        "hf://policyengine/example/data.h5@release",
        tmp_path,
        session,
    )

    assert Path(result.path).read_bytes() == b"dataset"
    assert result.source_uri == "hf://policyengine/example/data.h5@release"
    assert result.bundle_dataset is None
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
    with pytest.raises(DatasetMaterializationError, match="Unsupported explicit"):
        materialize_dataset(
            "us",
            "gs://bucket/data.h5@release",
            allow_unmanaged=True,
            data_dir=tmp_path,
        )


def test_bundle_dataset_uses_bundle_strategy(tmp_path):
    expected = DatasetSource(
        source_uri="hf://policyengine/populace-us/populace_us_2024.h5@release",
        path=str(tmp_path / "populace_us_2024.h5"),
    )

    with patch.object(
        dataset_source,
        "_use_bundle_dataset",
        return_value=expected,
    ) as use_bundle:
        result = materialize_dataset(
            "us",
            "populace_us_2024",
            data_dir=tmp_path,
        )

    assert result is expected
    use_bundle.assert_called_once()


def test_explicit_local_path_uses_local_strategy(tmp_path):
    local_path = tmp_path / "custom.h5"
    local_path.touch()

    result = materialize_dataset(
        "us",
        str(local_path),
        allow_unmanaged=True,
        data_dir=tmp_path,
    )

    assert result == DatasetSource(
        source_uri=str(local_path),
        path=str(local_path),
    )
