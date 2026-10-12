"""Certification on an automated qualification of the exact pair.

Invariants:

- ``qualified_exact_pair`` is used only when neither the build-time model
  nor a publisher claim covers the model; it is exact (one model version,
  one core version, one data build) and names the qualified pair;
- the core must be the build core, publisher-claimed, or qualified;
- at runtime a qualified certificate is honoured only for exactly its model
  version and data build, online and offline;
- a bundle certificate on that basis needs a promotable ledger receipt for
  exactly what it certifies (``verify_certification_evidence``).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from policyengine.provenance.certification import (
    BASIS_QUALIFIED_PAIR,
    CertificationError,
    build_country_manifest_payload,
    validate_release_manifest,
)
from policyengine.provenance.manifest import (
    DataCertification,
    DataReleaseManifest,
    DataReleaseManifestUnavailableError,
    certify_data_release_compatibility,
    get_data_release_manifest,
)
from policyengine.provenance.qualification_ledger import (
    latest_receipts,
    pending_attempts,
    verify_certification_evidence,
    write_json,
)
from tests.qualification_fixtures import gates, make_pair, make_receipt

PAIR_ID = "a" * 64


def _uk_manifest(
    model_claims=("==2.122.2",), core_claims=("==3.32.13",)
) -> DataReleaseManifest:
    return DataReleaseManifest.model_validate(
        {
            "schema_version": 1,
            "data_package": {"name": "policyengine-uk-data", "version": "1.58.0"},
            "compatible_model_packages": [
                {"name": "policyengine-uk", "specifier": spec} for spec in model_claims
            ],
            "compatible_core_packages": [
                {"name": "policyengine-core", "specifier": spec} for spec in core_claims
            ],
            "default_datasets": {"national": "enhanced_frs_2024_25"},
            "build": {
                "build_id": "policyengine-uk-data-1.58.0",
                "built_with_core_package": {
                    "name": "policyengine-core",
                    "version": "3.32.13",
                },
                "built_with_model_package": {
                    "name": "policyengine-uk",
                    "version": "2.122.2",
                    "data_build_fingerprint": "sha256:build",
                },
            },
            "artifacts": {
                "enhanced_frs_2024_25": {
                    "kind": "microdata",
                    "path": "enhanced_frs_2024_25.h5",
                    "repo_id": "policyengine/policyengine-uk-data-private",
                    "revision": "1.58.0",
                    "sha256": "d" * 64,
                    "size_bytes": 10,
                }
            },
        }
    )


class TestValidateWithQualification:
    def test_uncovered_model_is_admitted_only_with_a_pair_id(self):
        with pytest.raises(CertificationError, match="qualification"):
            validate_release_manifest(_uk_manifest(), "policyengine-uk", "2.126.8")
        basis, warnings = validate_release_manifest(
            _uk_manifest(core_claims=("==3.33.0",)),
            "policyengine-uk",
            "2.126.8",
            core_version="3.33.0",
            qualified_pair_id=PAIR_ID,
        )
        assert basis == BASIS_QUALIFIED_PAIR
        assert any("exactly policyengine-uk==2.126.8" in item for item in warnings)

    def test_stronger_bases_win_over_qualification(self):
        basis, _ = validate_release_manifest(
            _uk_manifest(), "policyengine-uk", "2.122.2", qualified_pair_id=PAIR_ID
        )
        assert basis == "built_with_model_package"
        basis, _ = validate_release_manifest(
            _uk_manifest(model_claims=("==2.122.2", "==2.126.8")),
            "policyengine-uk",
            "2.126.8",
            qualified_pair_id=PAIR_ID,
        )
        assert basis == "legacy_compatible_model_package"

    @pytest.mark.parametrize(
        ("model_version", "model_claims"),
        [("2.122.2", ("==2.122.2",)), ("2.126.8", ("==2.122.2", "==2.126.8"))],
        ids=["build-time model", "publisher-claimed model"],
    )
    def test_an_unclaimed_core_makes_the_basis_the_exact_pair(
        self, model_version, model_claims
    ):
        """Interrupted review of #574: with the model on a stronger basis, a
        core the publisher never claimed was certified on that basis, and the
        certificate named no pair, so no evidence was ever required."""

        basis, warnings = validate_release_manifest(
            _uk_manifest(model_claims=model_claims),
            "policyengine-uk",
            model_version,
            core_version="9.99.0",
            qualified_pair_id=PAIR_ID,
        )
        assert basis == BASIS_QUALIFIED_PAIR
        assert any("policyengine-core==9.99.0" in item for item in warnings)
        with pytest.raises(CertificationError, match="policyengine-core 9.99.0"):
            validate_release_manifest(
                _uk_manifest(model_claims=model_claims),
                "policyengine-uk",
                model_version,
                core_version="9.99.0",
            )

    def test_qualified_pair_needs_its_core_version(self):
        with pytest.raises(CertificationError, match="core"):
            validate_release_manifest(
                _uk_manifest(), "policyengine-uk", "2.126.8", qualified_pair_id=PAIR_ID
            )

    def test_core_outside_claims_is_refused_unless_qualified(self):
        with pytest.raises(CertificationError, match="policyengine-core 3.34.0"):
            validate_release_manifest(
                _uk_manifest(model_claims=("==2.126.8",)),
                "policyengine-uk",
                "2.126.8",
                core_version="3.34.0",
            )
        basis, warnings = validate_release_manifest(
            _uk_manifest(),
            "policyengine-uk",
            "2.126.8",
            core_version="3.34.0",
            qualified_pair_id=PAIR_ID,
        )
        assert basis == BASIS_QUALIFIED_PAIR
        assert any("outside the publisher's core claims" in item for item in warnings)

    def test_build_core_and_claimed_core_pass(self):
        for core in ("3.32.13",):
            validate_release_manifest(
                _uk_manifest(), "policyengine-uk", "2.122.2", core_version=core
            )

    def test_payload_names_the_pair_and_core(self):
        manifest = _uk_manifest()
        payload = build_country_manifest_payload(
            country="uk",
            manifest=manifest,
            uri_parts={
                "repo_type": "model",
                "repo_id": "policyengine/policyengine-uk-data-private",
                "revision": "f" * 40,
                "path": "releases/1.58.0/release_manifest.json",
            },
            policyengine_version="6.2.7",
            model_package="policyengine-uk",
            model_version="2.126.8",
            model_wheel={
                "sha256": "a" * 64,
                "url": "https://files.pythonhosted.org/x.whl",
            },
            compatibility_basis=BASIS_QUALIFIED_PAIR,
            core_version="3.33.0",
            qualified_pair_id=PAIR_ID,
        )
        certification = payload["certification"]
        assert certification["compatibility_basis"] == BASIS_QUALIFIED_PAIR
        assert certification["certified_for_core_version"] == "3.33.0"
        assert certification["qualification_pair_id"] == PAIR_ID
        assert certification["qualification_ledger_url"].endswith(f"/uk/{PAIR_ID}")


def _response(payload):
    response = MagicMock()
    response.status_code = 200
    response.text = json.dumps(payload)
    response.content = response.text.encode()
    response.raise_for_status.return_value = None
    return response


def _qualified(model="2.126.8", build_id="policyengine-uk-data-1.58.0"):
    return DataCertification(
        compatibility_basis="qualified_exact_pair",
        certified_for_model_version=model,
        certified_for_core_version="3.33.0",
        data_build_id=build_id,
        data_build_fingerprint="sha256:build",
        qualification_pair_id=PAIR_ID,
    )


class TestRuntimeAcceptance:
    def setup_method(self):
        get_data_release_manifest.cache_clear()

    def _certify(
        self, bundled, runtime_model, remote=None, fingerprint=None, core="3.33.0"
    ):
        manifest = MagicMock(certification=bundled)
        manifest.model_package.name = "policyengine-uk"
        manifest.data_package = MagicMock(
            release_manifest_revision=None, repo_id="r", version="1.58.0"
        )
        patches = [
            patch(
                "policyengine.provenance.manifest.get_release_manifest",
                return_value=manifest,
            )
        ]
        if remote is None:
            patches.append(
                patch(
                    "policyengine.provenance.manifest.get_data_release_manifest",
                    side_effect=DataReleaseManifestUnavailableError("private"),
                )
            )
        else:
            patches.append(
                patch(
                    "policyengine.provenance.manifest.get_data_release_manifest",
                    return_value=remote,
                )
            )
        with patches[0], patches[1]:
            return certify_data_release_compatibility(
                "uk",
                runtime_model_version=runtime_model,
                runtime_data_build_fingerprint=fingerprint,
                runtime_core_version=core,
            )

    def test_online_exact_model_and_build_is_honoured(self):
        certification = self._certify(_qualified(), "2.126.8", remote=_uk_manifest())
        assert certification.compatibility_basis == "qualified_exact_pair"

    def test_online_other_model_version_is_refused(self):
        with pytest.raises(ValueError, match="not certified"):
            self._certify(_qualified(), "2.126.9", remote=_uk_manifest())

    def test_online_other_data_build_is_refused(self):
        with pytest.raises(ValueError, match="not certified"):
            self._certify(
                _qualified(build_id="policyengine-uk-data-1.59.0"),
                "2.126.8",
                remote=_uk_manifest(),
            )

    def test_online_other_core_is_refused(self):
        """Interrupted review of #574: an exact pair was honoured whatever core ran."""

        with pytest.raises(ValueError, match="not certified"):
            self._certify(_qualified(), "2.126.8", remote=_uk_manifest(), core="3.34.0")

    def test_offline_other_core_is_not_certified(self):
        certification = self._certify(_qualified(), "2.126.8", core="3.34.0")
        assert certification.compatibility_basis == (
            "unverified_data_release_manifest_unavailable"
        )

    def test_the_installed_core_is_read_when_none_is_given(self):
        with patch("importlib.metadata.version", return_value="3.34.0") as installed:
            with pytest.raises(ValueError, match="not certified"):
                self._certify(_qualified(), "2.126.8", remote=_uk_manifest(), core=None)
        installed.assert_called_with("policyengine-core")

    def test_other_bases_make_no_runtime_core_claim(self):
        legacy = DataCertification(
            compatibility_basis="legacy_compatible_model_package",
            certified_for_model_version="2.126.8",
            certified_for_core_version="3.33.0",
            data_build_id="policyengine-uk-data-1.58.0",
        )
        assert (
            self._certify(legacy, "2.126.8", core="3.34.0").compatibility_basis
            == "legacy_compatible_model_package"
        )

    def test_offline_fingerprint_difference_is_expected(self):
        certification = self._certify(
            _qualified(), "2.126.8", fingerprint="sha256:runtime"
        )
        assert certification.compatibility_basis == "qualified_exact_pair"


