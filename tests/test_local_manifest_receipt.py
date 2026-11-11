"""Local-manifest runtime evidence preserves the bundle certificate's identity."""

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from policyengine.provenance import certification, manifest, receipt

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    REPO_ROOT / "src/policyengine/data/schemas/execution_receipt.v1.schema.json"
)
LOCAL_BASIS = "exact_build_model_version_local_manifest"


@pytest.fixture
def packaged_receipt(monkeypatch, tmp_path):
    bundle = json.loads(
        (REPO_ROOT / "src/policyengine/data/bundle/manifest.json").read_text()
    )
    record = bundle["data_releases"]["uk"]
    dataset_path = tmp_path / "dataset.h5"
    dataset_path.write_bytes(b"synthetic certified dataset")
    digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    record["datasets"][record["default_dataset"]]["sha256"] = digest
    record["certified_data_artifact"]["sha256"] = digest
    bundle_path = tmp_path / "manifest.json"
    bundle_path.write_text(json.dumps(bundle))
    versions = {
        "policyengine": bundle["policyengine_version"],
        "policyengine-uk": record["certification"]["certified_for_model_version"],
        "policyengine-core": bundle["packages"]["policyengine-core"]["version"],
    }
    monkeypatch.setattr(
        certification, "default_bundle_source_path", lambda: bundle_path
    )
    monkeypatch.setattr(
        receipt,
        "installed_package_identity",
        lambda name, **kwargs: receipt.PackageIdentity(
            name=name, version=versions[name]
        ),
    )
    monkeypatch.setattr(receipt, "loaded_versions", lambda: {})
    monkeypatch.setattr(
        receipt, "_refuse_package_changed_after_process_start", lambda name: None
    )
    monkeypatch.setattr(receipt, "_projected_years", lambda *args: (2025, 2026))
    monkeypatch.delenv("POLICYENGINE_UK_DATA_MANIFEST_FILE", raising=False)

    def build(*, caller_supplied=False):
        current_law = receipt.ReformIdentity(kind="current_law")
        return receipt.build_execution_receipt(
            country_id="uk",
            dataset_path=dataset_path,
            years=[2026],
            reform=current_law,
            baseline=current_law,
            bundle=bundle if caller_supplied else None,
        )

    return build, bundle


def test_packaged_receipt_records_local_basis_without_changing_certificate(
    packaged_receipt, monkeypatch
):
    build, bundle = packaged_receipt
    calls = []

    def certify(country_id, model_version, **kwargs):
        calls.append((country_id, model_version, kwargs))
        return manifest.DataCertification(
            compatibility_basis=LOCAL_BASIS,
            certified_for_model_version=model_version,
        )

    monkeypatch.setenv("POLICYENGINE_UK_DATA_MANIFEST_FILE", "/verified/manifest.json")
    monkeypatch.setattr(manifest, "certify_data_release_compatibility", certify)
    result = build()
    assert result.runtime.data_certification_basis == LOCAL_BASIS
    assert calls == [
        (
            "uk",
            result.model.version,
            {
                "runtime_core_version": result.core.version,
                "runtime_data_build_fingerprint": result.data.build_fingerprint,
            },
        )
    ]
    assert (
        result.certificate.compatibility_basis
        == (bundle["data_releases"]["uk"]["certification"]["compatibility_basis"])
    )
    assert receipt.verify_certificate(result, bundle) == []
    payload = json.loads(result.model_dump_json())
    jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text())).validate(
        payload
    )
    assert (
        receipt.ExecutionReceipt.model_validate_json(result.model_dump_json()) == result
    )


def test_local_manifest_errors_stop_receipt_building(packaged_receipt, monkeypatch):
    build, _ = packaged_receipt
    monkeypatch.setenv("POLICYENGINE_UK_DATA_MANIFEST_FILE", "/missing/manifest.json")

    def refuse(*args, **kwargs):
        raise ValueError("local manifest: expected SHA-256 aaa; actual SHA-256 bbb")

    monkeypatch.setattr(manifest, "certify_data_release_compatibility", refuse)
    with pytest.raises(ValueError, match="expected SHA-256 aaa; actual SHA-256 bbb"):
        build()


@pytest.mark.parametrize("caller_supplied", [False, True])
def test_unset_setting_keeps_receipt_building_offline(
    packaged_receipt, monkeypatch, caller_supplied
):
    build, _ = packaged_receipt

    def unexpected(*args, **kwargs):
        raise AssertionError(
            "unset local manifest must not cause certification or fetches"
        )

    monkeypatch.setattr(manifest, "certify_data_release_compatibility", unexpected)
    monkeypatch.setattr(manifest.requests, "get", unexpected)
    result = build(caller_supplied=caller_supplied)
    assert result.runtime.data_certification_basis is None
    assert (
        "data_certification_basis"
        not in json.loads(result.model_dump_json())["runtime"]
    )


def test_local_runtime_context_does_not_change_certificate_or_result_digests(
    packaged_receipt, monkeypatch
):
    build, bundle = packaged_receipt
    original = build()
    monkeypatch.setenv("POLICYENGINE_UK_DATA_MANIFEST_FILE", "/verified/manifest.json")
    monkeypatch.setattr(
        manifest,
        "certify_data_release_compatibility",
        lambda *args, **kwargs: manifest.DataCertification(
            compatibility_basis=LOCAL_BASIS,
            certified_for_model_version=original.model.version,
        ),
    )
    local = build()
    assert local.runtime.data_certification_basis == LOCAL_BASIS
    assert local.certificate == original.certificate
    assert local.execution_identity_sha256 == original.execution_identity_sha256
    assert local.receipt_sha256 == original.receipt_sha256
    assert receipt.verify_certificate(local, bundle) == []


def test_caller_supplied_bundle_does_not_claim_packaged_manifest_provenance(
    packaged_receipt, monkeypatch
):
    build, _ = packaged_receipt
    monkeypatch.setenv("POLICYENGINE_UK_DATA_MANIFEST_FILE", "/verified/manifest.json")

    def unexpected(*args, **kwargs):
        raise AssertionError("a caller's bundle is not the local file's trust anchor")

    monkeypatch.setattr(manifest, "certify_data_release_compatibility", unexpected)
    result = build(caller_supplied=True)
    assert result.certificate.certificate_source == "caller_supplied"
    assert result.runtime.data_certification_basis is None
