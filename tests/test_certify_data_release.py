"""Tests for direct data-release certification."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from policyengine.provenance.certification import (
    US_STATE_CODES,
    CertificationError,
    build_country_manifest_payload,
    certify_data_release,
    merge_area_coded_national_release_manifest,
    merge_local_area_release_manifest,
    merge_regional_release_manifest,
    merge_us_local_area_release_manifest,
    merge_us_regional_release_manifest,
    merge_us_state_release_manifest,
    model_compatibility_basis,
    parse_manifest_uri,
    required_supplemental_release_files,
    should_validate_vendored_artifacts,
    validate_release_manifest,
)
from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    DataReleaseManifest,
    _apply_dataset_overlays,
)

TAG = "populace-us-2024-aaaaaaa-20260101"
MANIFEST_URI = (
    f"hf://dataset/policyengine/populace-us@{TAG}/releases/{TAG}/release_manifest.json"
)
UK_TAG = "populace-uk-2023-bbbbbbb-20260101"
UK_MANIFEST_URI = (
    "hf://dataset/policyengine/populace-uk-private"
    f"@{UK_TAG}/releases/{UK_TAG}/release_manifest.json"
)
US_DATA_VERSION = "1.115.5"
US_DATA_MANIFEST_URI = (
    "hf://model/policyengine/policyengine-us-data"
    f"@{US_DATA_VERSION}/releases/{US_DATA_VERSION}/release_manifest.json"
)
US_LOCAL_AREA_TAG = "populace-us-2024-buildo-acs-local-767312d60-20260923T074941Z"
US_LOCAL_AREA_MANIFEST_URI = (
    "hf://dataset/policyengine/populace-us"
    f"@{US_LOCAL_AREA_TAG}/releases/{US_LOCAL_AREA_TAG}/release_manifest.json"
)


def _release_manifest_payload() -> dict:
    return {
        "schema_version": 1,
        "data_package": {"name": "populace-data", "version": "0.1.0"},
        "compatible_model_packages": [
            {"name": "policyengine-us", "specifier": "==1.723.0"}
        ],
        "compatible_core_packages": [
            {"name": "policyengine-core", "specifier": "==3.27.1"}
        ],
        "default_datasets": {"national": "populace_us_2024"},
        "build": {
            "build_id": TAG,
            "built_at": "2026-01-01T00:00:00Z",
            "built_with_model_package": {
                "name": "policyengine-us",
                "version": "1.723.0",
                "git_sha": "deadbeef",
            },
        },
        "metadata": {
            "region_datasets": {
                "national": {"path_template": "populace_us_2024.h5"},
                "state": {"path_template": "states/{state_code}.h5"},
            }
        },
        "artifacts": {
            "populace_us_2024": {
                "kind": "microdata",
                "path": "populace_us_2024.h5",
                "repo_id": "policyengine/populace-us",
                "revision": TAG,
                "sha256": "a" * 64,
                "size_bytes": 1,
            },
            "populace_us_2024_calibration": {
                "kind": "calibration",
                "path": "populace_us_2024_calibration.npz",
                "repo_id": "policyengine/populace-us",
                "revision": TAG,
                "sha256": "c" * 64,
                "size_bytes": 1,
            },
            "calibration_diagnostics": {
                "kind": "diagnostics",
                "path": "calibration_diagnostics.json",
                "repo_id": "policyengine/populace-us",
                "revision": TAG,
                "sha256": "e" * 64,
                "size_bytes": 1,
            },
            "us_source_coverage": {
                "kind": "diagnostics",
                "path": "us_source_coverage.json",
                "repo_id": "policyengine/populace-us",
                "revision": TAG,
                "sha256": "f" * 64,
                "size_bytes": 1,
            },
            "states/AK": {
                "kind": "microdata",
                "path": "states/AK.h5",
                "repo_id": "policyengine/policyengine-us-data",
                "revision": "1.115.5",
                "sha256": "b" * 64,
                "size_bytes": 1,
            },
            "districts/CA-01": {
                "kind": "microdata",
                "path": "districts/CA-01.h5",
                "repo_id": "policyengine/populace-us",
                "revision": TAG,
                "sha256": "1" * 64,
                "size_bytes": 1,
            },
        },
    }


def _populace_manifest_payload_without_regions() -> dict:
    payload = _release_manifest_payload()
    payload["metadata"] = {}
    payload["artifacts"].pop("states/AK")
    payload["artifacts"].pop("districts/CA-01")
    return payload


def _state_release_manifest_payload(
    *,
    missing: set[str] | None = None,
    malformed: dict[str, str] | None = None,
    without_hash: set[str] | None = None,
) -> dict:
    missing = missing or set()
    malformed = malformed or {}
    without_hash = without_hash or set()
    artifacts = {}
    for index, state_code in enumerate(US_STATE_CODES):
        if state_code in missing:
            continue
        path = malformed.get(state_code, f"states/{state_code}.h5")
        artifact = {
            "kind": "microdata",
            "path": path,
            "repo_id": "policyengine/policyengine-us-data",
            "revision": US_DATA_VERSION,
            "sha256": f"{index + 1:064x}",
            "size_bytes": 1,
        }
        if state_code in without_hash:
            artifact.pop("sha256")
        artifacts[f"states/{state_code}"] = artifact
    return {
        "schema_version": 1,
        "data_package": {"name": "policyengine-us-data", "version": US_DATA_VERSION},
        "artifacts": artifacts,
    }


def _local_area_release_manifest_payload() -> dict:
    return {
        "schema_version": 1,
        "data_package": {"name": "microcosm-data", "version": "0.1.0"},
        "dataset_role": "non_default_local_area",
        "is_default": False,
        "default_datasets": {},
        "build": {
            "build_id": US_LOCAL_AREA_TAG,
            "built_with_model_package": {
                "name": "policyengine-us",
                "version": "1.723.0",
            },
        },
        "artifacts": {
            "populace_us_2024_acs_local": {
                "kind": "microdata",
                "path": "populace_us_2024_acs_local.h5",
                "repo_id": "policyengine/populace-us",
                "revision": US_LOCAL_AREA_TAG,
                "sha256": "7" * 64,
                "size_bytes": 1,
            }
        },
    }


def _manifest() -> DataReleaseManifest:
    return DataReleaseManifest.model_validate(_release_manifest_payload())


def _load_bundle_script(monkeypatch):
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "bundle_script",
        scripts_dir / "bundle.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _uk_release_manifest_payload() -> dict:
    payload = _release_manifest_payload()
    payload["compatible_model_packages"] = [
        {"name": "policyengine-uk", "specifier": "==2.89.2"}
    ]
    payload["build"]["build_id"] = UK_TAG
    payload["build"]["built_with_model_package"] = {
        "name": "policyengine-uk",
        "version": "2.89.2",
        "git_sha": "deadbeef",
    }
    for artifact in payload["artifacts"].values():
        if artifact["repo_id"] == "policyengine/populace-us":
            artifact["repo_id"] = "policyengine/populace-uk-private"
            artifact["revision"] = UK_TAG
    payload["artifacts"].pop("us_source_coverage")
    payload["artifacts"].pop("states/AK")
    payload["artifacts"].pop("districts/CA-01")
    return payload


def _tmp_bundle(tmp_path: Path) -> Path:
    bundle_path = tmp_path / "manifest.json"
    bundle_path.write_text(json.dumps(_bundle_source_payload()) + "\n")
    return bundle_path


def _bundle_source_payload() -> dict:
    return {
        "schema_version": 2,
        "bundle_version": "9.9.9",
        "policyengine_version": "9.9.9",
        "packages": {
            "policyengine": {"name": "policyengine", "version": "9.9.9"},
            "policyengine-uk": {"name": "policyengine-uk", "version": "2.0.0"},
            "policyengine-us": {"name": "policyengine-us", "version": "1.0.0"},
        },
        "extras": {},
        "countries": {
            "uk": {"model_package": "policyengine-uk"},
            "us": {"model_package": "policyengine-us"},
        },
        "data_releases": {},
    }


class TestParseManifestUri:
    def test__given_dataset_uri__then_parses_parts(self):
        parts = parse_manifest_uri(MANIFEST_URI)

        assert parts["repo_type"] == "dataset"
        assert parts["repo_id"] == "policyengine/populace-us"
        assert parts["revision"] == TAG
        assert parts["path"] == f"releases/{TAG}/release_manifest.json"

    def test__given_bare_path__then_raises(self):
        with pytest.raises(CertificationError, match="hf://dataset"):
            parse_manifest_uri("https://example.com/manifest.json")


class TestModelBasisAgreement:
    """The primary and regional checks share one model-basis decision."""

    def test__given_claim_only__then_both_paths_give_the_same_warning(self):
        manifest = _manifest()
        manifest.build.built_with_model_package = None

        basis, warnings = validate_release_manifest(
            manifest, "policyengine-us", "1.723.0"
        )
        regional_basis, regional_warnings = model_compatibility_basis(
            manifest, "policyengine-us", "1.723.0"
        )

        assert basis == regional_basis == "legacy_compatible_model_package"
        assert regional_warnings == [
            warning for warning in warnings if "compatibility claim" in warning
        ]

    def test__given_no_basis__then_both_refusals_state_the_same_reason(self):
        manifest = _manifest()
        manifest.build.built_with_model_package = None

        with pytest.raises(CertificationError) as primary:
            validate_release_manifest(manifest, "policyengine-us", "9.9.9")
        with pytest.raises(CertificationError) as regional:
            model_compatibility_basis(manifest, "policyengine-us", "9.9.9")

        reason = str(regional.value).split(";")[0]
        assert str(primary.value).startswith(reason + ";")
        assert "automated qualification" in str(primary.value)
        assert "automated qualification" not in str(regional.value)


class TestValidateReleaseManifest:
    def test__given_built_with_match__then_built_with_basis_no_warnings(self):
        basis, warnings = validate_release_manifest(
            _manifest(), "policyengine-us", "1.723.0"
        )

        assert basis == "built_with_model_package"
        assert warnings == []

    def test__given_claim_only_match__then_publisher_basis_with_warning(self):
        payload = _release_manifest_payload()
        payload["compatible_model_packages"].append(
            {"name": "policyengine-us", "specifier": ">=1.724.0,<2"}
        )
        basis, warnings = validate_release_manifest(
            DataReleaseManifest.model_validate(payload),
            "policyengine-us",
            "1.730.0",
        )

        assert basis == "legacy_compatible_model_package"
        assert len(warnings) == 1
        assert "built with 1.723.0" in warnings[0]

    def test__given_no_basis__then_certification_refused(self):
        with pytest.raises(CertificationError, match="neither"):
            validate_release_manifest(_manifest(), "policyengine-us", "1.999.0")

    def test__given_missing_default__then_raises(self):
        payload = _release_manifest_payload()
        payload["default_datasets"] = {}

        with pytest.raises(CertificationError, match="national"):
            validate_release_manifest(
                DataReleaseManifest.model_validate(payload),
                "policyengine-us",
                "1.723.0",
            )

    def test__given_unpinned_artifact__then_raises(self):
        payload = _release_manifest_payload()
        payload["artifacts"]["populace_us_2024"]["revision"] = ""

        with pytest.raises(CertificationError, match="revision"):
            validate_release_manifest(
                DataReleaseManifest.model_validate(payload),
                "policyengine-us",
                "1.723.0",
            )


class TestBuildCountryManifestPayload:
    def _payload(self) -> dict:
        return build_country_manifest_payload(
            country="us",
            manifest=_manifest(),
            uri_parts=parse_manifest_uri(MANIFEST_URI),
            policyengine_version="9.9.9",
            model_package="policyengine-us",
            model_version="1.723.0",
            model_wheel={"sha256": "d" * 64, "url": "https://example/wheel"},
        )

    def test__given_manifest__then_pins_data_package_and_default(self):
        payload = self._payload()

        assert payload["bundle_id"] == "us-9.9.9"
        assert payload["data_package"]["name"] == "populace-data"
        assert payload["data_package"]["repo_id"] == "policyengine/populace-us"
        assert payload["data_package"]["repo_type"] == "dataset"
        assert payload["data_package"]["release_manifest_revision"] == TAG
        assert payload["default_dataset"] == "populace_us_2024"
        assert payload["model_package"]["sha256"] == "d" * 64
        assert payload["model_package"]["wheel_url"] == "https://example/wheel"

    def test__given_populace_area_h5_artifact__then_omits_it_from_runtime_bundle(self):
        payload = self._payload()

        assert "states/AK" not in payload["datasets"]
        assert "districts/CA-01" not in payload["datasets"]

    def test__given_release_scoped_diagnostics__then_rewrites_paths(self):
        payload = self._payload()

        assert payload["datasets"]["populace_us_2024"]["path"] == "populace_us_2024.h5"
        assert (
            payload["datasets"]["populace_us_2024_calibration"]["path"]
            == "populace_us_2024_calibration.npz"
        )
        assert payload["datasets"]["calibration_diagnostics"]["path"] == (
            f"releases/{TAG}/calibration_diagnostics.json"
        )
        assert payload["datasets"]["us_source_coverage"]["path"] == (
            f"releases/{TAG}/us_source_coverage.json"
        )

    def test__given_populace_region_templates__then_only_national_is_carried_through(
        self,
    ):
        payload = self._payload()

        assert payload["region_datasets"] == {
            "national": {"path_template": "populace_us_2024.h5"}
        }

    def test__given_populace_manifest_without_regions__then_adds_national_template(
        self,
    ):
        payload = build_country_manifest_payload(
            country="us",
            manifest=DataReleaseManifest.model_validate(
                _populace_manifest_payload_without_regions()
            ),
            uri_parts=parse_manifest_uri(MANIFEST_URI),
            policyengine_version="9.9.9",
            model_package="policyengine-us",
            model_version="1.723.0",
            model_wheel={},
        )

        assert payload["region_datasets"] == {
            "national": {"path_template": "populace_us_2024.h5"}
        }

    def test__given_build_provenance__then_certification_carries_it(self):
        payload = self._payload()

        certification = payload["certification"]
        assert certification["compatibility_basis"] == "built_with_model_package"
        assert certification["certified_by"] == "policyengine.py bundle certification"
        assert certification["data_build_id"] == TAG
        assert certification["built_with_model_version"] == "1.723.0"
        assert certification["built_with_model_git_sha"] == "deadbeef"
        assert payload["certified_data_artifact"]["build_id"] == TAG
        assert payload["certified_data_artifact"]["uri"] == (
            f"hf://policyengine/populace-us/populace_us_2024.h5@{TAG}"
        )


class TestMergeUSStateReleaseManifest:
    def test__given_state_manifest__then_does_not_vendor_state_region_artifacts(self):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        states = DataReleaseManifest.model_validate(_state_release_manifest_payload())

        merged = merge_us_state_release_manifest(primary, states)
        payload = build_country_manifest_payload(
            country="us",
            manifest=merged,
            uri_parts=parse_manifest_uri(MANIFEST_URI),
            policyengine_version="9.9.9",
            model_package="policyengine-us",
            model_version="1.723.0",
            model_wheel={},
        )

        assert "states/CA" not in payload["datasets"]
        assert payload["region_datasets"] == {
            "national": {"path_template": "populace_us_2024.h5"},
        }

    def test__given_missing_state_artifact__then_raises(self):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        states = DataReleaseManifest.model_validate(
            _state_release_manifest_payload(missing={"CA"})
        )

        with pytest.raises(CertificationError, match="Missing US state artifacts: CA"):
            merge_us_state_release_manifest(primary, states)

    def test__given_malformed_state_path__then_raises(self):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        states = DataReleaseManifest.model_validate(
            _state_release_manifest_payload(malformed={"CA": "state/CA.h5"})
        )

        with pytest.raises(CertificationError, match="states/<STATE>.h5"):
            merge_us_state_release_manifest(primary, states)

    def test__given_state_without_hash__then_raises(self):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        states = DataReleaseManifest.model_validate(
            _state_release_manifest_payload(without_hash={"CA"})
        )

        with pytest.raises(CertificationError, match="states/CA"):
            merge_us_state_release_manifest(primary, states)

    def test__given_duplicate_state_artifact__then_warns_and_ignores_duplicate(self):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        state_payload = _state_release_manifest_payload()
        state_payload["artifacts"]["states/CA_duplicate"] = {
            **state_payload["artifacts"]["states/CA"],
            "sha256": "f" * 64,
        }
        states = DataReleaseManifest.model_validate(state_payload)

        with pytest.warns(RuntimeWarning, match="Duplicate US state artifact for CA"):
            merged = merge_us_state_release_manifest(primary, states)

        assert "states/CA_duplicate" not in merged.artifacts
        assert (
            merged.artifacts["states/CA"].sha256
            == (state_payload["artifacts"]["states/CA"]["sha256"])
        )


class TestMergeUSLocalAreaReleaseManifest:
    def test__given_typed_local_area_release__then_certifies_shared_dataset(self):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        regional = DataReleaseManifest.model_validate(
            _local_area_release_manifest_payload()
        )

        merged = merge_us_local_area_release_manifest(
            primary,
            regional,
            regional_repo_type="dataset",
        )
        payload = build_country_manifest_payload(
            country="us",
            manifest=merged,
            uri_parts=parse_manifest_uri(MANIFEST_URI),
            policyengine_version="9.9.9",
            model_package="policyengine-us",
            model_version="1.723.0",
            model_wheel={},
        )

        local_dataset = payload["datasets"]["populace_us_2024_acs_local"]
        assert local_dataset == {
            "path": "populace_us_2024_acs_local.h5",
            "revision": US_LOCAL_AREA_TAG,
            "sha256": "7" * 64,
            "repo_id": "policyengine/populace-us",
            "repo_type": "dataset",
        }
        assert payload["region_datasets"] == {
            "congressional_district": {
                "path_template": "populace_us_2024_acs_local.h5"
            },
            "national": {"path_template": "populace_us_2024.h5"},
            "state": {"path_template": "populace_us_2024_acs_local.h5"},
        }

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        [
            ("dataset_role", "other", "dataset_role='non_default_local_area'"),
            ("is_default", True, "is_default=false"),
            ("default_datasets", {"national": "local"}, "default datasets"),
        ],
    )
    def test__given_invalid_release_role__then_rejects_it(
        self,
        field,
        value,
        message,
    ):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        regional_payload = _local_area_release_manifest_payload()
        regional_payload[field] = value
        regional = DataReleaseManifest.model_validate(regional_payload)

        with pytest.raises(CertificationError, match=message):
            merge_us_local_area_release_manifest(primary, regional)

    def test__given_more_than_one_microdata_artifact__then_rejects_it(self):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        regional_payload = _local_area_release_manifest_payload()
        regional_payload["artifacts"]["second"] = {
            **regional_payload["artifacts"]["populace_us_2024_acs_local"],
            "path": "second.h5",
        }
        regional = DataReleaseManifest.model_validate(regional_payload)

        with pytest.raises(CertificationError, match="exactly one microdata"):
            merge_us_local_area_release_manifest(primary, regional)

    def test__given_legacy_regional_release__then_uses_state_merge(self):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        states = DataReleaseManifest.model_validate(_state_release_manifest_payload())

        merged = merge_us_regional_release_manifest(primary, states)

        assert "states/CA" in merged.artifacts
        assert merged.metadata["region_datasets"]["state"] == {
            "path_template": "states/{state_code}.h5"
        }

    def test__given_unknown_regional_role__then_rejects_it(self):
        primary = DataReleaseManifest.model_validate(
            _populace_manifest_payload_without_regions()
        )
        regional_payload = _local_area_release_manifest_payload()
        regional_payload["dataset_role"] = "unknown"
        regional = DataReleaseManifest.model_validate(regional_payload)

        with pytest.raises(CertificationError, match="Unsupported.*dataset_role"):
            merge_us_regional_release_manifest(primary, regional)


class TestCertifyDataRelease:
    def test__given_fetched_populace_manifest__then_updates_bundle_manifest(
        self, tmp_path
    ):
        bundle_path = tmp_path / "manifest.json"
        bundle_path.write_text(json.dumps(_bundle_source_payload()) + "\n")
        response = MagicMock()
        response.status_code = 200
        response.content = json.dumps(_uk_release_manifest_payload()).encode()

        with (
            patch(
                "policyengine.provenance.certification.requests.get",
                return_value=response,
            ),
            patch(
                "policyengine.provenance.certification.head_artifact",
                return_value=True,
            ),
            patch(
                "policyengine.provenance.certification.head_release_file",
                return_value=True,
            ),
            patch(
                "policyengine.provenance.certification.head_artifact_reference",
                return_value=True,
            ),
            patch(
                "policyengine.provenance.certification.fetch_pypi_wheel_metadata",
                return_value={"sha256": "d" * 64, "url": "https://example"},
            ),
            patch(
                "policyengine.provenance.certification.policyengine_version",
                return_value="9.9.9",
            ),
        ):
            result = certify_data_release(
                country="uk",
                data_producer="populace",
                manifest_uri=UK_MANIFEST_URI,
                model_version="2.89.2",
                bundle_path=bundle_path,
            )

        written = json.loads(bundle_path.read_text())
        release = written["data_releases"]["uk"]
        assert release["data_producer"] == "populace"
        assert release["default_dataset"] == "populace_us_2024"
        assert release["certification"]["data_build_id"] == UK_TAG
        assert release["version"] == UK_TAG
        assert release["source_manifest_uri"] == UK_MANIFEST_URI
        assert written["packages"]["policyengine-uk"]["version"] == "2.89.2"
        assert result.data_producer == "populace"
        assert result.dataset_count == 3
        assert result.build_id == UK_TAG
        assert result.bundle_path == bundle_path

    def test__given_us_local_area_manifest__then_certifies_shared_regional_dataset(
        self, tmp_path
    ):
        bundle_path = tmp_path / "manifest.json"
        bundle_path.write_text(json.dumps(_bundle_source_payload()) + "\n")
        primary_response = MagicMock()
        primary_response.status_code = 200
        primary_response.content = json.dumps(
            _populace_manifest_payload_without_regions()
        ).encode()
        regional_response = MagicMock()
        regional_response.status_code = 200
        regional_response.content = json.dumps(
            _local_area_release_manifest_payload()
        ).encode()

        with (
            patch(
                "policyengine.provenance.certification.requests.get",
                side_effect=[primary_response, regional_response],
            ),
            patch(
                "policyengine.provenance.certification.head_artifact",
                return_value=True,
            ),
            patch(
                "policyengine.provenance.certification.head_release_file",
                return_value=True,
            ),
            patch(
                "policyengine.provenance.certification.head_artifact_reference",
                return_value=True,
            ),
            patch(
                "policyengine.provenance.certification.fetch_pypi_wheel_metadata",
                return_value={"sha256": "d" * 64, "url": "https://example"},
            ),
            patch(
                "policyengine.provenance.certification.policyengine_version",
                return_value="9.9.9",
            ),
        ):
            result = certify_data_release(
                country="us",
                data_producer="populace",
                manifest_uri=MANIFEST_URI,
                regional_manifest_uri=US_LOCAL_AREA_MANIFEST_URI,
                model_version="1.723.0",
                bundle_path=bundle_path,
            )

        written = json.loads(bundle_path.read_text())
        release = written["data_releases"]["us"]
        assert release["source_manifest_uri"] == MANIFEST_URI
        assert release["regional_source_manifest_uri"] == US_LOCAL_AREA_MANIFEST_URI
        assert release["region_datasets"] == {
            "congressional_district": {
                "path_template": "populace_us_2024_acs_local.h5"
            },
            "national": {"path_template": "populace_us_2024.h5"},
            "state": {"path_template": "populace_us_2024_acs_local.h5"},
        }
        assert "populace_us_2024_acs_local" in release["datasets"]
        assert (
            release["datasets"]["populace_us_2024_acs_local"]["repo_type"] == "dataset"
        )
        assert release["regional_release_kind"] == "local_area"
        assert result.dataset_count == 5

    def test__given_us_without_data_producer__then_legacy_update_is_explicitly_unsupported(
        self, tmp_path
    ):
        bundle_path = tmp_path / "manifest.json"
        bundle_path.write_text(json.dumps(_bundle_source_payload()) + "\n")

        with pytest.raises(CertificationError, match="Legacy data-producer"):
            certify_data_release(
                country="us",
                manifest_uri=MANIFEST_URI,
                model_version="1.723.0",
                bundle_path=bundle_path,
            )

    def test__given_bundle_wrapper_regional_args__then_forwards_to_certifier(
        self, monkeypatch
    ):
        bundle_script = _load_bundle_script(monkeypatch)
        captured: dict[str, list[str]] = {}
        fake_certifier = ModuleType("certify_data_release")

        def fake_main(argv: list[str]) -> int:
            captured["argv"] = argv
            return 0

        fake_certifier.main = fake_main
        monkeypatch.setitem(sys.modules, "certify_data_release", fake_certifier)

        result = bundle_script.main(
            [
                "certify-data",
                "--country",
                "us",
                "--data-producer",
                "populace",
                "--manifest-uri",
                MANIFEST_URI,
                "--regional-manifest-uri",
                US_DATA_MANIFEST_URI,
                "--regional-artifact-prefix",
                "states/",
                "--regional-path-template",
                "states/{state_code}.h5",
                "--model-version",
                "1.723.0",
                "--no-generate",
                "--skip-artifact-check",
            ]
        )

        assert result == 0
        assert captured["argv"] == [
            "--country",
            "us",
            "--manifest-uri",
            MANIFEST_URI,
            "--data-producer",
            "populace",
            "--model-version",
            "1.723.0",
            "--regional-manifest-uri",
            US_DATA_MANIFEST_URI,
            "--regional-artifact-prefix",
            "states/",
            "--regional-path-template",
            "states/{state_code}.h5",
            "--no-generate",
            "--skip-artifact-check",
        ]

    def test__given_missing_populace_us_source_coverage__then_raises(self, tmp_path):
        response = MagicMock()
        response.status_code = 200
        response.content = json.dumps(_release_manifest_payload()).encode()

        with (
            patch(
                "policyengine.provenance.certification.requests.get",
                return_value=response,
            ),
            patch(
                "policyengine.provenance.certification.head_release_file",
                return_value=False,
            ),
            pytest.raises(CertificationError, match="us_source_coverage.json"),
        ):
            certify_data_release(
                country="us",
                data_producer="populace",
                manifest_uri=MANIFEST_URI,
                model_version="1.723.0",
                bundle_path=_tmp_bundle(tmp_path),
            )

    def test__given_unreachable_artifact__then_raises(self, tmp_path):
        response = MagicMock()
        response.status_code = 200
        response.content = json.dumps(_release_manifest_payload()).encode()

        with (
            patch(
                "policyengine.provenance.certification.requests.get",
                return_value=response,
            ),
            patch(
                "policyengine.provenance.certification.head_artifact",
                return_value=False,
            ),
            patch(
                "policyengine.provenance.certification.head_release_file",
                return_value=True,
            ),
            patch(
                "policyengine.provenance.certification.head_artifact_reference",
                return_value=True,
            ),
            pytest.raises(CertificationError, match="not reachable"),
        ):
            certify_data_release(
                country="us",
                data_producer="populace",
                manifest_uri=MANIFEST_URI,
                model_version="1.723.0",
                bundle_path=_tmp_bundle(tmp_path),
            )

    def test__given_unreachable_vendored_artifact__then_raises(self, tmp_path):
        response = MagicMock()
        response.status_code = 200
        response.content = json.dumps(_release_manifest_payload()).encode()

        with (
            patch(
                "policyengine.provenance.certification.requests.get",
                return_value=response,
            ),
            patch(
                "policyengine.provenance.certification.head_artifact",
                return_value=True,
            ),
            patch(
                "policyengine.provenance.certification.head_release_file",
                return_value=True,
            ),
            patch(
                "policyengine.provenance.certification.fetch_pypi_wheel_metadata",
                return_value={"sha256": "d" * 64, "url": "https://example"},
            ),
            patch(
                "policyengine.provenance.certification.head_artifact_reference",
                return_value=False,
            ),
            pytest.raises(CertificationError, match="Vendored artifact"),
        ):
            certify_data_release(
                country="us",
                data_producer="populace",
                manifest_uri=MANIFEST_URI,
                model_version="1.723.0",
                bundle_path=_tmp_bundle(tmp_path),
            )


class TestVendoredSidecarBinding:
    def test__given_vendored_bundle_manifest__then_tro_sidecar_binds_it(self):
        """The shipped TRO must bind the certified country payload embedded in
        the bundle manifest."""
        import hashlib
        from importlib.resources import files

        bundle_dir = files("policyengine").joinpath("data", "bundle")
        expected = hashlib.sha256(
            bundle_dir.joinpath("manifest.json").read_bytes()
        ).hexdigest()

        tro = json.loads(bundle_dir.joinpath("us.trace.tro.jsonld").read_text())
        artifacts = tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
        bundle_manifest = next(
            a for a in artifacts if a["@id"].endswith("bundle_manifest")
        )

        assert bundle_manifest["trov:sha256"] == expected
        performance = tro["@graph"][0]["trov:hasPerformance"]
        assert performance["pe:emittedIn"] == "repository-bundle"


def _source_enrichment_manifest_payload() -> dict:
    """A `microcosm-data` release whose sidecars use the `evidence` kind.

    This is the shape the Populace US producer publishes for source-enrichment
    releases: the data package is named `microcosm-data` rather than
    `populace-data`, and release-directory sidecars are labelled `evidence`
    rather than `diagnostics`.
    """
    payload = _release_manifest_payload()
    payload["data_package"]["name"] = "microcosm-data"
    payload["artifacts"]["us_source_coverage"]["kind"] = "evidence"
    payload["artifacts"]["build_manifest"] = {
        "kind": "evidence",
        "path": "build_manifest.json",
        "repo_id": "policyengine/populace-us",
        "revision": TAG,
        "sha256": "1" * 64,
        "size_bytes": 1,
    }
    return payload


class TestSourceEnrichmentProducerRelease:
    """The `microcosm-data` producer name must keep every Populace rule armed.

    A release published under the newer producer name previously fell through
    every `populace-data` guard, which both skipped the per-artifact
    reachability check and left release-scoped sidecars pinned at repo-root
    paths that do not resolve.
    """

    def _payload(self) -> dict:
        return build_country_manifest_payload(
            country="us",
            manifest=DataReleaseManifest.model_validate(
                _source_enrichment_manifest_payload()
            ),
            uri_parts=parse_manifest_uri(MANIFEST_URI),
            policyengine_version="9.9.9",
            model_package="policyengine-us",
            model_version="1.723.0",
            model_wheel={"sha256": "d" * 64, "url": "https://example/wheel"},
        )

    def test__given_evidence_kind_sidecar__then_rewrites_to_release_path(self):
        datasets = self._payload()["datasets"]

        assert datasets["us_source_coverage"]["path"] == (
            f"releases/{TAG}/us_source_coverage.json"
        )
        assert datasets["build_manifest"]["path"] == (
            f"releases/{TAG}/build_manifest.json"
        )

    def test__given_microdata_kind__then_keeps_repo_root_path(self):
        datasets = self._payload()["datasets"]

        assert datasets["populace_us_2024"]["path"] == "populace_us_2024.h5"
        assert (
            datasets["populace_us_2024_calibration"]["path"]
            == "populace_us_2024_calibration.npz"
        )

    def test__given_microcosm_producer__then_validates_vendored_artifacts(self):
        assert should_validate_vendored_artifacts(
            "us",
            DataReleaseManifest.model_validate(_source_enrichment_manifest_payload()),
            parse_manifest_uri(MANIFEST_URI),
        )

    def test__given_microcosm_producer__then_requires_source_coverage_file(self):
        assert required_supplemental_release_files(
            "us",
            DataReleaseManifest.model_validate(_source_enrichment_manifest_payload()),
            parse_manifest_uri(MANIFEST_URI),
        ) == ("us_source_coverage.json",)

    def test__given_microcosm_producer__then_still_omits_area_h5_artifacts(self):
        datasets = self._payload()["datasets"]

        assert "states/AK" not in datasets
        assert "districts/CA-01" not in datasets

    def test__given_microcosm_producer__then_still_drops_area_region_templates(self):
        assert self._payload()["region_datasets"] == {
            "national": {"path_template": "populace_us_2024.h5"}
        }


UK_NATIONAL_LINE = "microcosm-uk-2024-25-national"
UK_NATIONAL_TAG = f"{UK_NATIONAL_LINE}-20261101T000000Z-aaaaaaaa"
UK_NATIONAL_URI = (
    "hf://dataset/policyengine/populace-uk-private"
    f"@{UK_NATIONAL_TAG}/releases/{UK_NATIONAL_LINE}/release_manifest.json"
)
UK_DENSE_LINE = "microcosm-uk-2024-25-dense"
UK_DENSE_TAG = f"{UK_DENSE_LINE}-20261101T000000Z-bbbbbbbb"
UK_DENSE_URI = (
    "hf://dataset/policyengine/populace-uk-private"
    f"@{UK_DENSE_TAG}/releases/{UK_DENSE_LINE}/release_manifest.json"
)
EFRS_URI = (
    "hf://model/policyengine/policyengine-uk-data-private"
    "@0aa3eee1cdae8f8125f4aff126a8f01957595dc3/releases/1.58.0/release_manifest.json"
)
UK_MODEL_VERSION = "2.126.12"
EFRS_REPO = "policyengine/policyengine-uk-data-private"


def _microcosm_uk_national_payload() -> dict:
    return {
        "schema_version": 1,
        "data_package": {"name": "microcosm-data", "version": "0.1.0"},
        "default_datasets": {"national": "microcosm_uk_2024_25"},
        "compatible_model_packages": [
            {"name": "policyengine-uk", "specifier": f"=={UK_MODEL_VERSION}"}
        ],
        "build": {
            "build_id": UK_NATIONAL_LINE,
            "cut_tag": UK_NATIONAL_TAG,
            "built_with_model_package": {
                "name": "policyengine-uk",
                "version": UK_MODEL_VERSION,
            },
        },
        "artifacts": {
            "microcosm_uk_2024_25": {
                "kind": "microdata",
                "path": "microcosm_uk_2024_25.h5",
                "repo_id": "policyengine/populace-uk-private",
                "revision": UK_NATIONAL_TAG,
                "sha256": "a" * 64,
            },
            "calibration_diagnostics": {
                "kind": "diagnostics",
                "path": "calibration_diagnostics.json",
                "repo_id": "policyengine/populace-uk-private",
                "revision": UK_NATIONAL_TAG,
            },
        },
    }


def _microcosm_uk_dense_payload() -> dict:
    return {
        "schema_version": 1,
        "data_package": {"name": "microcosm-data", "version": "0.1.0"},
        "dataset_role": "non_default_local_area",
        "is_default": False,
        "default_datasets": {},
        "build": {
            "build_id": UK_DENSE_LINE,
            "cut_tag": UK_DENSE_TAG,
            "built_with_model_package": {
                "name": "policyengine-uk",
                "version": UK_MODEL_VERSION,
            },
        },
        "artifacts": {
            "microcosm_uk_2024_25_dense": {
                "kind": "microdata",
                "path": "microcosm_uk_2024_25_dense.h5",
                "repo_id": "policyengine/populace-uk-private",
                "revision": UK_DENSE_TAG,
                "sha256": "b" * 64,
            },
            "rowwise_candidate_manifest": {
                "kind": "diagnostics",
                "path": "rowwise_candidate_manifest.json",
                "repo_id": "policyengine/populace-uk-private",
                "revision": UK_DENSE_TAG,
            },
        },
    }


def _efrs_release_payload() -> dict:
    """Shaped like policyengine-uk-data's enhanced FRS 1.58.0 release."""

    def artifact(kind: str, path: str, digit: str) -> dict:
        return {
            "kind": kind,
            "path": path,
            "repo_id": EFRS_REPO,
            "revision": "1.58.0",
            "sha256": digit * 64,
        }

    return {
        "schema_version": 1,
        "data_package": {"name": "policyengine-uk-data", "version": "1.58.0"},
        "default_datasets": {
            "national": "enhanced_frs_2024_25",
            "baseline": "frs_2024_25",
        },
        "compatible_model_packages": [
            {"name": "policyengine-uk", "specifier": "==2.122.2"},
            {"name": "policyengine-uk", "specifier": f"=={UK_MODEL_VERSION}"},
        ],
        "build": {
            "build_id": "policyengine-uk-data-1.58.0",
            "built_with_model_package": {
                "name": "policyengine-uk",
                "version": "2.122.2",
            },
        },
        "artifacts": {
            "enhanced_frs_2024_25": artifact(
                "microdata", "enhanced_frs_2024_25.h5", "1"
            ),
            "frs_2024_25": artifact("microdata", "frs_2024_25.h5", "2"),
            "local_authority_weights": artifact(
                "weights", "local_authority_weights.h5", "3"
            ),
            "local_geography_weights": artifact(
                "weights", "local_geography_weights.csv.gz", "4"
            ),
            "parliamentary_constituency_weights": artifact(
                "weights", "parliamentary_constituency_weights.h5", "5"
            ),
        },
    }


