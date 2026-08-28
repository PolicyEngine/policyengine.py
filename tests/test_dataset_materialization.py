import hashlib
from pathlib import Path

import pytest

from policyengine.provenance.dataset_materialization import (
    BundleDatasetPlan,
    DatasetMaterializationError,
    MaterializedDataset,
    _dataset_package_type,
    materialize_bundle_dataset,
    materialize_unmanaged_dataset_source,
    resolve_bundle_dataset_plan,
)
from policyengine.provenance.manifest import CountryReleaseManifest


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
                    "repo_type": "model",
                    "revision": "populace-release",
                    "sha256": "b" * 64,
                },
            },
        }
    )


def test_resolve_bundle_dataset_plan_inherits_primary_package(tmp_path):
    plan = resolve_bundle_dataset_plan("uk", data_dir=tmp_path, manifest=_manifest())

    assert plan.data_package_name == "policyengine-uk-data"
    assert plan.repo_id == "policyengine/policyengine-uk-data-private"
    assert plan.repo_type == "model"
    assert plan.revision == "uk-release"
    assert plan.destination == tmp_path / "enhanced_frs_2024_25.h5"
    assert plan.build_id == "policyengine-uk-data-test-build"


def test_resolve_bundle_dataset_plan_uses_cross_package_overlay(tmp_path):
    plan = resolve_bundle_dataset_plan(
        "uk",
        "populace_uk_2023",
        data_dir=tmp_path,
        manifest=_manifest(),
    )

    assert plan.data_package_name == "populace-data"
    assert plan.repo_id == "policyengine/populace-uk-private"
    assert plan.repo_type == "model"
    assert plan.revision == "populace-release"
    assert plan.build_id is None


def test_bundle_dataset_models_round_trip_json():
    plan = resolve_bundle_dataset_plan("uk", manifest=_manifest())
    assert BundleDatasetPlan.model_validate_json(plan.model_dump_json()) == plan

    result = MaterializedDataset(
        **plan.model_dump(exclude={"path", "destination"}),
        actual_sha256=plan.expected_sha256,
        path=Path("data/enhanced_frs_2024_25.h5"),
        cache_hit=True,
    )
    assert MaterializedDataset.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    ("package_name", "expected_type"),
    [
        ("policyengine-us-data", "country"),
        ("policyengine-uk-data", "country"),
        ("populace-data", "populace"),
    ],
)
def test_dataset_package_type(package_name, expected_type):
    assert _dataset_package_type(package_name) == expected_type


def test_unknown_data_package_is_rejected():
    with pytest.raises(DatasetMaterializationError, match="Unsupported bundle"):
        _dataset_package_type("unknown-data")


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


def test_materialize_country_data_package_uses_model_repo_url(tmp_path):
    session = _Session(_Response(b"country-data"))
    manifest = _manifest_with_hash(_sha256(b"country-data"))

    result = materialize_bundle_dataset(
        "uk", data_dir=tmp_path, manifest=manifest, session=session
    )

    assert result.path.read_bytes() == b"country-data"
    assert result.cache_hit is False
    assert session.calls[0][0].startswith(
        "https://huggingface.co/policyengine/policyengine-uk-data-private/resolve/"
    )


def test_materialize_populace_package_uses_dataset_repo_url(tmp_path):
    session = _Session(_Response(b"populace-data"))
    manifest = _manifest_with_hash(
        _sha256(b"populace-data"),
        data_package_name="populace-data",
        repo_type="dataset",
    )

    result = materialize_bundle_dataset(
        "uk", data_dir=tmp_path, manifest=manifest, session=session
    )

    assert result.path.read_bytes() == b"populace-data"
    assert session.calls[0][0].startswith(
        "https://huggingface.co/datasets/policyengine/"
    )


def test_materialize_downloads_and_verifies_metadata_sidecar(tmp_path):
    dataset_payload = b"long-term-data"
    metadata_payload = b'{"year": 2100}'
    manifest = _manifest_with_hash(_sha256(dataset_payload))
    reference = manifest.datasets[manifest.default_dataset]
    reference.metadata_sha256 = _sha256(metadata_payload)
    session = _Session(_Response(dataset_payload), _Response(metadata_payload))

    result = materialize_bundle_dataset(
        "uk", data_dir=tmp_path, manifest=manifest, session=session
    )

    assert result.metadata_path == (tmp_path / "enhanced_frs_2024_25.h5.metadata.json")
    assert result.metadata_path.read_bytes() == metadata_payload
    assert result.metadata_actual_sha256 == reference.metadata_sha256
    assert session.calls[1][0].endswith("/enhanced_frs_2024_25.h5.metadata.json")


def test_materialize_reuses_only_hash_verified_cache(tmp_path):
    payload = b"certified"
    manifest = _manifest_with_hash(_sha256(payload))
    destination = tmp_path / "enhanced_frs_2024_25.h5"
    destination.write_bytes(payload)
    session = _Session()

    result = materialize_bundle_dataset(
        "uk", data_dir=tmp_path, manifest=manifest, session=session
    )

    assert result.cache_hit is True
    assert session.calls == []


