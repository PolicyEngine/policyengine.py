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

    def test__given_region_templates__then_carried_through(self):
        payload = self._payload()

        assert payload["region_datasets"]["state"] == {
            "path_template": "states/{state_code}.h5"
        }

    def test__given_build_provenance__then_certification_carries_it(self):
        payload = self._payload()

        certification = payload["certification"]
        assert certification["compatibility_basis"] == "built_with_model_package"
        assert certification["certified_by"] == "policyengine.py certification"
        assert certification["data_build_id"] == TAG
        assert certification["built_with_model_version"] == "1.723.0"
        assert certification["built_with_model_git_sha"] == "deadbeef"
        assert payload["certified_data_artifact"]["build_id"] == TAG
        assert payload["certified_data_artifact"]["uri"] == (
            f"hf://policyengine/populace-us/populace_us_2024.h5@{TAG}"
        )


class TestCertifyDataRelease:
    def test__given_fetched_manifest__then_writes_country_manifest(self, tmp_path):
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
        ):
            result = certify_data_release(
                country="us",
                manifest_uri=MANIFEST_URI,
                model_version="1.723.0",
                output_dir=tmp_path,
            )

        written = json.loads((tmp_path / "us.json").read_text())
        assert written["default_dataset"] == "populace_us_2024"
        assert written["certification"]["data_build_id"] == TAG
        assert result.dataset_count == 2
        assert result.build_id == TAG

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
                manifest_uri=MANIFEST_URI,
                model_version="1.723.0",
                output_dir=tmp_path,
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
            pytest.raises(CertificationError, match="not reachable"),
        ):
            certify_data_release(
                country="us",
                manifest_uri=MANIFEST_URI,
                model_version="1.723.0",
                output_dir=tmp_path,
            )


class TestVendoredSidecarBinding:
    def test__given_vendored_us_manifest__then_tro_sidecar_binds_it(self):
        """The shipped TRO must bind the shipped country manifest under the
        canonical-model convention used by build_trace_tro_from_release_bundle."""
        import hashlib
        from importlib.resources import files

        from policyengine.provenance.manifest import CountryReleaseManifest
        from policyengine.provenance.trace import canonical_json_bytes

        manifest_dir = files("policyengine").joinpath("data/release_manifests")
        manifest_text = manifest_dir.joinpath("us.json").read_text()
        country_manifest = CountryReleaseManifest.model_validate_json(manifest_text)
        expected = hashlib.sha256(
            canonical_json_bytes(country_manifest.model_dump(mode="json"))
        ).hexdigest()

        tro = json.loads(manifest_dir.joinpath("us.trace.tro.jsonld").read_text())
        artifacts = tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
        bundle_manifest = next(
            a for a in artifacts if a["@id"].endswith("bundle_manifest")
        )

        assert bundle_manifest["trov:sha256"] == expected