def _response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.content = json.dumps(payload).encode()
    return response


def _certify_uk(
    bundle_path: Path, responses: list, manifest_uri: str = UK_NATIONAL_URI, **kwargs
):
    with (
        patch(
            "policyengine.provenance.certification.requests.get",
            side_effect=responses,
        ),
        patch(
            "policyengine.provenance.certification.head_artifact",
            return_value=True,
        ),
        patch(
            "policyengine.provenance.certification.head_artifact_reference",
            return_value=True,
        ),
        patch(
            "policyengine.provenance.certification.fetch_pypi_wheel_metadata",
            return_value={"sha256": "d" * 64, "url": "https://example"},
        ),
        patch(
            "policyengine.provenance.certification.policyengine_version",
            return_value="9.9.9",
        ),
    ):
        return certify_data_release(
            country="uk",
            data_producer="populace",
            manifest_uri=manifest_uri,
            model_version=UK_MODEL_VERSION,
            bundle_path=bundle_path,
            **kwargs,
        )


def _sim_api_routes_both_area_types(release: dict) -> bool:
    # policyengine-sim-api's uk_area_regions_routed: a UK default without area
    # codes is accepted only when both area region types are routed.
    manifest = CountryReleaseManifest.model_validate(release)
    return all(
        region_type in manifest.region_datasets
        for region_type in ("constituency", "local_authority")
    )