# --- Ledger evidence ---------------------------------------------------------


def _record_for(receipt):
    pair = receipt.pair
    return {
        "certification": {
            "compatibility_basis": "qualified_exact_pair",
            "qualification_pair_id": pair.pair_id,
            "certified_for_model_version": pair.model.version,
            "certified_for_core_version": pair.core.version,
            "data_build_id": pair.data.build_id,
        },
        "model_package": {
            "version": pair.model.version,
            "sha256": pair.model.wheel_sha256,
        },
        "data_package": {
            "version": pair.data.release_version,
            "release_manifest_revision": pair.data.release_manifest_revision,
        },
        "default_dataset": pair.data.dataset,
        "certified_data_artifact": {
            "dataset": pair.data.dataset,
            "sha256": pair.data.dataset_sha256,
        },
        "datasets": {
            pair.data.dataset: {
                "repo_id": pair.data.repo_id,
                "path": pair.data.dataset_path,
                "revision": pair.data.dataset_revision,
                "sha256": pair.data.dataset_sha256,
            }
        },
    }


def test_other_bases_need_no_ledger_evidence():
    assert (
        verify_certification_evidence(
            {
                "certification": {
                    "compatibility_basis": "legacy_compatible_model_package"
                }
            },
            None,
        )
        == []
    )


