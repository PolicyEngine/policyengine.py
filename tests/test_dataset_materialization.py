import hashlib
from unittest.mock import patch

import pytest

import policyengine.provenance.dataset_materialization as dataset_materialization
from policyengine.provenance.dataset_materialization import (
    DatasetMaterializationError,
    _resolve_bundle_dataset,
    _reuse_or_download_bundle_files,
)
from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    https_dataset_uri,
)


def _manifest() -> CountryReleaseManifest:
    return CountryReleaseManifest.model_validate(
        {
            "country_id": "uk",
            "policyengine_version": "5.0.4",
            "model_package": {"name": "policyengine-uk", "version": "2.90.2"},
            "data_package": {
                "name": "policyengine-uk-data",
                "version": "1.56.16",
                "repo_id": "policyengine/policyengine-uk-data-private",
                "repo_type": "model",
            },
            "default_dataset": "enhanced_frs_2024_25",
            "certified_data_artifact": {
                "dataset": "enhanced_frs_2024_25",
                "uri": "hf://policyengine/policyengine-uk-data-private/enhanced_frs_2024_25.h5@uk-release",
                "sha256": "a" * 64,
                "build_id": "policyengine-uk-data-test-build",
            },
            "datasets": {
                "enhanced_frs_2024_25": {
                    "path": "enhanced_frs_2024_25.h5",
                    "revision": "uk-release",
                    "sha256": "a" * 64,
                },
                "populace_uk_2023": {
                    "data_package_name": "populace-data",
                    "path": "populace_uk_2023.h5",
                    "repo_id": "policyengine/populace-uk-private",
                    "repo_type": "dataset",
                    "revision": "populace-release",
                    "sha256": "b" * 64,
                },
            },
        }
    )


def test_resolve_bundle_dataset_inherits_primary_package(tmp_path):
    dataset = _resolve_bundle_dataset("uk", data_dir=tmp_path, manifest=_manifest())

    assert dataset.data_package_name == "policyengine-uk-data"
    assert dataset.repo_id == "policyengine/policyengine-uk-data-private"
    assert dataset.repo_type == "model"
    assert dataset.revision == "uk-release"
    assert dataset.destination == tmp_path / "enhanced_frs_2024_25.h5"


def test_resolve_bundle_dataset_uses_cross_package_overlay(tmp_path):
    dataset = _resolve_bundle_dataset(
        "uk",
        "populace_uk_2023",
        data_dir=tmp_path,
        manifest=_manifest(),
    )

    assert dataset.data_package_name == "populace-data"
    assert dataset.repo_id == "policyengine/populace-uk-private"
    assert dataset.repo_type == "dataset"
    assert dataset.revision == "populace-release"


def test_bundled_uk_populace_dataset_uses_dataset_repository_url():
    dataset = _resolve_bundle_dataset("uk", "populace_uk_2023")

    url = https_dataset_uri(
        dataset.repo_id,
        dataset.path,
        dataset.revision,
        repo_type=dataset.repo_type,
    )

    assert dataset.data_package_name == "populace-data"
    assert dataset.repo_type == "dataset"
    assert url.startswith(
        "https://huggingface.co/datasets/policyengine/populace-uk-private/"
    )


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
        self.responses = list(responses or [_Response()])
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _manifest_with_hash(
    sha256: str,
    *,
    data_package_name: str = "policyengine-uk-data",
    repo_type: str = "model",
) -> CountryReleaseManifest:
    manifest = _manifest()
    manifest.data_package.name = data_package_name
    manifest.data_package.repo_type = repo_type
    manifest.datasets[manifest.default_dataset].sha256 = sha256
    return manifest


def _download(manifest, tmp_path, session):
    dataset = _resolve_bundle_dataset(
        "uk",
        data_dir=tmp_path,
        manifest=manifest,
    )
    with patch.object(dataset_materialization.requests, "get", side_effect=session.get):
        return _reuse_or_download_bundle_files(dataset)


def test_country_data_package_uses_model_repository_url(tmp_path):
    session = _Session(_Response(b"country-data"))
    manifest = _manifest_with_hash(_sha256(b"country-data"))

    result = _download(manifest, tmp_path, session)

    assert result.path.read_bytes() == b"country-data"
    assert result.sha256 == _sha256(b"country-data")
    assert session.calls[0][0].startswith(
        "https://huggingface.co/policyengine/policyengine-uk-data-private/resolve/"
    )


def test_populace_package_uses_dataset_repository_url(tmp_path):
    session = _Session(_Response(b"populace-data"))
    manifest = _manifest_with_hash(
        _sha256(b"populace-data"),
        data_package_name="populace-data",
        repo_type="dataset",
    )

    result = _download(manifest, tmp_path, session)

    assert result.path.read_bytes() == b"populace-data"
    assert session.calls[0][0].startswith(
        "https://huggingface.co/datasets/policyengine/"
    )


def test_downloads_and_verifies_metadata_sidecar(tmp_path):
    dataset_payload = b"long-term-data"
    metadata_payload = b'{"year": 2100}'
    manifest = _manifest_with_hash(_sha256(dataset_payload))
    manifest.datasets[manifest.default_dataset].metadata_sha256 = _sha256(
        metadata_payload
    )
    session = _Session(_Response(dataset_payload), _Response(metadata_payload))

    result = _download(manifest, tmp_path, session)

    assert result.metadata_path == (tmp_path / "enhanced_frs_2024_25.h5.metadata.json")
    assert result.metadata_path.read_bytes() == metadata_payload
    assert session.calls[1][0].endswith("/enhanced_frs_2024_25.h5.metadata.json")


def test_reuses_destination_when_hash_matches(tmp_path):
    payload = b"certified"
    manifest = _manifest_with_hash(_sha256(payload))
    destination = tmp_path / "enhanced_frs_2024_25.h5"
    destination.write_bytes(payload)
    session = _Session()

    result = _download(manifest, tmp_path, session)

    assert result.path == destination
    assert session.calls == []


def test_replaces_destination_when_hash_does_not_match(tmp_path):
    payload = b"certified"
    manifest = _manifest_with_hash(_sha256(payload))
    destination = tmp_path / "enhanced_frs_2024_25.h5"
    destination.write_bytes(b"old")

    _download(manifest, tmp_path, _Session(_Response(payload)))

    assert destination.read_bytes() == payload


def test_hash_failure_preserves_existing_destination(tmp_path):
    manifest = _manifest_with_hash(_sha256(b"expected"))
    destination = tmp_path / "enhanced_frs_2024_25.h5"
    destination.write_bytes(b"old")

    with pytest.raises(DatasetMaterializationError, match="sha256"):
        _download(manifest, tmp_path, _Session(_Response(b"wrong")))

    assert destination.read_bytes() == b"old"


def test_download_passes_hugging_face_token(monkeypatch, tmp_path):
    monkeypatch.setenv("HUGGING_FACE_TOKEN", "secret-token")
    payload = b"certified"
    session = _Session(_Response(payload))

    _download(_manifest_with_hash(_sha256(payload)), tmp_path, session)

    assert session.calls[0][1]["headers"] == {"Authorization": "Bearer secret-token"}


@pytest.mark.parametrize("status_code", [401, 403])
def test_authentication_failure_does_not_retry_repository_type(tmp_path, status_code):
    session = _Session(_Response(status_code=status_code))

    with pytest.raises(DatasetMaterializationError, match="credentials"):
        _download(
            _manifest_with_hash(_sha256(b"certified")),
            tmp_path,
            session,
        )

    assert len(session.calls) == 1