def test_materialize_reuses_hash_verified_local_mirror(monkeypatch, tmp_path):
    payload = b"certified-local-mirror"
    manifest = _manifest_with_hash(_sha256(payload))
    mirror = tmp_path / "mirror" / "enhanced_frs_2024_25.h5"
    mirror.parent.mkdir()
    mirror.write_bytes(payload)
    monkeypatch.setattr(
        "policyengine.provenance.dataset_materialization.resolve_local_managed_dataset_source",
        lambda *args, **kwargs: str(mirror),
    )
    session = _Session()

    result = materialize_bundle_dataset(
        "uk", data_dir=tmp_path, manifest=manifest, session=session
    )

    assert result.path == mirror
    assert result.cache_hit is True
    assert session.calls == []


def test_materialize_ignores_mismatched_local_mirror(monkeypatch, tmp_path):
    payload = b"certified-download"
    manifest = _manifest_with_hash(_sha256(payload))
    mirror = tmp_path / "mirror" / "enhanced_frs_2024_25.h5"
    mirror.parent.mkdir()
    mirror.write_bytes(b"wrong")
    monkeypatch.setattr(
        "policyengine.provenance.dataset_materialization.resolve_local_managed_dataset_source",
        lambda *args, **kwargs: str(mirror),
    )
    session = _Session(_Response(payload))

    result = materialize_bundle_dataset(
        "uk", data_dir=tmp_path, manifest=manifest, session=session
    )

    assert result.path == tmp_path / "enhanced_frs_2024_25.h5"
    assert result.path.read_bytes() == payload
    assert mirror.read_bytes() == b"wrong"


def test_materialize_replaces_and_backs_up_mismatched_cache(tmp_path):
    payload = b"certified"
    manifest = _manifest_with_hash(_sha256(payload))
    destination = tmp_path / "enhanced_frs_2024_25.h5"
    destination.write_bytes(b"old")

    materialize_bundle_dataset(
        "uk",
        data_dir=tmp_path,
        manifest=manifest,
        session=_Session(_Response(payload)),
    )

    assert destination.read_bytes() == payload
    backups = list(
        (tmp_path / ".policyengine-bundle-backups").glob("*/enhanced_frs_2024_25.h5")
    )
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"old"


def test_hash_failure_does_not_replace_existing_cache(tmp_path):
    manifest = _manifest_with_hash(_sha256(b"expected"))
    destination = tmp_path / "enhanced_frs_2024_25.h5"
    destination.write_bytes(b"old")

    with pytest.raises(DatasetMaterializationError, match="sha256"):
        materialize_bundle_dataset(
            "uk",
            data_dir=tmp_path,
            manifest=manifest,
            session=_Session(_Response(b"wrong")),
        )

    assert destination.read_bytes() == b"old"
    assert not (tmp_path / ".policyengine-bundle-backups").exists()


def test_materialize_passes_hugging_face_token(monkeypatch, tmp_path):
    monkeypatch.setenv("HUGGING_FACE_TOKEN", "secret-token")
    payload = b"certified"
    session = _Session(_Response(payload))

    materialize_bundle_dataset(
        "uk",
        data_dir=tmp_path,
        manifest=_manifest_with_hash(_sha256(payload)),
        session=session,
    )

    assert session.calls[0][1]["headers"] == {"Authorization": "Bearer secret-token"}


@pytest.mark.parametrize("status_code", [401, 403])
def test_managed_auth_failure_does_not_retry_repo_type(tmp_path, status_code):
    session = _Session(_Response(status_code=status_code))

    with pytest.raises(DatasetMaterializationError, match="credentials"):
        materialize_bundle_dataset(
            "uk",
            data_dir=tmp_path,
            manifest=_manifest_with_hash(_sha256(b"certified")),
            session=session,
        )

    assert len(session.calls) == 1


def test_unmanaged_hf_retries_dataset_repo_only_after_not_found(tmp_path):
    session = _Session(_Response(status_code=404), _Response(b"dataset"))

    result = materialize_unmanaged_dataset_source(
        "hf://policyengine/example/data.h5@release",
        data_dir=tmp_path,
        session=session,
    )

    assert Path(result).read_bytes() == b"dataset"
    assert "/policyengine/example/" in session.calls[0][0]
    assert "/datasets/policyengine/example/" in session.calls[1][0]


def test_unmanaged_auth_failure_does_not_retry(tmp_path):
    session = _Session(_Response(status_code=403))

    with pytest.raises(DatasetMaterializationError, match="credentials"):
        materialize_unmanaged_dataset_source(
            "hf://policyengine/example/data.h5@release",
            data_dir=tmp_path,
            session=session,
        )

    assert len(session.calls) == 1


def test_unmanaged_local_path_is_preserved():
    assert materialize_unmanaged_dataset_source("/tmp/custom.h5") == ("/tmp/custom.h5")


def test_unmanaged_gcs_source_is_rejected():
    with pytest.raises(DatasetMaterializationError, match="no longer supported"):
        materialize_unmanaged_dataset_source("gs://bucket/data.h5@release")