class TestUKRegionalMerge:
    def _national(self) -> DataReleaseManifest:
        return DataReleaseManifest.model_validate(_microcosm_uk_national_payload())

    def test__given_uk_local_area_release__then_routes_constituencies_and_las(self):
        merged, kind = merge_regional_release_manifest(
            "uk",
            self._national(),
            DataReleaseManifest.model_validate(_microcosm_uk_dense_payload()),
            regional_repo_type="dataset",
        )

        assert kind == "local_area"
        assert merged.metadata["region_datasets"] == {
            "national": {"path_template": "microcosm_uk_2024_25.h5"},
            "constituency": {"path_template": "microcosm_uk_2024_25_dense.h5"},
            "local_authority": {"path_template": "microcosm_uk_2024_25_dense.h5"},
        }
        dense = merged.artifacts["microcosm_uk_2024_25_dense"]
        assert dense.revision == UK_DENSE_TAG
        assert dense.repo_type == "dataset"
        # Only the microdata joins; the local release's evidence stays there.
        assert "rowwise_candidate_manifest" not in merged.artifacts

    def test__given_efrs_as_area_coded_national__then_carries_dataset_and_matrices(
        self,
    ):
        merged, kind = merge_regional_release_manifest(
            "uk",
            self._national(),
            DataReleaseManifest.model_validate(_efrs_release_payload()),
            release_kind="area_coded_national",
            regional_repo_type="model",
        )

        assert kind == "area_coded_national"
        assert merged.default_datasets == {"national": "microcosm_uk_2024_25"}
        region_datasets = merged.metadata["region_datasets"]
        assert region_datasets["constituency"] == {
            "path_template": "enhanced_frs_2024_25.h5"
        }
        assert region_datasets["local_authority"] == region_datasets["constituency"]
        carried = {
            "enhanced_frs_2024_25",
            "local_authority_weights",
            "local_geography_weights",
            "parliamentary_constituency_weights",
        }
        assert carried <= set(merged.artifacts)
        assert "frs_2024_25" not in merged.artifacts
        for name in carried:
            artifact = merged.artifacts[name]
            assert (artifact.repo_id, artifact.revision) == (EFRS_REPO, "1.58.0")
            assert artifact.repo_type == "model"

    def test__given_national_release_without_kind__then_names_the_flag(self):
        with pytest.raises(
            CertificationError, match="--regional-release-kind area_coded_national"
        ):
            merge_regional_release_manifest(
                "uk",
                self._national(),
                DataReleaseManifest.model_validate(_efrs_release_payload()),
            )

    def test__given_area_coded_release_without_a_matrix__then_rejects_it(self):
        payload = _efrs_release_payload()
        payload["artifacts"].pop("local_authority_weights")

        with pytest.raises(CertificationError, match="local_authority_weights.h5"):
            merge_area_coded_national_release_manifest(
                "uk",
                self._national(),
                DataReleaseManifest.model_validate(payload),
            )

    def test__given_local_area_release_as_area_coded_national__then_rejects_it(self):
        with pytest.raises(CertificationError, match="must be a national release"):
            merge_area_coded_national_release_manifest(
                "uk",
                self._national(),
                DataReleaseManifest.model_validate(_microcosm_uk_dense_payload()),
            )

    def test__given_us_area_coded_national__then_rejects_it(self):
        with pytest.raises(CertificationError, match="only supported for the UK"):
            merge_area_coded_national_release_manifest(
                "us",
                DataReleaseManifest.model_validate(
                    _populace_manifest_payload_without_regions()
                ),
                DataReleaseManifest.model_validate(_efrs_release_payload()),
            )

    def test__given_uk_local_area_release__then_generic_merge_checks_role(self):
        payload = _microcosm_uk_dense_payload()
        payload["is_default"] = True

        with pytest.raises(
            CertificationError, match="UK local-area release must declare is_default"
        ):
            merge_local_area_release_manifest(
                "uk",
                self._national(),
                DataReleaseManifest.model_validate(payload),
            )


