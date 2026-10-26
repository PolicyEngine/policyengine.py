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
DENSE = "microcosm_uk_2024_25_dense"
BUILD_CORE_VERSION = "3.33.3"
DEFAULTED_INPUTS = [
    "local_bus_uncapped_single_fare",
    "salary_sacrifice_returned_to_income",
]


def older_dense() -> dict:
    dense = _microcosm_uk_dense_payload()
    dense["build"]["built_with_model_package"]["version"] = "2.120.0"
    dense["build"]["built_with_core_package"] = {
        "name": "policyengine-core",
        "version": BUILD_CORE_VERSION,
    }
    dense["compatible_model_packages"] = [
        {"name": "policyengine-uk", "specifier": "==2.120.0"}
    ]
    return dense


def manifest_sha256(dense: dict) -> str:
    """The digest of the bytes ``_response`` serves for ``dense``."""
    return hashlib.sha256(json.dumps(dense).encode()).hexdigest()


def input_evidence(dense: dict | None = None) -> dict:
    """An audit whose build model lacks the two inputs the target adds."""
    dense = older_dense() if dense is None else dense
    artifact = dense["artifacts"][DENSE]
    build = dense["build"]
    return {
        "schema_version": 2,
        "regional_manifest_uri": UK_DENSE_URI,
        "regional_manifest_sha256": manifest_sha256(dense),
        "model_package": "policyengine-uk",
        "model_version": UK_MODEL_VERSION,
        "build_model_version": build["built_with_model_package"]["version"],
        "build_core_version": build["built_with_core_package"]["version"],
        "artifacts": {
            DENSE: {
                key: artifact[key] for key in ("repo_id", "path", "revision", "sha256")
            }
            | {
                "columns": ["employment_income"],
                "columns_by_period": {"2025": ["employment_income"]},
            }
        },
        "model_variables": ["employment_income", *DEFAULTED_INPUTS],
        "model_inputs": ["employment_income", *DEFAULTED_INPUTS],
        "build_model_variables": ["employment_income"],
        "build_model_inputs": ["employment_income"],
        "dropped_columns": [],
        "never_modelled_columns": [],
        "defaulted_inputs": DEFAULTED_INPUTS.copy(),
        "audited_by": "Budget regional input-surface review",
        "limitations": [VAT_LIMIT],
    }


def store_column(evidence: dict, column: str) -> None:
    measured = evidence["artifacts"][DENSE]
    measured["columns"] = sorted([*measured["columns"], column])
    measured["columns_by_period"]["2025"] = measured["columns"]


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


@pytest.mark.parametrize("model_package", ["policyengine-us", "another-model"])
@pytest.mark.parametrize("accept_mismatch", [False, True])
def test_regional_release_built_with_another_model_package_refuses(
    tmp_path, model_package, accept_mismatch
):
    dense = older_dense()
    dense["build"]["built_with_model_package"]["name"] = model_package
    if not accept_mismatch:
        dense["compatible_model_packages"] = [
            {"name": "policyengine-uk", "specifier": f"=={UK_MODEL_VERSION}"}
        ]
    bundle_path = _tmp_bundle(tmp_path)
    before = bundle_path.read_bytes()

    with pytest.raises(
        CertificationError,
        match=f"built with {model_package}, not policyengine-uk",
    ):
        if accept_mismatch:
            certify_with_evidence(bundle_path, input_evidence(dense), dense)
        else:
            _certify_uk(
                bundle_path,
                [_response(_microcosm_uk_national_payload()), _response(dense)],
                regional_manifest_uri=UK_DENSE_URI,
            )

    assert bundle_path.read_bytes() == before


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
    evidence["artifacts"][DENSE][field] = wrong
    with pytest.raises(CertificationError):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


def test_a_dropped_column_refuses_even_with_an_acceptance_reason(tmp_path):
    """The build model defines the stored column and the target does not."""
    evidence = input_evidence()
    store_column(evidence, "removed_model_variable")
    evidence["build_model_variables"].append("removed_model_variable")
    evidence["build_model_inputs"].append("removed_model_variable")
    evidence["dropped_columns"] = ["removed_model_variable"]
    with pytest.raises(CertificationError, match="[Dd]ropped.*removed_model_variable"):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


def test_a_column_neither_model_defines_is_recorded_not_refused(tmp_path):
    evidence = input_evidence()
    store_column(evidence, "constituency_code_oa")
    evidence["never_modelled_columns"] = ["constituency_code_oa"]
    bundle_path = _tmp_bundle(tmp_path)

    result = certify_with_evidence(bundle_path, evidence)

    release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
    record = release["regional_certification"]
    assert record["never_modelled_columns"] == ["constituency_code_oa"]
    assert record["dropped_columns"] == []
    assert record["evidence"] == evidence
    (warning,) = [w for w in result.warnings if "accepted mismatch" in w]
    assert "never-modelled columns (stored, defined by neither model): 1" in warning


