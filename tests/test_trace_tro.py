"""Tests for TRACE Transparent Research Object (TRO) export.

Covers bundle-level TROs (``policyengine.core.trace_tro``) and per-simulation
TROs (``policyengine.results.trace_tro``), plus the ``policyengine trace-tro``
CLI and JSON-Schema conformance.
"""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import Draft202012Validator

from policyengine.cli import main as cli_main
from policyengine.core.release_manifest import (
    DataReleaseManifest,
    get_data_release_manifest,
    get_release_manifest,
)
from policyengine.core.tax_benefit_model import TaxBenefitModel
from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion
from policyengine.core.trace_tro import (
    POLICYENGINE_ORGANIZATION,
    TRACE_TROV_VERSION,
    build_trace_tro_from_release_bundle,
    compute_trace_composition_fingerprint,
    extract_bundle_tro_reference,
    serialize_trace_tro,
)
from policyengine.results import (
    ResultsJson,
    ResultsMetadata,
    ValueEntry,
    build_results_trace_tro,
    write_results_with_trace_tro,
)

FAKE_WHEEL_SHA = "a" * 64
FAKE_WHEEL_URL = (
    "https://files.pythonhosted.org/packages/ab/cd/"
    "policyengine_us-1.647.0-py3-none-any.whl"
)


def _fake_fetch_pypi(name: str, version: str) -> dict:
    return {"sha256": FAKE_WHEEL_SHA, "url": FAKE_WHEEL_URL}


def _us_data_release_manifest(
    sha256: str = "c" * 64,
    data_build_fingerprint: str = "sha256:build",
) -> DataReleaseManifest:
    return DataReleaseManifest.model_validate(
        {
            "schema_version": 1,
            "data_package": {
                "name": "policyengine-us-data",
                "version": "1.73.0",
            },
            "build": {
                "build_id": "policyengine-us-data-1.73.0",
                "built_at": "2026-04-10T12:00:00Z",
                "built_with_model_package": {
                    "name": "policyengine-us",
                    "version": "1.647.0",
                    "git_sha": "deadbeef",
                    "data_build_fingerprint": data_build_fingerprint,
                },
            },
            "compatible_model_packages": [],
            "default_datasets": {"national": "enhanced_cps_2024"},
            "artifacts": {
                "enhanced_cps_2024": {
                    "kind": "microdata",
                    "path": "enhanced_cps_2024.h5",
                    "repo_id": "policyengine/policyengine-us-data",
                    "revision": "1.73.0",
                    "sha256": sha256,
                    "size_bytes": 123,
                }
            },
        }
    )


@pytest.fixture
def tro_schema() -> dict:
    schema_path = Path(
        str(files("policyengine").joinpath("data", "schemas", "trace_tro.schema.json"))
    )
    return json.loads(schema_path.read_text())


@pytest.fixture(autouse=True)
def clear_manifest_caches():
    yield
    get_release_manifest.cache_clear()
    get_data_release_manifest.cache_clear()


