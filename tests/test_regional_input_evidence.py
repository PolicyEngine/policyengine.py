"""A regional model exception requires an audit of the exact dense bytes."""

import copy
import hashlib
import json

import pytest

from policyengine.provenance.certification import CertificationError
from policyengine.provenance.manifest import CountryReleaseManifest
from tests.test_certify_data_release import (
    UK_DENSE_URI,
    UK_MODEL_VERSION,
    _certify_uk,
    _microcosm_uk_dense_payload,
    _microcosm_uk_national_payload,
    _response,
    _tmp_bundle,
)

REASON = "Budget accepts the audited dense model gap; area runs remain uncertified"
VAT_LIMIT = (
    "the dense cut's VAT predates the policyengine-uk VAT factor fix "
    "(#2187, 2.135.7); the dashboard holds a VAT limit"
)
DEFAULTED_INPUTS = [
    "local_bus_uncapped_single_fare",
    "salary_sacrifice_returned_to_income",
]


def older_dense() -> dict:
    dense = _microcosm_uk_dense_payload()
    dense["build"]["built_with_model_package"]["version"] = "2.120.0"
    dense["compatible_model_packages"] = [
        {"name": "policyengine-uk", "specifier": "==2.120.0"}
    ]
    return dense


def input_evidence(dense: dict | None = None) -> dict:
    dense = older_dense() if dense is None else dense
    name = "microcosm_uk_2024_25_dense"
    artifact = dense["artifacts"][name]
    return {
        "schema_version": 1,
        "regional_manifest_uri": UK_DENSE_URI,
        "regional_manifest_sha256": hashlib.sha256(
            json.dumps(dense).encode()
        ).hexdigest(),
        "model_package": "policyengine-uk",
        "model_version": UK_MODEL_VERSION,
        "artifacts": {
            name: {
                key: artifact[key] for key in ("repo_id", "path", "revision", "sha256")
            }
            | {"columns": ["employment_income"]}
        },
        "model_variables": ["employment_income", *DEFAULTED_INPUTS],
        "model_inputs": ["employment_income", *DEFAULTED_INPUTS],
        "dropped_columns": [],
        "defaulted_inputs": DEFAULTED_INPUTS.copy(),
        "audited_by": "Budget regional input-surface review",
        "limitations": [VAT_LIMIT],
    }


def certify_with_evidence(bundle_path, evidence: dict, dense: dict | None = None):
    dense = older_dense() if dense is None else dense
    return _certify_uk(
        bundle_path,
        [_response(_microcosm_uk_national_payload()), _response(dense)],
        regional_manifest_uri=UK_DENSE_URI,
        regional_model_mismatch_reason=REASON,
        regional_input_surface_evidence=evidence,
    )


def test_accepted_mismatch_without_audited_evidence_refuses(tmp_path):
    with pytest.raises(CertificationError, match="[Ee]vidence|[Aa]udit"):
        _certify_uk(
            _tmp_bundle(tmp_path),
            [
                _response(_microcosm_uk_national_payload()),
                _response(older_dense()),
            ],
            regional_manifest_uri=UK_DENSE_URI,
            regional_model_mismatch_reason=REASON,
        )


@pytest.mark.parametrize(
    ("field", "wrong"),
    [
        ("regional_manifest_uri", UK_DENSE_URI.replace("dense", "other-dense")),
        ("regional_manifest_sha256", "0" * 64),
        ("model_package", "policyengine-us"),
        ("model_version", "2.147.1"),
    ],
)
def test_evidence_for_another_cut_bytes_or_model_refuses(tmp_path, field, wrong):
    evidence = input_evidence()
    evidence[field] = wrong
    with pytest.raises(CertificationError):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


@pytest.mark.parametrize(
    ("field", "wrong"),
    [
        ("repo_id", "policyengine/another-dense"),
        ("path", "different_dense.h5"),
        ("revision", "different-cut"),
        ("sha256", "0" * 64),
    ],
)
def test_evidence_for_other_artifact_bytes_or_identity_refuses(tmp_path, field, wrong):
    evidence = input_evidence()
    evidence["artifacts"]["microcosm_uk_2024_25_dense"][field] = wrong
    with pytest.raises(CertificationError):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


