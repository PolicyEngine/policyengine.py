"""Tests for TRACE Transparent Research Object (TRO) export.

Covers bundle-level TROs (``policyengine.core.trace_tro``) and per-simulation
TROs (``policyengine.results.trace_tro``), plus the ``policyengine trace-tro``
CLI, determinism guarantees, and JSON-Schema conformance against TROv 2023/05.
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
    TRACE_TROV_NAMESPACE,
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


@pytest.fixture
def us_bundle_tro(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    return build_trace_tro_from_release_bundle(
        get_release_manifest("us"),
        _us_data_release_manifest(),
        fetch_pypi=_fake_fetch_pypi,
    )


@pytest.fixture(autouse=True)
def clear_manifest_caches():
    yield
    get_release_manifest.cache_clear()
    get_data_release_manifest.cache_clear()


class TestBundleTRO:
    """Bundle-level TRACE TRO emission."""

    def test__given_context__then_uses_public_trov_namespace(self, us_bundle_tro):
        context = us_bundle_tro["@context"][0]
        assert context["trov"] == TRACE_TROV_NAMESPACE
        assert context["trov"] == "https://w3id.org/trace/2023/05/trov#"

    def test__given_root_type__then_is_single_transparent_research_object(
        self, us_bundle_tro
    ):
        node = us_bundle_tro["@graph"][0]
        assert node["@type"] == "trov:TransparentResearchObject"

    def test__given_trs__then_is_transparent_research_system(self, us_bundle_tro):
        trs = us_bundle_tro["@graph"][0]["trov:wasAssembledBy"]
        assert trs["@type"] == "trov:TransparentResearchSystem"

    def test__given_performance__then_is_transparent_research_performance(
        self, us_bundle_tro
    ):
        performance = us_bundle_tro["@graph"][0]["trov:hasPerformance"]
        assert performance["@type"] == "trov:TransparentResearchPerformance"
        assert performance["trov:accessedArrangement"]["@id"] == "arrangement/1"

    def test__given_artifacts__then_use_flat_trov_sha256(self, us_bundle_tro):
        artifacts = us_bundle_tro["@graph"][0]["trov:hasComposition"][
            "trov:hasArtifact"
        ]
        for artifact in artifacts:
            assert "trov:sha256" in artifact
            assert "trov:hash" not in artifact
            assert len(artifact["trov:sha256"]) == 64

    def test__given_locations__then_use_has_location_and_has_artifact(
        self, us_bundle_tro
    ):
        locations = us_bundle_tro["@graph"][0]["trov:hasArrangement"][0][
            "trov:hasArtifactLocation"
        ]
        for location in locations:
            assert "trov:hasLocation" in location
            assert "trov:path" not in location
            assert "trov:hasArtifact" in location
            assert "trov:artifact" not in location

    def test__given_creator__then_is_policyengine_organization(self, us_bundle_tro):
        assert us_bundle_tro["@graph"][0]["schema:creator"] == POLICYENGINE_ORGANIZATION

    def test__given_us_bundle__then_model_wheel_hash_is_included(self, us_bundle_tro):
        country_manifest = get_release_manifest("us")
        artifacts = us_bundle_tro["@graph"][0]["trov:hasComposition"][
            "trov:hasArtifact"
        ]
        wheels = [a for a in artifacts if a["@id"].endswith("model_wheel")]
        assert len(wheels) == 1
        # us.json pins the wheel sha directly so PyPI is not consulted.
        assert wheels[0]["trov:sha256"] == country_manifest.model_package.sha256
        locations = us_bundle_tro["@graph"][0]["trov:hasArrangement"][0][
            "trov:hasArtifactLocation"
        ]
        wheel_loc = next(loc for loc in locations if loc["@id"].endswith("model_wheel"))
        assert wheel_loc["trov:hasLocation"] == country_manifest.model_package.wheel_url

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
        wheels = [a for a in artifacts if a["@id"].endswith("model_wheel")]
        assert wheels[0]["trov:sha256"] == "b" * 64
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

    def test__given_manifest_dataset_sha__then_data_release_sha_not_required(self):
        country_manifest = get_release_manifest("us")
        country_manifest.certified_data_artifact.sha256 = "d" * 64
        data_release_manifest = _us_data_release_manifest(sha256=None)

        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            data_release_manifest,
            fetch_pypi=_fake_fetch_pypi,
        )

        artifacts = tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
        dataset = next(a for a in artifacts if a["@id"].endswith("dataset"))
        assert dataset["trov:sha256"] == "d" * 64

    def test__given_artifact_locations__then_all_paths_are_https_or_local(
        self, us_bundle_tro
    ):
        locations = us_bundle_tro["@graph"][0]["trov:hasArrangement"][0][
            "trov:hasArtifactLocation"
        ]
        paths = [location["trov:hasLocation"] for location in locations]
        assert paths[0].startswith("data/release_manifests/")
        for path in paths[1:]:
            assert path.startswith("https://"), path

    def test__given_certification__then_fields_are_machine_readable(
        self, us_bundle_tro
    ):
        country_manifest = get_release_manifest("us")
        performance = us_bundle_tro["@graph"][0]["trov:hasPerformance"]
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

    def test__given_github_actions_env__then_emitted_in_is_ci(self, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
        monkeypatch.setenv("GITHUB_REPOSITORY", "PolicyEngine/policyengine.py")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")
        monkeypatch.setenv("GITHUB_SHA", "abc123")

        tro = build_trace_tro_from_release_bundle(
            get_release_manifest("us"),
            _us_data_release_manifest(),
            fetch_pypi=_fake_fetch_pypi,
        )

        performance = tro["@graph"][0]["trov:hasPerformance"]
        assert performance["pe:emittedIn"] == "github-actions"
        assert (
            performance["pe:ciRunUrl"]
            == "https://github.com/PolicyEngine/policyengine.py/actions/runs/12345"
        )
        assert performance["pe:ciGitSha"] == "abc123"

    def test__given_no_ci_env__then_emitted_in_is_local(
        self, monkeypatch, us_bundle_tro
    ):
        performance = us_bundle_tro["@graph"][0]["trov:hasPerformance"]
        assert performance["pe:emittedIn"] == "local"
        assert "pe:ciRunUrl" not in performance
        assert "pe:ciGitSha" not in performance

    def test__given_fresh_manifest_instances__then_tro_bytes_match(self, monkeypatch):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        first = serialize_trace_tro(
            build_trace_tro_from_release_bundle(
                get_release_manifest("us"),
                _us_data_release_manifest(),
                fetch_pypi=_fake_fetch_pypi,
            )
        )
        get_release_manifest.cache_clear()
        second = serialize_trace_tro(
            build_trace_tro_from_release_bundle(
                get_release_manifest("us"),
                _us_data_release_manifest(),
                fetch_pypi=_fake_fetch_pypi,
            )
        )
        assert first == second

    def test__given_hashes_in_any_order__then_fingerprint_matches(self):
        hashes = ["c" * 64, "a" * 64, "b" * 64]
        assert compute_trace_composition_fingerprint(
            hashes
        ) == compute_trace_composition_fingerprint(reversed(hashes))

    def test__given_hex_length_ambiguity__then_separator_prevents_collision(self):
        assert compute_trace_composition_fingerprint(
            ["ab", "cdef"]
        ) != compute_trace_composition_fingerprint(["abcd", "ef"])

    def test__given_generated_tro__then_validates_against_json_schema(
        self, tro_schema, us_bundle_tro
    ):
        errors = list(Draft202012Validator(tro_schema).iter_errors(us_bundle_tro))
        assert errors == [], [error.message for error in errors]

    def test__given_non_https_location__then_schema_rejects(self, tro_schema):
        # Schema must catch the "non-HTTPS artifact locations" claim in the docs.
        bad = {
            "@context": [
                {
                    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                    "trov": TRACE_TROV_NAMESPACE,
                    "schema": "https://schema.org/",
                    "pe": "https://policyengine.org/trace/0.1#",
                }
            ],
            "@graph": [
                {
                    "@id": "tro",
                    "@type": "trov:TransparentResearchObject",
                    "schema:name": "bad",
                    "schema:creator": POLICYENGINE_ORGANIZATION,
                    "trov:wasAssembledBy": {
                        "@id": "trs",
                        "@type": "trov:TransparentResearchSystem",
                        "schema:name": "x",
                    },
                    "trov:hasComposition": {
                        "@id": "composition/1",
                        "@type": "trov:ArtifactComposition",
                        "trov:hasFingerprint": {
                            "@id": "fp",
                            "@type": "trov:CompositionFingerprint",
                            "trov:sha256": "a" * 64,
                        },
                        "trov:hasArtifact": [
                            {
                                "@id": "composition/1/artifact/1",
                                "@type": "trov:ResearchArtifact",
                                "trov:sha256": "a" * 64,
                            }
                        ],
                    },
                    "trov:hasArrangement": [
                        {
                            "@id": "arrangement/1",
                            "@type": "trov:ArtifactArrangement",
                            "trov:hasArtifactLocation": [
                                {
                                    "@id": "arrangement/1/location/1",
                                    "@type": "trov:ArtifactLocation",
                                    "trov:hasArtifact": {
                                        "@id": "composition/1/artifact/1"
                                    },
                                    "trov:hasLocation": "file:///tmp/leak.h5",
                                }
                            ],
                        }
                    ],
                    "trov:hasPerformance": {
                        "@id": "trp/1",
                        "@type": "trov:TransparentResearchPerformance",
                        "trov:wasConductedBy": {"@id": "trs"},
                        "trov:accessedArrangement": {"@id": "arrangement/1"},
                        "pe:emittedIn": "local",
                    },
                }
            ],
        }
        errors = list(Draft202012Validator(tro_schema).iter_errors(bad))
        assert errors, "schema must reject file:// locations"

    def test__given_trace_tro_property__then_emits_valid_tro(self):
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

    def test__given_bundle_and_results__then_simulation_tro_pins_both(
        self, us_bundle_tro
    ):
        tro = build_results_trace_tro(
            self._results(),
            bundle_tro=us_bundle_tro,
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
        performance = tro["@graph"][0]["trov:hasPerformance"]
        assert (
            performance["pe:bundleFingerprint"]
            == extract_bundle_tro_reference(us_bundle_tro)["fingerprint"]
        )

    def test__given_simulation_tro__then_validates_against_json_schema(
        self, tro_schema, us_bundle_tro
    ):
        tro = build_results_trace_tro(
            self._results(),
            bundle_tro=us_bundle_tro,
            reform_payload={"salt_cap": 0},
        )
        errors = list(Draft202012Validator(tro_schema).iter_errors(tro))
        assert errors == [], [error.message for error in errors]

    def test__given_no_reform__then_only_bundle_and_results_are_pinned(
        self, us_bundle_tro
    ):
        tro = build_results_trace_tro(self._results(), bundle_tro=us_bundle_tro)
        artifact_ids = {
            a["@id"]
            for a in tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
        }
        assert artifact_ids == {
            "composition/1/artifact/bundle_tro",
            "composition/1/artifact/results",
        }

    def test__given_bundle_tro_url__then_performance_records_it(self, us_bundle_tro):
        tro = build_results_trace_tro(
            self._results(),
            bundle_tro=us_bundle_tro,
            bundle_tro_url="https://raw.githubusercontent.com/PolicyEngine/policyengine.py/v3.4.5/src/policyengine/data/release_manifests/us.trace.tro.jsonld",
        )

        performance = tro["@graph"][0]["trov:hasPerformance"]
        assert performance["pe:bundleTroUrl"].startswith(
            "https://raw.githubusercontent.com/PolicyEngine/policyengine.py/"
        )
        locations = tro["@graph"][0]["trov:hasArrangement"][0][
            "trov:hasArtifactLocation"
        ]
        bundle_location = next(
            loc for loc in locations if loc["@id"].endswith("bundle_tro")
        )
        assert bundle_location["trov:hasLocation"].startswith("https://")

    def test__given_forged_bundle_tro__then_hash_changes_in_sim_tro(
        self, us_bundle_tro
    ):
        # If the caller swaps the bundle TRO, the artifact hash in the sim TRO
        # changes, so a verifier that re-fetches from pe:bundleTroUrl will
        # detect the swap.
        original = build_results_trace_tro(self._results(), bundle_tro=us_bundle_tro)
        forged_bundle = json.loads(json.dumps(us_bundle_tro))
        forged_bundle["@graph"][0]["schema:description"] = "forged"
        forged = build_results_trace_tro(self._results(), bundle_tro=forged_bundle)

        def bundle_hash(tro):
            return next(
                a["trov:sha256"]
                for a in tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
                if a["@id"].endswith("bundle_tro")
            )

        assert bundle_hash(original) != bundle_hash(forged)

    def test__given_write_helper__then_results_and_tro_files_are_sidebyside(
        self, tmp_path, us_bundle_tro
    ):
        written = write_results_with_trace_tro(
            self._results(),
            tmp_path / "results.json",
            bundle_tro=us_bundle_tro,
            reform_payload={"salt_cap": 0},
        )

        assert written["results"].exists()
        assert written["tro"].exists()
        assert written["tro"].name == "results.trace.tro.jsonld"
        tro_payload = json.loads(written["tro"].read_text())
        assert tro_payload["@graph"][0]["schema:creator"] == POLICYENGINE_ORGANIZATION


class TestCLI:
    """``policyengine`` CLI entry point."""

    def test__given_trace_tro_stdout__then_writes_canonical_json(
        self, capsysbinary, monkeypatch
    ):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
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
        payload = json.loads(capsysbinary.readouterr().out)
        assert payload["@graph"][0]["schema:creator"] == POLICYENGINE_ORGANIZATION
        assert payload["@graph"][0]["trov:hasPerformance"]["pe:emittedIn"] == "local"

    def test__given_out_path__then_writes_to_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
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
        assert payload["@graph"][0]["@type"] == "trov:TransparentResearchObject"

    def test__given_release_manifest_command__then_prints_bundle(self, capsys):
        exit_code = cli_main(["release-manifest", "us"])

        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["country_id"] == "us"

    def test__given_validate_command__then_accepts_valid_tro(
        self, tmp_path, us_bundle_tro
    ):
        tro_path = tmp_path / "us.trace.tro.jsonld"
        tro_path.write_bytes(serialize_trace_tro(us_bundle_tro))

        exit_code = cli_main(["trace-tro-validate", str(tro_path)])

        assert exit_code == 0

    def test__given_validate_command__then_rejects_invalid_tro(self, tmp_path, capsys):
        bad = {"@context": [{"trov": "wrong"}], "@graph": []}
        tro_path = tmp_path / "bad.jsonld"
        tro_path.write_text(json.dumps(bad))

        exit_code = cli_main(["trace-tro-validate", str(tro_path)])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "invalid" in err.lower() or "error" in err.lower()