class TestBundleTRO:
    """Bundle-level TRACE TRO emission."""

    def test__given_us_bundle__then_schema_creator_is_policyengine_organization(
        self,
    ):
        country_manifest = get_release_manifest("us")

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=_fake_fetch_pypi,
        )

        assert tro["@graph"][0]["schema:creator"] == POLICYENGINE_ORGANIZATION

    def test__given_us_bundle__then_model_wheel_is_hashed_as_artifact(self):
        country_manifest = get_release_manifest("us")

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=_fake_fetch_pypi,
        )

        artifacts = tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
        wheel_artifacts = [a for a in artifacts if a["@id"].endswith("model_wheel")]
        assert len(wheel_artifacts) == 1
        assert wheel_artifacts[0]["trov:hash"]["trov:hashValue"] == FAKE_WHEEL_SHA
        locations = tro["@graph"][0]["trov:hasArrangement"][0][
            "trov:hasArtifactLocation"
        ]
        wheel_location = next(
            location
            for location in locations
            if location["@id"].endswith("model_wheel")
        )
        assert wheel_location["trov:path"] == FAKE_WHEEL_URL

    def test__given_manifest_sha__then_pypi_not_fetched(self):
        country_manifest = get_release_manifest("us")
        country_manifest.model_package.sha256 = "b" * 64
        country_manifest.model_package.wheel_url = "https://example/wheel.whl"
        fetch_pypi = MagicMock()

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=fetch_pypi,
        )

        artifacts = tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
        wheel_artifacts = [a for a in artifacts if a["@id"].endswith("model_wheel")]
        assert wheel_artifacts[0]["trov:hash"]["trov:hashValue"] == "b" * 64
        fetch_pypi.assert_not_called()

    def test__given_pypi_unreachable__then_wheel_artifact_is_skipped(self):
        country_manifest = get_release_manifest("us")
        country_manifest.model_package.sha256 = None
        country_manifest.model_package.wheel_url = None

        def failing_fetch(name, version):
            raise RuntimeError("PyPI unreachable")

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=failing_fetch,
        )

        artifact_ids = [
            a["@id"]
            for a in tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
        ]
        assert not any(aid.endswith("model_wheel") for aid in artifact_ids)

    def test__given_artifact_locations__then_all_paths_are_https_or_local(self):
        country_manifest = get_release_manifest("us")

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=_fake_fetch_pypi,
        )

        locations = tro["@graph"][0]["trov:hasArrangement"][0][
            "trov:hasArtifactLocation"
        ]
        paths = [location["trov:path"] for location in locations]
        # Bundle manifest is a local wheel-internal path; everything else must
        # be dereferenceable HTTPS so a reproducibility reviewer can fetch it.
        assert paths[0].startswith("data/release_manifests/")
        for path in paths[1:]:
            assert path.startswith("https://"), path

    def test__given_certification__then_fields_are_machine_readable(self):
        country_manifest = get_release_manifest("us")

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=_fake_fetch_pypi,
        )

        performance = tro["@graph"][0]["trov:hasPerformance"][0]
        assert (
            performance["pe:certifiedForModelVersion"]
            == country_manifest.certification.certified_for_model_version
        )
        assert (
            performance["pe:compatibilityBasis"]
            == country_manifest.certification.compatibility_basis
        )
        assert (
            performance["pe:builtWithModelVersion"]
            == country_manifest.certification.built_with_model_version
        )
        assert (
            performance["pe:dataBuildId"]
            == country_manifest.certification.data_build_id
        )

    def test__given_github_actions_env__then_ci_attestation_is_included(
        self, monkeypatch
    ):
        country_manifest = get_release_manifest("us")
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
        monkeypatch.setenv("GITHUB_REPOSITORY", "PolicyEngine/policyengine.py")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")
        monkeypatch.setenv("GITHUB_SHA", "abc123")

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=_fake_fetch_pypi,
        )

        performance = tro["@graph"][0]["trov:hasPerformance"][0]
        assert (
            performance["pe:ciRunUrl"]
            == "https://github.com/PolicyEngine/policyengine.py/actions/runs/12345"
        )
        assert performance["pe:ciGitSha"] == "abc123"

    def test__given_non_ci_env__then_no_attestation_fields(self, monkeypatch):
        country_manifest = get_release_manifest("us")
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=_fake_fetch_pypi,
        )

        performance = tro["@graph"][0]["trov:hasPerformance"][0]
        assert "pe:ciRunUrl" not in performance
        assert "pe:ciGitSha" not in performance

    def test__given_same_inputs__then_built_tros_serialize_identically(self):
        country_manifest = get_release_manifest("us")
        data = _us_data_release_manifest()

        first = serialize_trace_tro(
            build_trace_tro_from_release_bundle(
                country_manifest,
                data,
                fetch_pypi=_fake_fetch_pypi,
                ci_attestation={},
            )
        )
        second = serialize_trace_tro(
            build_trace_tro_from_release_bundle(
                country_manifest,
                data,
                fetch_pypi=_fake_fetch_pypi,
                ci_attestation={},
            )
        )
        assert first == second

    def test__given_hashes_in_any_order__then_composition_fingerprint_matches(
        self,
    ):
        hashes = ["ccc", "aaa", "bbb"]
        assert compute_trace_composition_fingerprint(
            hashes
        ) == compute_trace_composition_fingerprint(reversed(hashes))

    def test__given_generated_tro__then_validates_against_json_schema(self, tro_schema):
        country_manifest = get_release_manifest("us")

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=_fake_fetch_pypi,
        )

        errors = list(Draft202012Validator(tro_schema).iter_errors(tro))
        assert errors == [], [error.message for error in errors]

    def test__given_vocabulary_version_constant__then_matches_context_namespace(
        self,
    ):
        assert TRACE_TROV_VERSION == "0.1"

    def test__given_model_version_attribute__then_trace_tro_property_works(
        self,
    ):
        manifest = get_release_manifest("us")
        data_release_manifest = _us_data_release_manifest()
        model_version = TaxBenefitModelVersion(
            model=TaxBenefitModel(id="us"),
            version=manifest.model_package.version,
            release_manifest=manifest,
            model_package=manifest.model_package,
            data_package=manifest.data_package,
            default_dataset_uri=manifest.default_dataset_uri,
            data_certification=manifest.certification,
        )

        with patch(
            "policyengine.core.tax_benefit_model_version.get_data_release_manifest",
            return_value=data_release_manifest,
        ):
            with patch(
                "policyengine.core.trace_tro.fetch_pypi_wheel_metadata",
                side_effect=_fake_fetch_pypi,
            ):
                tro = model_version.trace_tro

        assert tro["@graph"][0]["schema:creator"] == POLICYENGINE_ORGANIZATION


