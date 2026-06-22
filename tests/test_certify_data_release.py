"""Tests for direct data-release certification."""

import json
from unittest.mock import MagicMock, patch

import pytest

from policyengine.provenance.certification import (
    CertificationError,
    build_country_manifest_payload,
    certify_data_release,
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
        },
    }


def _manifest() -> DataReleaseManifest:
    return DataReleaseManifest.model_validate(_release_manifest_payload())


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
    return payload


def _bundle_source_payload() -> dict:
    return {
        "schema_version": 2,
        "bundle_version": "9.9.9",
        "policyengine_version": "9.9.9",
        "packages": {
            "policyengine": {"name": "policyengine", "version": "9.9.9"},
            "policyengine-uk": {"name": "policyengine-uk", "version": "2.0.0"},
        },
        "extras": {},
        "countries": {"uk": {"model_package": "policyengine-uk"}},
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

    def test__given_inherited_artifact__then_keeps_its_repo_pin(self):
        payload = self._payload()

        assert payload["datasets"]["states/AK"] == {
            "path": "states/AK.h5",
            "revision": "1.115.5",
            "sha256": "b" * 64,
            "repo_id": "policyengine/policyengine-us-data",
        }

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

    def test__given_region_templates__then_carried_through(self):
        payload = self._payload()

        assert payload["region_datasets"]["state"] == {
            "path_template": "states/{state_code}.h5"
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


class TestCertifyDataRelease:
    def test__given_fetched_populace_manifest__then_updates_bundle_source(
        self, tmp_path
    ):
        bundle_path = tmp_path / "policyengine-bundle.json"
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
        assert result.dataset_count == 4
        assert result.build_id == UK_TAG
        assert result.bundle_path == bundle_path

    def test__given_us_without_data_producer__then_legacy_update_is_explicitly_unsupported(
        self, tmp_path
    ):
        bundle_path = tmp_path / "policyengine-bundle.json"
        bundle_path.write_text(json.dumps(_bundle_source_payload()) + "\n")

        with pytest.raises(CertificationError, match="Legacy data-producer"):
            certify_data_release(
                country="us",
                manifest_uri=MANIFEST_URI,
                model_version="1.723.0",
                bundle_path=bundle_path,
            )

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