def test_matching_promotable_receipt_is_sufficient():
    receipt = make_receipt()
    assert verify_certification_evidence(_record_for(receipt), receipt) == []


REFERENCE_FIELDS = ["repo_id", "path", "revision", "sha256"]


@pytest.mark.parametrize("field", REFERENCE_FIELDS)
def test_the_dataset_reference_the_runtime_resolves_is_evidence_too(field):
    """Interrupted review of #574: a record pointing its default dataset at
    another repository, path, revision or file verified against the receipt."""

    receipt = make_receipt()
    record = _record_for(receipt)
    record["datasets"][receipt.pair.data.dataset][field] = "f" * 64
    problems = verify_certification_evidence(record, receipt)
    assert any("dataset reference" in problem for problem in problems)
    del record["datasets"][receipt.pair.data.dataset]
    assert verify_certification_evidence(record, receipt)


def test_a_record_without_the_model_wheel_hash_is_refused():
    receipt = make_receipt()
    record = _record_for(receipt)
    del record["model_package"]["sha256"]
    problems = verify_certification_evidence(record, receipt)
    assert any("model wheel sha256" in problem for problem in problems)


def test_missing_or_unpromotable_receipt_is_refused():
    receipt = make_receipt()
    record = _record_for(receipt)
    assert verify_certification_evidence(record, None)
    pending = make_receipt(gate_results=gates(replay="needs_review"))
    assert verify_certification_evidence(_record_for(pending), pending)