class TestSimulationTRO:
    """Per-simulation TROs chained from a bundle TRO."""

    def _bundle_tro(self):
        country_manifest = get_release_manifest("us")
        return build_trace_tro_from_release_bundle(
            country_manifest,
            _us_data_release_manifest(),
            fetch_pypi=_fake_fetch_pypi,
        )

    def _results(self, **overrides):
        return ResultsJson(
            metadata=ResultsMetadata(
                title="SALT cap repeal",
                repo="PolicyEngine/analyses",
                generated_at="2026-04-18T12:00:00Z",
                **overrides,
            ),
            values={
                "budget_impact": ValueEntry(
                    value=-15200000000,
                    display="$15.2 billion",
                    source_line=47,
                    source_url="https://github.com/PolicyEngine/analyses/blob/main/salt.py#L47",
                )
            },
        )

    def test__given_bundle_and_results__then_simulation_tro_pins_both(self):
        bundle_tro = self._bundle_tro()
        results = self._results()

        tro = build_results_trace_tro(
            results,
            bundle_tro=bundle_tro,
            reform_payload={"salt_cap": 0},
            reform_name="SALT cap repeal",
        )

        artifact_ids = {
            a["@id"]
            for a in tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
        }
        assert artifact_ids == {
            "composition/1/artifact/bundle_tro",
            "composition/1/artifact/reform",
            "composition/1/artifact/results",
        }
        performance = tro["@graph"][0]["trov:hasPerformance"][0]
        assert (
            performance["pe:bundleFingerprint"]
            == extract_bundle_tro_reference(bundle_tro)["fingerprint"]
        )

    def test__given_simulation_tro__then_validates_against_json_schema(
        self, tro_schema
    ):
        tro = build_results_trace_tro(
            self._results(),
            bundle_tro=self._bundle_tro(),
            reform_payload={"salt_cap": 0},
        )

        errors = list(Draft202012Validator(tro_schema).iter_errors(tro))
        assert errors == [], [error.message for error in errors]

    def test__given_no_reform__then_only_bundle_and_results_are_pinned(self):
        tro = build_results_trace_tro(self._results(), bundle_tro=self._bundle_tro())

        artifact_ids = {
            a["@id"]
            for a in tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
        }
        assert artifact_ids == {
            "composition/1/artifact/bundle_tro",
            "composition/1/artifact/results",
        }

    def test__given_write_helper__then_results_and_tro_files_are_sidebyside(
        self, tmp_path
    ):
        written = write_results_with_trace_tro(
            self._results(),
            tmp_path / "results.json",
            bundle_tro=self._bundle_tro(),
            reform_payload={"salt_cap": 0},
        )

        assert written["results"].exists()
        assert written["tro"].exists()
        assert written["tro"].name == "results.trace.tro.jsonld"
        tro_payload = json.loads(written["tro"].read_text())
        assert tro_payload["@graph"][0]["schema:creator"] == POLICYENGINE_ORGANIZATION


class TestCLI:
    """``policyengine`` CLI entry point."""

    def test__given_trace_tro_stdout__then_writes_canonical_json(self, capsysbinary):
        data_release_manifest = _us_data_release_manifest()

        with patch(
            "policyengine.cli.get_data_release_manifest",
            return_value=data_release_manifest,
        ):
            with patch(
                "policyengine.core.trace_tro.fetch_pypi_wheel_metadata",
                side_effect=_fake_fetch_pypi,
            ):
                exit_code = cli_main(["trace-tro", "us"])

        assert exit_code == 0
        stdout = capsysbinary.readouterr().out
        payload = json.loads(stdout)
        assert payload["@graph"][0]["schema:creator"] == POLICYENGINE_ORGANIZATION
        assert payload["@graph"][0]["trov:vocabularyVersion"] == TRACE_TROV_VERSION

    def test__given_out_path__then_writes_to_file(self, tmp_path):
        out = tmp_path / "nested" / "us.trace.tro.jsonld"
        data_release_manifest = _us_data_release_manifest()

        with patch(
            "policyengine.cli.get_data_release_manifest",
            return_value=data_release_manifest,
        ):
            with patch(
                "policyengine.core.trace_tro.fetch_pypi_wheel_metadata",
                side_effect=_fake_fetch_pypi,
            ):
                exit_code = cli_main(["trace-tro", "us", "--out", str(out)])

        assert exit_code == 0
        assert out.exists()
        payload = json.loads(out.read_text())
        assert payload["@graph"][0]["trov:vocabularyVersion"] == "0.1"

    def test__given_release_manifest_command__then_prints_bundle(self, capsys):
        exit_code = cli_main(["release-manifest", "us"])

        assert exit_code == 0
        stdout = capsys.readouterr().out
        payload = json.loads(stdout)
        assert payload["country_id"] == "us"