def test_an_input_absent_under_both_models_is_not_reported(tmp_path):
    evidence = input_evidence()
    for field in (
        "model_variables",
        "model_inputs",
        "build_model_variables",
        "build_model_inputs",
    ):
        evidence[field].append("legacy_input")
    bundle_path = _tmp_bundle(tmp_path)
    certify_with_evidence(bundle_path, evidence)
    record = json.loads(bundle_path.read_text())["data_releases"]["uk"][
        "regional_certification"
    ]
    assert record["defaulted_inputs"] == DEFAULTED_INPUTS

    evidence["defaulted_inputs"] = sorted([*DEFAULTED_INPUTS, "legacy_input"])
    with pytest.raises(CertificationError, match="disagrees"):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


@pytest.mark.parametrize(
    ("field", "wrong"),
    [("build_model_version", "2.120.1"), ("build_core_version", "3.33.4")],
)
def test_evidence_against_another_build_model_refuses(tmp_path, field, wrong):
    evidence = input_evidence()
    evidence[field] = wrong
    with pytest.raises(CertificationError, match="build model"):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


@pytest.mark.parametrize(
    "unrecorded", ["built_with_model_package", "built_with_core_package"]
)
def test_a_regional_release_without_build_versions_has_no_baseline(
    tmp_path, unrecorded
):
    dense = older_dense()
    evidence = input_evidence(dense)
    del dense["build"][unrecorded]
    evidence["regional_manifest_sha256"] = manifest_sha256(dense)
    with pytest.raises(CertificationError, match="baseline"):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence, dense)


def test_version_1_evidence_refuses(tmp_path):
    evidence = input_evidence()
    evidence["schema_version"] = 1
    with pytest.raises(CertificationError, match="schema_version"):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


def test_an_h5_suffix_in_any_case_must_be_measured_as_the_audit_does():
    from policyengine.provenance.certification import accepted_regional_mismatch
    from policyengine.provenance.manifest import DataReleaseManifest

    dense = older_dense()
    dense["artifacts"][DENSE]["path"] = "microcosm_uk_2024_25_dense.H5"
    evidence = input_evidence(dense)
    manifest = DataReleaseManifest.model_validate(dense)

    def accept(evidence):
        return accepted_regional_mismatch(
            manifest,
            "policyengine-uk",
            UK_MODEL_VERSION,
            REASON,
            regional_manifest_uri=UK_DENSE_URI,
            regional_manifest_sha256=manifest_sha256(dense),
            evidence=evidence,
        )

    record, _ = accept(evidence)
    assert set(record["evidence"]["artifacts"]) == {DENSE}
    evidence["artifacts"] = {"another_file": evidence["artifacts"][DENSE]}
    with pytest.raises(CertificationError, match="every regional microdata"):
        accept(evidence)


@pytest.mark.parametrize(
    "field", ["dropped_columns", "never_modelled_columns", "defaulted_inputs"]
)
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
    record = manifest.regional_certification.model_dump(mode="json", exclude_none=True)
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


def test_missing_period_measurements_refuse(tmp_path):
    evidence = input_evidence()
    del evidence["artifacts"][DENSE]["columns_by_period"]
    with pytest.raises(CertificationError):
        certify_with_evidence(_tmp_bundle(tmp_path), evidence)


def test_budget_target_records_vat_limit_and_both_named_defaults(tmp_path, monkeypatch):
    from tests import test_certify_data_release as fixtures

    monkeypatch.setattr(fixtures, "UK_MODEL_VERSION", "2.147.2")
    dense = older_dense()
    dense["build"]["built_with_model_package"]["version"] = "2.132.6"
    dense["compatible_model_packages"][0]["specifier"] = "==2.132.6"
    audit = input_evidence(dense)
    audit["model_version"] = "2.147.2"
    audit["limitations"] = ["The dense cut was calibrated under an older model."]
    path = _tmp_bundle(tmp_path)
    certify_with_evidence(path, audit, dense)
    release = json.loads(path.read_text())["data_releases"]["uk"]
    record = release["regional_certification"]
    assert record["certified_for_model_version"] == "2.147.2"
    assert record["built_with_model_version"] == "2.132.6"
    assert VAT_LIMIT in record["limitations"]
    assert set(DEFAULTED_INPUTS) <= set(record["defaulted_inputs"])
    assert release["certification"]["compatibility_basis"] == "built_with_model_package"


def test_regional_acceptance_never_widens_national_coverage(tmp_path):
    national = _microcosm_uk_national_payload()
    national["build"]["built_with_model_package"]["version"] = "2.120.0"
    national["compatible_model_packages"][0]["specifier"] = "==2.120.0"
    with pytest.raises(CertificationError, match="new data build|compatibility claim"):
        _certify_uk(
            _tmp_bundle(tmp_path),
            [_response(national), _response(older_dense())],
            regional_manifest_uri=UK_DENSE_URI,
            regional_model_mismatch_reason=REASON,
            regional_input_surface_evidence=input_evidence(),
        )
