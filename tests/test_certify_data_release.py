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
    merge_us_state_release_manifest,
    parse_manifest_uri,
    validate_release_manifest,
)
from policyengine.provenance.manifest import DataReleaseManifest

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

        assert basis == "compatible_model_packages"
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

    def test__given_us_regional_manifest__then_validates_but_does_not_vendor_state_artifacts(
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
            _state_release_manifest_payload()
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
                regional_manifest_uri=US_DATA_MANIFEST_URI,
                model_version="1.723.0",
                bundle_path=bundle_path,
            )

        written = json.loads(bundle_path.read_text())
        release = written["data_releases"]["us"]
        assert release["source_manifest_uri"] == MANIFEST_URI
        assert release["regional_source_manifest_uri"] == US_DATA_MANIFEST_URI
        assert release["region_datasets"] == {
            "national": {"path_template": "populace_us_2024.h5"}
        }
        assert "states/CA" not in release["datasets"]
        assert result.dataset_count == 4

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