def test_a_dropped_column_refuses_even_with_an_acceptance_reason(tmp_path):
    evidence = input_evidence()
    evidence["artifacts"]["microcosm_uk_2024_25_dense"]["columns"].append(
        "removed_model_variable"
    )
    evidence["dropped_columns"] = ["removed_model_variable"]
    with pytest.raises(CertificationError, match="[Dd]ropped|removed_model_variable"):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


@pytest.mark.parametrize("field", ["dropped_columns", "defaulted_inputs"])
def test_the_declared_comparison_must_match_the_measured_surfaces(tmp_path, field):
    evidence = input_evidence()
    evidence[field] = ["invented_variable"]
    with pytest.raises(CertificationError):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


def test_a_missing_artifact_measurement_refuses(tmp_path):
    evidence = input_evidence()
    evidence["artifacts"] = {}
    with pytest.raises(CertificationError):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


def test_every_default_and_limitation_survives_validation_and_roundtrip(tmp_path):
    bundle_path = _tmp_bundle(tmp_path)
    evidence = input_evidence()
    certify_with_evidence(bundle_path, evidence)

    release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
    manifest = CountryReleaseManifest.model_validate(release)
    assert manifest.regional_certification is not None
    record = manifest.regional_certification.model_dump(mode="json")
    assert record["defaulted_inputs"] == DEFAULTED_INPUTS
    assert record["dropped_columns"] == []
    assert record["limitations"] == [VAT_LIMIT]
    assert record["evidence"] == evidence
    assert record["area_receipts"] == "uncertified"
    assert record["accepted_reason"] == REASON
    assert (
        release["regional_source_manifest_sha256"]
        == evidence["regional_manifest_sha256"]
    )
    rebuilt = CountryReleaseManifest.model_validate_json(manifest.model_dump_json())
    assert rebuilt.regional_certification == manifest.regional_certification
    assert release["certification"]["compatibility_basis"] == "built_with_model_package"


def test_evidence_digest_binds_original_manifest_bytes(tmp_path):
    dense = older_dense()
    response = _response(dense)
    response.content = json.dumps(dense, indent=2).encode()
    evidence = input_evidence(dense)
    with pytest.raises(CertificationError):
        _certify_uk(
            _tmp_bundle(tmp_path),
            [_response(_microcosm_uk_national_payload()), response],
            regional_manifest_uri=UK_DENSE_URI,
            regional_model_mismatch_reason=REASON,
            regional_input_surface_evidence=evidence,
        )

    evidence["regional_manifest_sha256"] = hashlib.sha256(response.content).hexdigest()
    bundle_path = _tmp_bundle(tmp_path)
    _certify_uk(
        bundle_path,
        [_response(_microcosm_uk_national_payload()), response],
        regional_manifest_uri=UK_DENSE_URI,
        regional_model_mismatch_reason=REASON,
        regional_input_surface_evidence=evidence,
    )
    release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
    assert (
        release["regional_source_manifest_sha256"]
        == evidence["regional_manifest_sha256"]
    )


def test_drop_regional_release_removes_acceptance_and_preserves_national_cert(tmp_path):
    bundle_path = _tmp_bundle(tmp_path)
    certify_with_evidence(bundle_path, input_evidence())
    before = json.loads(bundle_path.read_text())["data_releases"]["uk"]
    _certify_uk(
        bundle_path,
        [_response(_microcosm_uk_national_payload())],
        drop_regional_release=True,
    )
    after = json.loads(bundle_path.read_text())["data_releases"]["uk"]
    assert after["certification"] == before["certification"]
    assert "regional_certification" not in after
    assert "regional_source_manifest_sha256" not in after
    assert "regional_source_manifest_uri" not in after
    assert "regional_release_kind" not in after
    assert "microcosm_uk_2024_25_dense" not in after["datasets"]
    assert set(after["region_datasets"]) == {"national"}


def test_limitations_and_evidence_are_in_hashed_bundle_material(tmp_path):
    from policyengine.provenance.canonical import canonical_sha256

    bundle_path = _tmp_bundle(tmp_path)
    certify_with_evidence(bundle_path, input_evidence())
    before = json.loads(bundle_path.read_text())
    after = copy.deepcopy(before)
    after["data_releases"]["uk"]["regional_certification"]["limitations"].append(
        "An additional reviewed regional limitation"
    )

    def digest(bundle):
        manifest = CountryReleaseManifest.model_validate(bundle["data_releases"]["uk"])
        return canonical_sha256(manifest.model_dump(mode="json"))

    assert digest(before) != digest(after)