FIELDS = [
    ("certification", "certified_for_model_version"),
    ("certification", "certified_for_core_version"),
    ("certification", "data_build_id"),
    ("model_package", "version"),
    ("model_package", "sha256"),
    ("data_package", "version"),
    ("data_package", "release_manifest_revision"),
    ("certified_data_artifact", "sha256"),
    ("certified_data_artifact", "dataset"),
]


@settings(max_examples=60, deadline=None)
@given(field=st.sampled_from(FIELDS), value=st.text(min_size=1, max_size=8))
def test_any_certified_field_differing_from_the_receipt_is_refused(field, value):
    receipt = make_receipt()
    record = copy.deepcopy(_record_for(receipt))
    if record[field[0]][field[1]] == value:
        return
    record[field[0]][field[1]] = value
    assert verify_certification_evidence(record, receipt)


def test_ledger_listing(tmp_path):
    qualified = make_receipt()
    write_json(
        tmp_path / "uk" / qualified.pair_id / "qualification_receipt.json",
        qualified.canonical_payload(),
    )
    pending = (
        tmp_path / "uk" / ("b" * 64) / "attempts" / "abc" / "replay" / "request.json"
    )
    write_json(pending, {"schema": "x"})
    assert [r.pair_id for r in latest_receipts(tmp_path)] == [qualified.pair_id]
    assert pending_attempts(tmp_path) == [pending.parent.parent]


def test_committed_bundle_has_ledger_evidence_for_qualified_pairs():
    """The release gate: an exact-pair certificate ships only with its evidence."""

    from policyengine.provenance.qualification_ledger import fetch_ledger_receipt

    bundle_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "policyengine"
        / "data"
        / "bundle"
        / "manifest.json"
    )
    bundle = json.loads(bundle_path.read_text())
    checked = 0
    for country_id, record in bundle["data_releases"].items():
        certification = record.get("certification") or {}
        if certification.get("compatibility_basis") != "qualified_exact_pair":
            continue
        receipt = fetch_ledger_receipt(
            country_id, certification["qualification_pair_id"]
        )
        assert verify_certification_evidence(record, receipt) == []
        checked += 1
    qualified = [
        country_id
        for country_id, record in bundle["data_releases"].items()
        if (record.get("certification") or {}).get("compatibility_basis")
        == "qualified_exact_pair"
    ]
    assert checked == len(qualified)


def test_pair_id_changes_with_any_pinned_identity():
    base = make_pair()
    for variant in (
        make_pair(model="2.126.9"),
        make_pair(core="3.33.1"),
        make_pair(data="1.59.0"),
        make_pair(dataset_sha="0" * 64),
    ):
        assert variant.pair_id != base.pair_id