class TestUKRegionalCertification:
    def test__given_national_first_efrs_route__then_bundle_routes_areas_to_efrs(
        self, tmp_path
    ):
        bundle_path = _tmp_bundle(tmp_path)

        result = _certify_uk(
            bundle_path,
            [
                _response(_microcosm_uk_national_payload()),
                _response(_efrs_release_payload()),
            ],
            regional_manifest_uri=EFRS_URI,
            regional_release_kind="area_coded_national",
        )

        release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
        assert release["default_dataset"] == "microcosm_uk_2024_25"
        assert release["regional_release_kind"] == "area_coded_national"
        assert release["regional_source_manifest_uri"] == EFRS_URI
        assert release["region_datasets"]["constituency"] == {
            "path_template": "enhanced_frs_2024_25.h5"
        }
        assert _sim_api_routes_both_area_types(release)
        # sim-api binds a matrix only to the release of the dataset it
        # reweights: the same repo and revision.
        datasets = release["datasets"]
        for name in (
            "enhanced_frs_2024_25",
            "parliamentary_constituency_weights",
            "local_authority_weights",
        ):
            assert (datasets[name]["repo_id"], datasets[name]["revision"]) == (
                EFRS_REPO,
                "1.58.0",
            )
            assert datasets[name]["repo_type"] == "model"
        # Diagnostics stay under the release directory of the national cut.
        assert datasets["calibration_diagnostics"]["path"] == (
            f"releases/{UK_NATIONAL_LINE}/calibration_diagnostics.json"
        )
        # The cut tag, not the line name, identifies the certified build.
        assert release["version"] == UK_NATIONAL_TAG
        assert release["certification"]["data_build_id"] == UK_NATIONAL_TAG
        assert result.build_id == UK_NATIONAL_TAG

    def test__given_ship_together_dense_route__then_bundle_routes_areas_to_local(
        self, tmp_path
    ):
        bundle_path = _tmp_bundle(tmp_path)

        _certify_uk(
            bundle_path,
            [
                _response(_microcosm_uk_national_payload()),
                _response(_microcosm_uk_dense_payload()),
            ],
            regional_manifest_uri=UK_DENSE_URI,
        )

        release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
        assert release["regional_release_kind"] == "local_area"
        assert release["region_datasets"]["local_authority"] == {
            "path_template": "microcosm_uk_2024_25_dense.h5"
        }
        assert release["datasets"]["microcosm_uk_2024_25_dense"]["revision"] == (
            UK_DENSE_TAG
        )
        assert _sim_api_routes_both_area_types(release)

    def test__given_regional_release_without_a_claim__then_refuses(self, tmp_path):
        efrs = _efrs_release_payload()
        efrs["compatible_model_packages"] = [
            {"name": "policyengine-uk", "specifier": "==2.122.2"}
        ]

        with pytest.raises(CertificationError, match="Regional release .*2.126.12"):
            _certify_uk(
                _tmp_bundle(tmp_path),
                [
                    _response(_microcosm_uk_national_payload()),
                    _response(efrs),
                ],
                regional_manifest_uri=EFRS_URI,
                regional_release_kind="area_coded_national",
            )

    def _older_dense(self) -> dict:
        dense = _microcosm_uk_dense_payload()
        dense["build"]["built_with_model_package"]["version"] = "2.120.0"
        dense["build"]["built_with_core_package"] = {
            "name": "policyengine-core",
            "version": "3.33.3",
        }
        dense["compatible_model_packages"] = [
            {"name": "policyengine-uk", "specifier": "==2.120.0"}
        ]
        return dense

    def test__given_older_dense_cut__then_refuses_without_an_accepted_mismatch(
        self, tmp_path
    ):
        with pytest.raises(CertificationError, match="Regional release .*2.126.12"):
            _certify_uk(
                _tmp_bundle(tmp_path),
                [
                    _response(_microcosm_uk_national_payload()),
                    _response(self._older_dense()),
                ],
                regional_manifest_uri=UK_DENSE_URI,
            )

    def test__given_accepted_mismatch__then_routes_and_records_it(self, tmp_path):
        bundle_path = _tmp_bundle(tmp_path)
        reason = "area receipts are uncertified; the dense cut lags one release"
        from tests.test_regional_input_evidence import input_evidence

        evidence = input_evidence(self._older_dense())

        result = _certify_uk(
            bundle_path,
            [
                _response(_microcosm_uk_national_payload()),
                _response(self._older_dense()),
            ],
            regional_manifest_uri=UK_DENSE_URI,
            regional_model_mismatch_reason=reason,
            regional_input_surface_evidence=evidence,
        )

        release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
        assert release["regional_release_kind"] == "local_area"
        assert release["regional_certification"] == {
            "compatibility_basis": "accepted_model_mismatch",
            "certified_for_model_version": UK_MODEL_VERSION,
            "built_with_model_version": "2.120.0",
            "accepted_reason": reason,
            "area_receipts": "uncertified",
            "regional_manifest_uri": UK_DENSE_URI,
            "regional_manifest_sha256": evidence["regional_manifest_sha256"],
            "defaulted_inputs": evidence["defaulted_inputs"],
            "dropped_columns": [],
            "never_modelled_columns": [],
            "limitations": evidence["limitations"],
            "evidence": evidence,
        }
        # The national certificate itself is untouched by the regional record.
        assert release["certification"]["compatibility_basis"] == (
            "built_with_model_package"
        )
        assert _sim_api_routes_both_area_types(release)
        manifest = CountryReleaseManifest.model_validate(release)
        assert manifest.regional_certification is not None
        assert manifest.regional_certification.built_with_model_version == "2.120.0"
        mismatch = [w for w in result.warnings if "accepted mismatch" in w]
        assert len(mismatch) == 1 and "2.120.0" in mismatch[0]

    def test__given_a_covering_regional_release__then_an_accepted_mismatch_refuses(
        self, tmp_path
    ):
        with pytest.raises(CertificationError, match="drop --accept-regional"):
            _certify_uk(
                _tmp_bundle(tmp_path),
                [
                    _response(_microcosm_uk_national_payload()),
                    _response(_microcosm_uk_dense_payload()),
                ],
                regional_manifest_uri=UK_DENSE_URI,
                regional_model_mismatch_reason="not needed",
            )

    @pytest.mark.parametrize("reason", ["", "   "])
    def test__given_an_empty_reason__then_refuses(self, tmp_path, reason):
        with pytest.raises(CertificationError, match="needs a reason"):
            _certify_uk(
                _tmp_bundle(tmp_path),
                [
                    _response(_microcosm_uk_national_payload()),
                    _response(self._older_dense()),
                ],
                regional_manifest_uri=UK_DENSE_URI,
                regional_model_mismatch_reason=reason,
            )

    def test__given_an_accepted_mismatch__then_the_core_must_still_be_covered(
        self, tmp_path
    ):
        from tests.test_regional_input_evidence import input_evidence

        national = _microcosm_uk_national_payload()
        national["compatible_core_packages"] = [
            {"name": "policyengine-core", "specifier": "==3.33.0"}
        ]
        with pytest.raises(
            CertificationError, match="Regional release .*policyengine-core 3.33.0"
        ):
            _certify_uk(
                _tmp_bundle(tmp_path),
                [_response(national), _response(self._older_dense())],
                regional_manifest_uri=UK_DENSE_URI,
                regional_model_mismatch_reason="area receipts are uncertified",
                regional_input_surface_evidence=input_evidence(self._older_dense()),
                core_version="3.33.0",
            )

    def test__given_an_accepted_mismatch_without_a_regional_release__then_refuses(
        self, tmp_path
    ):
        with pytest.raises(CertificationError, match="pass --regional-manifest-uri"):
            _certify_uk(
                _tmp_bundle(tmp_path),
                [_response(_microcosm_uk_national_payload())],
                drop_regional_release=True,
                regional_model_mismatch_reason="area receipts are uncertified",
            )

    def test__given_bundle_wrapper_accepted_mismatch__then_forwards_it(
        self, monkeypatch
    ):
        bundle_script = _load_bundle_script(monkeypatch)
        captured: dict[str, list[str]] = {}
        fake = ModuleType("certify_data_release")

        def fake_main(argv):
            captured["argv"] = argv
            return 0

        fake.main = fake_main
        monkeypatch.setitem(sys.modules, "certify_data_release", fake)
        reason = "area receipts are uncertified"
        assert (
            bundle_script.main(
                [
                    "certify-data",
                    "--country",
                    "uk",
                    "--manifest-uri",
                    UK_NATIONAL_URI,
                    "--regional-manifest-uri",
                    UK_DENSE_URI,
                    "--accept-regional-model-mismatch",
                    reason,
                    "--regional-input-surface-evidence",
                    "regional-audit.json",
                ]
            )
            == 0
        )
        argv = captured["argv"]
        assert argv[argv.index("--accept-regional-model-mismatch") + 1] == reason
        assert (
            argv[argv.index("--regional-input-surface-evidence") + 1]
            == "regional-audit.json"
        )

    def test__given_bundle_wrapper_empty_reason__then_certifier_refuses_it(
        self, monkeypatch, tmp_path, capsys
    ):
        bundle_script = _load_bundle_script(monkeypatch)
        spec = importlib.util.spec_from_file_location(
            "certify_data_release",
            Path(__file__).resolve().parents[1] / "scripts" / "certify_data_release.py",
        )
        certifier = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(certifier)
        monkeypatch.setitem(sys.modules, "certify_data_release", certifier)
        bundle_path = _tmp_bundle(tmp_path)
        original_bundle = bundle_path.read_bytes()
        captured = {}

        def certify_temporary_bundle(**kwargs):
            captured.update(kwargs)
            kwargs["bundle_path"] = bundle_path
            return certify_data_release(**kwargs)

        monkeypatch.setattr(certifier, "certify_data_release", certify_temporary_bundle)
        with (
            patch(
                "policyengine.provenance.certification.requests.get",
                side_effect=[
                    _response(_microcosm_uk_national_payload()),
                    _response(self._older_dense()),
                ],
            ),
            pytest.raises(SystemExit) as error,
        ):
            bundle_script.main(
                [
                    "certify-data",
                    "--country",
                    "uk",
                    "--manifest-uri",
                    UK_NATIONAL_URI,
                    "--model-version",
                    UK_MODEL_VERSION,
                    "--regional-manifest-uri",
                    UK_DENSE_URI,
                    "--accept-regional-model-mismatch",
                    "",
                    "--no-generate",
                    "--no-changelog",
                    "--skip-artifact-check",
                ]
            )
        # bundle.py reports the certifier's refusal as a usage error.
        assert error.value.code == 2
        assert isinstance(error.value.__context__, CertificationError)
        assert "needs a reason" in str(error.value.__context__)
        assert capsys.readouterr().out == ""
        assert captured["regional_model_mismatch_reason"] == ""
        assert bundle_path.read_bytes() == original_bundle

    def test__given_pinned_core__then_the_regional_release_must_cover_it(
        self, tmp_path
    ):
        # A qualified pair names the primary release only, so the regional
        # release covers the pinned core by its own build or claims.
        national = _microcosm_uk_national_payload()
        national["compatible_core_packages"] = [
            {"name": "policyengine-core", "specifier": "==3.33.0"}
        ]

        with pytest.raises(
            CertificationError, match="Regional release .*policyengine-core 3.33.0"
        ):
            _certify_uk(
                _tmp_bundle(tmp_path),
                [_response(national), _response(_efrs_release_payload())],
                regional_manifest_uri=EFRS_URI,
                regional_release_kind="area_coded_national",
                core_version="3.33.0",
            )

        efrs = _efrs_release_payload()
        efrs["compatible_core_packages"] = [
            {"name": "policyengine-core", "specifier": "==3.33.0"}
        ]
        bundle_path = _tmp_bundle(tmp_path)
        _certify_uk(
            bundle_path,
            [_response(national), _response(efrs)],
            regional_manifest_uri=EFRS_URI,
            regional_release_kind="area_coded_national",
            core_version="3.33.0",
        )
        release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
        assert release["certification"]["certified_for_core_version"] == "3.33.0"
        assert release["certification"]["core_binding"] == "certified"
        assert release["regional_release_kind"] == "area_coded_national"

    def test__given_no_core_version__then_the_certificate_follows_the_pin_openly(
        self, tmp_path
    ):
        """Without --core-version the certificate follows the bundle's core pin.

        It says so (core_binding bundle_pin), and certification reports a
        release that does not claim the pin instead of refusing it.
        """
        national = _microcosm_uk_national_payload()
        national["compatible_core_packages"] = [
            {"name": "policyengine-core", "specifier": "==3.33.3"}
        ]
        bundle_path = _tmp_bundle(tmp_path)
        bundle = json.loads(bundle_path.read_text())
        bundle["packages"]["policyengine-core"] = {
            "name": "policyengine-core",
            "version": "3.33.3",
        }
        bundle_path.write_text(json.dumps(bundle))

        result = _certify_uk(
            bundle_path,
            [_response(national), _response(_microcosm_uk_dense_payload())],
            regional_manifest_uri=UK_DENSE_URI,
        )

        written = json.loads(bundle_path.read_text())
        certification = written["data_releases"]["uk"]["certification"]
        assert certification["core_binding"] == "bundle_pin"
        assert "certified_for_core_version" not in certification
        assert written["packages"]["policyengine-core"]["version"] == "3.33.3"
        # The national release claims the pin; the local-area one claims no core.
        unclaimed = [w for w in result.warnings if "follows the core pin" in w]
        assert len(unclaimed) == 1
        assert unclaimed[0].startswith("regional release: ")

    def test__given_unreachable_regional_artifact__then_refuses(self, tmp_path):
        with (
            patch(
                "policyengine.provenance.certification.requests.get",
                side_effect=[
                    _response(_microcosm_uk_national_payload()),
                    _response(_microcosm_uk_dense_payload()),
                ],
            ),
            patch(
                "policyengine.provenance.certification.head_artifact",
                side_effect=lambda artifact, token=None: (
                    artifact.path != "microcosm_uk_2024_25_dense.h5"
                ),
            ),
            pytest.raises(CertificationError, match="Regional artifact"),
        ):
            certify_data_release(
                country="uk",
                data_producer="populace",
                manifest_uri=UK_NATIONAL_URI,
                regional_manifest_uri=UK_DENSE_URI,
                model_version=UK_MODEL_VERSION,
                bundle_path=_tmp_bundle(tmp_path),
            )

    def test__given_routed_bundle__then_recertifying_without_regional_refuses(
        self, tmp_path
    ):
        bundle_path = _tmp_bundle(tmp_path)
        _certify_uk(
            bundle_path,
            [
                _response(_microcosm_uk_national_payload()),
                _response(_microcosm_uk_dense_payload()),
            ],
            regional_manifest_uri=UK_DENSE_URI,
        )

        with pytest.raises(CertificationError, match="--drop-regional-release"):
            _certify_uk(bundle_path, [_response(_microcosm_uk_national_payload())])

        _certify_uk(
            bundle_path,
            [_response(_microcosm_uk_national_payload())],
            drop_regional_release=True,
        )
        release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
        assert "regional_source_manifest_uri" not in release
        assert "regional_release_kind" not in release
        assert set(release["region_datasets"]) == {"national"}

    def test__given_a_rollback_to_overlaid_names__then_their_overlays_go(
        self, tmp_path
    ):
        """A rollback certifies names the bundle keeps as overlays.

        Overlays may not shadow certified names, so a bundle that kept them
        would refuse every release-manifest read, and import with it.
        """
        bundle_path = _tmp_bundle(tmp_path)
        _certify_uk(
            bundle_path,
            [
                _response(_microcosm_uk_national_payload()),
                _response(_microcosm_uk_dense_payload()),
            ],
            regional_manifest_uri=UK_DENSE_URI,
        )
        bundle = json.loads(bundle_path.read_text())
        kept = {"path": "populace_uk_2023.h5", "repo_id": "x", "revision": "r"}
        bundle["dataset_overlays"] = {
            "uk": {
                "enhanced_frs_2024_25": {"path": "enhanced_frs_2024_25.h5"},
                "frs_2024_25": {"path": "frs_2024_25.h5"},
                "populace_uk_2023": kept,
            }
        }
        bundle_path.write_text(json.dumps(bundle))

        result = _certify_uk(
            bundle_path,
            [_response(_efrs_release_payload())],
            manifest_uri=EFRS_URI,
            drop_regional_release=True,
        )

        bundle = json.loads(bundle_path.read_text())
        assert bundle["data_releases"]["uk"]["default_dataset"] == (
            "enhanced_frs_2024_25"
        )
        assert bundle["dataset_overlays"]["uk"] == {"populace_uk_2023": kept}
        assert any("enhanced_frs_2024_25, frs_2024_25" in w for w in result.warnings)
        # The Microcosm names stop resolving, and certification says so.
        dropped = next(w for w in result.warnings if "no longer resolve" in w)
        assert "microcosm_uk_2024_25_dense" in dropped
        manifest = CountryReleaseManifest.model_validate(
            _apply_dataset_overlays("uk", bundle["data_releases"]["uk"], bundle)
        )
        assert "populace_uk_2023" in manifest.datasets

    def test__given_drop_and_a_regional_release__then_refuses_both(self, tmp_path):
        # Dropping the routing and routing to a release are opposite requests;
        # neither silently wins.
        with (
            patch(
                "policyengine.provenance.certification.requests.get",
                side_effect=AssertionError("no fetch"),
            ),
            pytest.raises(CertificationError, match="cannot be combined"),
        ):
            certify_data_release(
                country="uk",
                data_producer="populace",
                manifest_uri=UK_NATIONAL_URI,
                regional_manifest_uri=UK_DENSE_URI,
                drop_regional_release=True,
                model_version=UK_MODEL_VERSION,
                bundle_path=_tmp_bundle(tmp_path),
            )

    def test__given_bundle_wrapper_regional_kind__then_forwards_to_certifier(
        self, monkeypatch
    ):
        bundle_script = _load_bundle_script(monkeypatch)
        captured: dict[str, list[str]] = {}
        fake = ModuleType("certify_data_release")

        def fake_main(argv):
            captured["argv"] = argv
            return 0

        fake.main = fake_main
        monkeypatch.setitem(sys.modules, "certify_data_release", fake)

        assert (
            bundle_script.main(
                [
                    "certify-data",
                    "--country",
                    "uk",
                    "--manifest-uri",
                    UK_NATIONAL_URI,
                    "--regional-manifest-uri",
                    EFRS_URI,
                    "--regional-release-kind",
                    "area_coded_national",
                    "--drop-regional-release",
                ]
            )
            == 0
        )
        argv = captured["argv"]
        assert argv[argv.index("--regional-release-kind") + 1] == (
            "area_coded_national"
        )
        assert "--drop-regional-release" in argv
