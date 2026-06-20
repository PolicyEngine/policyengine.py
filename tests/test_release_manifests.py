"""Tests for bundled compatibility manifests and data release manifests."""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

from requests import Timeout

from policyengine.core.tax_benefit_model import TaxBenefitModel
from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion
from policyengine.provenance.manifest import (
    ArtifactPathReference,
    DataCertification,
    DataReleaseManifestUnavailableError,
    certify_data_release_compatibility,
    dataset_logical_name,
    get_data_release_manifest,
    get_release_manifest,
    https_release_manifest_uri,
    resolve_dataset_reference,
    resolve_local_managed_dataset_source,
    resolve_managed_dataset_reference,
)
from policyengine.tax_benefit_models.uk import (
    managed_microsimulation as managed_uk_microsimulation,
)
from policyengine.tax_benefit_models.us import (
    managed_microsimulation as managed_us_microsimulation,
)
from policyengine.tax_benefit_models.us import us_latest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
POLICYENGINE_VERSION = re.search(
    r'^version\s*=\s*"([^"]+)"',
    PYPROJECT.read_text(),
    re.MULTILINE,
).group(1)
US_MODEL_VERSION = "1.729.0"
US_BUILT_WITH_MODEL_VERSION = "1.729.0"
US_DATA_RELEASE_VERSION = "0.1.0"
US_DATA_RELEASE_ID = "populace-us-2024-f0af251-703bd81a565c-20260620T201958Z"
US_DATA_RELEASE_REVISION = US_DATA_RELEASE_ID
US_DATA_RELEASE_PATH = f"releases/{US_DATA_RELEASE_ID}/release_manifest.json"
US_DATA_ARTIFACT_REVISION = US_DATA_RELEASE_ID
US_CERTIFICATION_SOURCE = "policyengine.py certification"
US_MANAGED_DATASET_URI = (
    f"hf://policyengine/populace-us/populace_us_2024.h5@{US_DATA_ARTIFACT_REVISION}"
)
US_CERTIFIED_DATASET_URI = (
    f"hf://policyengine/populace-us/populace_us_2024.h5@{US_DATA_RELEASE_REVISION}"
)
US_RELEASE_MANIFEST_DATASET_URI = (
    f"hf://policyengine/populace-us/populace_us_2024.h5@{US_DATA_RELEASE_REVISION}"
)
UK_MODEL_VERSION = "2.89.2"
UK_BUILT_WITH_MODEL_VERSION = "2.89.2"
UK_DATA_RELEASE_VERSION = "0.1.0"
UK_DATA_RELEASE_ID = "populace-uk-2023-dd68c73-4aa4b14-20260619T023711Z"
UK_DATA_RELEASE_REVISION = UK_DATA_RELEASE_ID
UK_DATA_RELEASE_PATH = f"releases/{UK_DATA_RELEASE_ID}/release_manifest.json"
UK_CERTIFICATION_SOURCE = "policyengine.py certification"
UK_CERTIFIED_DATASET_URI = (
    f"hf://policyengine/populace-uk-private/populace_uk_2023.h5"
    f"@{UK_DATA_RELEASE_REVISION}"
)
UK_LEGACY_DATA_RELEASE_REVISION = "655dd07e4bb9c777b00dac044949611f1feb824f"
UK_LEGACY_FRS_DATASET_URI = (
    "hf://policyengine/policyengine-uk-data-private/frs_2023_24.h5"
    f"@{UK_LEGACY_DATA_RELEASE_REVISION}"
)
UK_LEGACY_ENHANCED_FRS_DATASET_URI = (
    "hf://policyengine/policyengine-uk-data-private/enhanced_frs_2023_24.h5"
    f"@{UK_LEGACY_DATA_RELEASE_REVISION}"
)


def _response_with_json(payload: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.text = json.dumps(payload)
    response.content = response.text.encode("utf-8")
    response.raise_for_status.return_value = None
    return response


def _country_module_with_microsimulation(
    name: str,
    microsimulation: MagicMock,
) -> ModuleType:
    module = ModuleType(name)
    module.Microsimulation = microsimulation
    module.__file__ = str(Path(__file__).resolve())
    return module


class TestReleaseManifests:
    """Tests for bundled country manifests."""

    def teardown_method(self):
        get_release_manifest.cache_clear()
        get_data_release_manifest.cache_clear()

    def test__given_us_manifest__then_has_pinned_model_and_data_packages(self):
        manifest = get_release_manifest("us")

        assert manifest.schema_version == 1
        assert manifest.bundle_id == f"us-{POLICYENGINE_VERSION}"
        assert manifest.country_id == "us"
        assert manifest.policyengine_version == POLICYENGINE_VERSION
        assert manifest.model_package.name == "policyengine-us"
        assert manifest.model_package.version == US_MODEL_VERSION
        assert manifest.data_package.name == "populace-data"
        assert manifest.data_package.version == US_DATA_RELEASE_VERSION
        assert manifest.data_package.repo_id == "policyengine/populace-us"
        assert manifest.data_package.release_manifest_path == US_DATA_RELEASE_PATH
        assert (
            manifest.data_package.release_manifest_revision == US_DATA_RELEASE_REVISION
        )
        assert manifest.certified_data_artifact is not None
        assert manifest.certified_data_artifact.build_id == US_DATA_RELEASE_ID
        assert manifest.certified_data_artifact.dataset == "populace_us_2024"
        assert manifest.certified_data_artifact.uri == US_CERTIFIED_DATASET_URI
        assert manifest.certification is not None
        assert manifest.certification.data_build_id == US_DATA_RELEASE_ID
        assert manifest.certification.compatibility_basis == "built_with_model_package"
        assert manifest.certification.certified_by == US_CERTIFICATION_SOURCE
        assert (
            manifest.certification.built_with_model_version
            == US_BUILT_WITH_MODEL_VERSION
        )
        assert manifest.certification.certified_for_model_version == US_MODEL_VERSION

    def test__given_uk_manifest__then_has_pinned_model_and_data_packages(self):
        manifest = get_release_manifest("uk")

        assert manifest.schema_version == 1
        assert manifest.bundle_id == f"uk-{POLICYENGINE_VERSION}"
        assert manifest.country_id == "uk"
        assert manifest.policyengine_version == POLICYENGINE_VERSION
        assert manifest.model_package.name == "policyengine-uk"
        assert manifest.model_package.version == UK_MODEL_VERSION
        assert manifest.data_package.name == "populace-data"
        assert manifest.data_package.version == UK_DATA_RELEASE_VERSION
        assert manifest.data_package.repo_id == "policyengine/populace-uk-private"
        assert manifest.data_package.release_manifest_path == UK_DATA_RELEASE_PATH
        assert (
            manifest.data_package.release_manifest_revision == UK_DATA_RELEASE_REVISION
        )
        assert manifest.certified_data_artifact is not None
        assert manifest.certified_data_artifact.build_id == UK_DATA_RELEASE_ID
        assert manifest.certified_data_artifact.dataset == "populace_uk_2023"
        assert manifest.certified_data_artifact.uri == UK_CERTIFIED_DATASET_URI
        assert manifest.certification is not None
        assert manifest.certification.data_build_id == UK_DATA_RELEASE_ID
        assert manifest.certification.compatibility_basis == "built_with_model_package"
        assert manifest.certification.certified_by == UK_CERTIFICATION_SOURCE
        assert (
            manifest.certification.built_with_model_version
            == UK_BUILT_WITH_MODEL_VERSION
        )
        assert manifest.certification.certified_for_model_version == UK_MODEL_VERSION

    def test__given_us_dataset_name__then_resolves_to_versioned_hf_url(self):
        resolved = resolve_dataset_reference("us", "populace_us_2024")

        assert resolved == US_MANAGED_DATASET_URI

    def test__given_dataset_explicit_revision__then_resolves_to_that_revision(self):
        manifest = get_release_manifest("us").model_copy(deep=True)
        manifest.datasets["long_term_cps_2100"] = ArtifactPathReference(
            path="long_term/2100.h5",
            revision="crfb-longrun-20260517",
            repo_id="policyengine/policyengine-us-data",
        )

        with patch(
            "policyengine.provenance.manifest.get_release_manifest",
            return_value=manifest,
        ):
            resolved = resolve_dataset_reference("us", "long_term_cps_2100")

        assert resolved == (
            "hf://policyengine/policyengine-us-data/"
            "long_term/2100.h5@crfb-longrun-20260517"
        )

    def test__given_uk_dataset_name__then_resolves_to_versioned_hf_url(self):
        resolved = resolve_dataset_reference("uk", "populace_uk_2023")

        assert resolved == UK_CERTIFIED_DATASET_URI

    def test__given_uk_legacy_dataset_names__then_resolves_bundled_aliases(self):
        assert (
            resolve_dataset_reference("uk", "frs_2023_24") == UK_LEGACY_FRS_DATASET_URI
        )
        assert (
            resolve_dataset_reference("uk", "enhanced_frs_2023_24")
            == UK_LEGACY_ENHANCED_FRS_DATASET_URI
        )

    def test__given_explicit_url__then_resolution_is_noop(self):
        url = "hf://policyengine/policyengine-us-data/cps_2023.h5@1.73.0"

        assert resolve_dataset_reference("us", url) == url

    def test__given_default_dataset__then_prefers_certified_data_artifact_uri(self):
        manifest = get_release_manifest("us")

        assert manifest.certified_data_artifact is not None
        assert manifest.default_dataset_uri == manifest.certified_data_artifact.uri

    def test__given_no_dataset__then_managed_resolution_uses_certified_default(self):
        assert (
            resolve_managed_dataset_reference("us")
            == get_release_manifest("us").default_dataset_uri
        )

    def test__given_explicit_uri__then_managed_resolution_requires_opt_in(self):
        dataset = "hf://policyengine/policyengine-us-data/cps_2023.h5@1.73.0"

        try:
            resolve_managed_dataset_reference("us", dataset)
        except ValueError as error:
            assert "bypass the policyengine.py release bundle" in str(error)
        else:
            raise AssertionError("Expected explicit dataset URI to be rejected")

        assert (
            resolve_managed_dataset_reference(
                "us",
                dataset,
                allow_unmanaged=True,
            )
            == dataset
        )

    def test__given_versioned_dataset_url__then_logical_name_drops_version(self):
        dataset = "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.73.0"

        assert dataset_logical_name(dataset) == "enhanced_cps_2024"

    def test__given_explicit_local_data_repo__then_resolves_local_mirror(
        self, monkeypatch, tmp_path
    ):
        local_dataset = (
            tmp_path
            / "policyengine-us-data"
            / "policyengine_us_data"
            / "storage"
            / "long_term"
            / "2100.h5"
        )
        local_dataset.parent.mkdir(parents=True)
        local_dataset.write_text("", encoding="utf-8")
        monkeypatch.setenv("POLICYENGINE_LOCAL_DATA_REPO_ROOT", str(tmp_path))

        resolved = resolve_local_managed_dataset_source(
            "us",
            "hf://policyengine/policyengine-us-data/long_term/2100.h5@candidate",
        )

        assert resolved == str(local_dataset)

    def test__given_country__then_can_fetch_data_release_manifest(self):
        get_data_release_manifest.cache_clear()
        payload = {
            "schema_version": 1,
            "data_package": {
                "name": "policyengine-us-data",
                "version": "1.78.2",
            },
            "build": {
                "build_id": "policyengine-us-data-1.78.2",
                "built_at": "2026-04-10T12:00:00Z",
                "built_with_core_package": {
                    "name": "policyengine-core",
                    "version": "3.26.0",
                },
                "built_with_model_package": {
                    "name": "policyengine-us",
                    "version": "1.687.0",
                    "git_sha": "deadbeef",
                    "data_build_fingerprint": "sha256:fingerprint",
                },
            },
            "compatible_model_packages": [
                {"name": "policyengine-us", "specifier": "==1.687.0"}
            ],
            "compatible_core_packages": [
                {"name": "policyengine-core", "specifier": "==3.26.0"},
                {"name": "policyengine-core", "specifier": "==3.26.1"},
            ],
            "default_datasets": {"national": "enhanced_cps_2024"},
            "artifacts": {
                "enhanced_cps_2024": {
                    "kind": "microdata",
                    "path": "enhanced_cps_2024.h5",
                    "repo_id": "policyengine/policyengine-us-data",
                    "revision": "1.78.2",
                    "sha256": "abc",
                    "size_bytes": 123,
                }
            },
        }

        with patch(
            "policyengine.provenance.manifest.requests.get",
            return_value=_response_with_json(payload),
        ) as mock_get:
            manifest = get_data_release_manifest("us")

        assert manifest.schema_version == 1
        assert manifest.data_package.name == "policyengine-us-data"
        assert manifest.default_datasets["national"] == "enhanced_cps_2024"
        assert manifest.build is not None
        assert manifest.build.build_id == "policyengine-us-data-1.78.2"
        assert manifest.build.built_at == "2026-04-10T12:00:00Z"
        assert manifest.build.built_with_core_package is not None
        assert manifest.build.built_with_core_package.version == "3.26.0"
        assert manifest.build.built_with_model_package is not None
        assert manifest.build.built_with_model_package.version == "1.687.0"
        assert [package.specifier for package in manifest.compatible_core_packages] == [
            "==3.26.0",
            "==3.26.1",
        ]
        assert (
            manifest.artifacts["enhanced_cps_2024"].uri
            == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.78.2"
        )
        mock_get.assert_called_once()
        assert mock_get.call_args.args[0] == (
            "https://huggingface.co/datasets/policyengine/populace-us/resolve/"
            f"{US_DATA_RELEASE_REVISION}/{US_DATA_RELEASE_PATH}"
        )

    def test__given_explicit_manifest_revision__then_builds_manifest_url(self):
        manifest = get_release_manifest("us")

        assert https_release_manifest_uri(manifest.data_package) == (
            "https://huggingface.co/datasets/policyengine/populace-us/resolve/"
            f"{US_DATA_RELEASE_REVISION}/{US_DATA_RELEASE_PATH}"
        )

    def test__given_release_manifest_artifact_uses_version_tag__then_rewrites_to_commit(
        self,
    ):
        get_data_release_manifest.cache_clear()
        payload = {
            "schema_version": 1,
            "data_package": {
                "name": "populace-data",
                "version": US_DATA_RELEASE_VERSION,
            },
            "artifacts": {
                "populace_us_2024": {
                    "kind": "microdata",
                    "path": "populace_us_2024.h5",
                    "repo_id": "policyengine/populace-us",
                    "revision": US_DATA_RELEASE_VERSION,
                    "sha256": "abc",
                    "size_bytes": 123,
                }
            },
        }

        with patch(
            "policyengine.provenance.manifest.requests.get",
            return_value=_response_with_json(payload),
        ):
            manifest = get_data_release_manifest("us")

        assert (
            manifest.artifacts["populace_us_2024"].uri
            == US_RELEASE_MANIFEST_DATASET_URI
        )
        assert (
            manifest.source_sha256
            == hashlib.sha256(json.dumps(payload).encode("utf-8")).hexdigest()
        )

    def test__given_missing_data_release_manifest__then_fetch_raises_unavailable(self):
        get_data_release_manifest.cache_clear()
        response = MagicMock()
        response.status_code = 404

        with patch(
            "policyengine.provenance.manifest.requests.get",
            return_value=response,
        ):
            try:
                get_data_release_manifest("us")
            except DataReleaseManifestUnavailableError as error:
                assert "No data release manifest" in str(error)
            else:
                raise AssertionError("Expected missing manifest to be reported")

    def test__given_range_specifier__then_certification_accepts_compatible_version(
        self,
    ):
        get_data_release_manifest.cache_clear()
        payload = {
            "schema_version": 1,
            "data_package": {
                "name": "policyengine-us-data",
                "version": "1.73.0",
            },
            "build": {
                "build_id": "policyengine-us-data-1.73.0",
                "built_with_model_package": {
                    "name": "policyengine-us",
                    "version": "1.637.0",
                    "data_build_fingerprint": "sha256:stable",
                },
            },
            "compatible_model_packages": [
                {
                    "name": "policyengine-us",
                    "specifier": ">=1.637.0,<2.0.0",
                }
            ],
            "default_datasets": {"national": "enhanced_cps_2024"},
            "artifacts": {},
        }

        with patch(
            "policyengine.provenance.manifest.requests.get",
            return_value=_response_with_json(payload),
        ):
            certification = certify_data_release_compatibility(
                "us",
                runtime_model_version="1.653.3",
            )

        assert certification.compatibility_basis == "legacy_compatible_model_package"
        assert certification.certified_for_model_version == "1.653.3"

    def test__given_matching_fingerprint__then_certification_allows_reuse(self):
        get_data_release_manifest.cache_clear()
        payload = {
            "schema_version": 1,
            "data_package": {
                "name": "policyengine-us-data",
                "version": "1.73.0",
            },
            "build": {
                "build_id": "policyengine-us-data-1.73.0",
                "built_with_model_package": {
                    "name": "policyengine-us",
                    "version": "1.601.0",
                    "git_sha": "deadbeef",
                    "data_build_fingerprint": "sha256:match",
                },
            },
            "compatible_model_packages": [],
            "default_datasets": {"national": "enhanced_cps_2024"},
            "artifacts": {},
        }

        with patch(
            "policyengine.provenance.manifest.requests.get",
            return_value=_response_with_json(payload),
        ):
            certification = certify_data_release_compatibility(
                "us",
                runtime_model_version="1.602.0",
                runtime_data_build_fingerprint="sha256:match",
            )

        assert certification.compatibility_basis == "matching_data_build_fingerprint"
        assert certification.data_build_id == "policyengine-us-data-1.73.0"
        assert certification.built_with_model_version == "1.601.0"
        assert certification.certified_for_model_version == "1.602.0"

    def test__given_private_manifest_unavailable__then_bundled_certification_is_used(
        self,
    ):
        get_data_release_manifest.cache_clear()

        with patch(
            "policyengine.provenance.manifest.get_data_release_manifest",
            side_effect=DataReleaseManifestUnavailableError("private repo"),
        ):
            certification = certify_data_release_compatibility(
                "us",
                runtime_model_version=US_MODEL_VERSION,
            )

        assert certification == get_release_manifest("us").certification

    def test__given_manifest_request_timeout__then_bundled_certification_is_used(
        self,
    ):
        get_data_release_manifest.cache_clear()

        with patch(
            "policyengine.provenance.manifest.requests.get",
            side_effect=Timeout("network timeout"),
        ):
            certification = certify_data_release_compatibility(
                "us",
                runtime_model_version=US_MODEL_VERSION,
            )

        assert certification == get_release_manifest("us").certification

    def test__given_private_manifest_unavailable_and_fingerprint_mismatch__then_fails(
        self,
    ):
        get_data_release_manifest.cache_clear()

        with (
            patch(
                "policyengine.provenance.manifest.get_data_release_manifest",
                side_effect=DataReleaseManifestUnavailableError("private repo"),
            ),
            patch(
                "policyengine.provenance.manifest.get_release_manifest",
                return_value=MagicMock(
                    certification=DataCertification(
                        compatibility_basis="matching_data_build_fingerprint",
                        certified_for_model_version="1.602.0",
                        data_build_fingerprint="sha256:expected",
                    ),
                ),
            ),
        ):
            try:
                certify_data_release_compatibility(
                    "us",
                    runtime_model_version="1.602.0",
                    runtime_data_build_fingerprint="sha256:not-a-match",
                )
            except ValueError as error:
                assert "does not match the bundled data certification" in str(error)
            else:
                raise AssertionError("Expected fingerprint mismatch to fail")

    def test__given_legacy_compatible_certification__then_offline_fingerprint_mismatch_is_allowed(
        self,
    ):
        get_data_release_manifest.cache_clear()
        bundled_certification = DataCertification(
            compatibility_basis="legacy_compatible_model_package",
            certified_for_model_version="1.602.0",
            data_build_fingerprint="sha256:build",
        )

        with (
            patch(
                "policyengine.provenance.manifest.get_data_release_manifest",
                side_effect=DataReleaseManifestUnavailableError("private repo"),
            ),
            patch(
                "policyengine.provenance.manifest.get_release_manifest",
                return_value=MagicMock(certification=bundled_certification),
            ),
        ):
            certification = certify_data_release_compatibility(
                "us",
                runtime_model_version="1.602.0",
                runtime_data_build_fingerprint="sha256:runtime",
            )

        assert certification == bundled_certification

    def test__given_manifest_fetch_failure_and_version_mismatch__then_fallback_fails(
        self,
    ):
        get_data_release_manifest.cache_clear()

        with patch(
            "policyengine.provenance.manifest.requests.get",
            side_effect=Timeout("network timeout"),
        ):
            try:
                certify_data_release_compatibility(
                    "us",
                    runtime_model_version="1.602.0",
                )
            except DataReleaseManifestUnavailableError as error:
                assert "Could not fetch" in str(error)
            else:
                raise AssertionError("Expected offline mismatched version to fail")

    def test__given_offline_hf__then_us_import_uses_bundled_certification(
        self,
        tmp_path,
    ):
        sitecustomize = tmp_path / "sitecustomize.py"
        sitecustomize.write_text(
            "\n".join(
                [
                    "import requests",
                    "from requests import Timeout",
                    "",
                    "def offline_get(*args, **kwargs):",
                    "    raise Timeout('offline')",
                    "",
                    "requests.get = offline_get",
                ]
            )
        )
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{tmp_path}{os.pathsep}{existing_pythonpath}"
            if existing_pythonpath
            else str(tmp_path)
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import policyengine.tax_benefit_models.us as us; "
                    "print(us.model.data_certification.certified_by)"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert US_CERTIFICATION_SOURCE in result.stdout

    def test__given_mismatched_version_and_fingerprint__then_certification_fails(self):
        get_data_release_manifest.cache_clear()
        payload = {
            "schema_version": 1,
            "data_package": {
                "name": "policyengine-us-data",
                "version": "1.73.0",
            },
            "build": {
                "build_id": "policyengine-us-data-1.73.0",
                "built_with_model_package": {
                    "name": "policyengine-us",
                    "version": "1.601.0",
                    "git_sha": "deadbeef",
                    "data_build_fingerprint": "sha256:build",
                },
            },
            "compatible_model_packages": [],
            "default_datasets": {"national": "enhanced_cps_2024"},
            "artifacts": {},
        }

        with patch(
            "policyengine.provenance.manifest.requests.get",
            return_value=_response_with_json(payload),
        ):
            try:
                certify_data_release_compatibility(
                    "us",
                    runtime_model_version="1.602.0",
                    runtime_data_build_fingerprint="sha256:runtime",
                )
            except ValueError as error:
                assert "not certified" in str(error)
            else:
                raise AssertionError("Expected certification to fail")

    def test__given_manifest_certification__then_release_bundle_exposes_it(self):
        manifest = get_release_manifest("uk")
        model_version = TaxBenefitModelVersion(
            model=TaxBenefitModel(id="uk"),
            version=manifest.model_package.version,
            release_manifest=manifest,
            model_package=manifest.model_package,
            data_package=manifest.data_package,
            default_dataset_uri=manifest.default_dataset_uri,
        )

        bundle = model_version.release_bundle

        assert bundle["bundle_id"] == f"uk-{POLICYENGINE_VERSION}"
        assert bundle["default_dataset"] == "populace_uk_2023"
        assert bundle["default_dataset_uri"] == manifest.default_dataset_uri
        assert bundle["certified_data_build_id"] == UK_DATA_RELEASE_ID
        assert bundle["data_build_model_version"] == UK_BUILT_WITH_MODEL_VERSION
        assert bundle["compatibility_basis"] == "built_with_model_package"
        assert bundle["certified_by"] == UK_CERTIFICATION_SOURCE

    def test__given_runtime_certification__then_release_bundle_prefers_runtime_value(
        self,
    ):
        manifest = get_release_manifest("us")
        model_version = TaxBenefitModelVersion(
            model=TaxBenefitModel(id="us"),
            version=manifest.model_package.version,
            release_manifest=manifest,
            model_package=manifest.model_package,
            data_package=manifest.data_package,
            default_dataset_uri=manifest.default_dataset_uri,
            data_certification={
                "compatibility_basis": "matching_data_build_fingerprint",
                "certified_for_model_version": "1.603.0",
                "data_build_id": "policyengine-us-data-1.73.0",
                "built_with_model_version": "1.602.0",
                "built_with_model_git_sha": "deadbeef",
                "data_build_fingerprint": "sha256:match",
                "certified_by": "runtime certification",
            },
        )

        bundle = model_version.release_bundle

        assert bundle["certified_data_build_id"] == "policyengine-us-data-1.73.0"
        assert bundle["data_build_model_version"] == "1.602.0"
        assert bundle["data_build_model_git_sha"] == "deadbeef"
        assert bundle["data_build_fingerprint"] == "sha256:match"
        assert bundle["compatibility_basis"] == "matching_data_build_fingerprint"
        assert bundle["certified_by"] == "runtime certification"

    def test__given_us_managed_microsimulation__then_passes_certified_dataset_and_bundle(
        self,
    ):
        mock_microsimulation = MagicMock()
        with (
            patch.dict(
                sys.modules,
                {
                    "policyengine_us": _country_module_with_microsimulation(
                        "policyengine_us",
                        mock_microsimulation,
                    )
                },
            ),
            patch(
                "policyengine.tax_benefit_models.us.model.materialize_dataset_source",
                return_value="/tmp/enhanced_cps_2024.h5",
            ),
        ):
            microsim = managed_us_microsimulation()

        dataset = mock_microsimulation.call_args.kwargs["dataset"]
        assert dataset == microsim.policyengine_bundle["runtime_dataset_source"]
        assert (
            microsim.policyengine_bundle["policyengine_version"] == POLICYENGINE_VERSION
        )
        assert microsim.policyengine_bundle["runtime_dataset"] == "populace_us_2024"
        assert (
            microsim.policyengine_bundle["runtime_dataset_uri"]
            == us_latest.default_dataset_uri
        )
        dataset_source = microsim.policyengine_bundle["runtime_dataset_source"]
        assert dataset_source == "/tmp/enhanced_cps_2024.h5"

    def test__given_us_unmanaged_dataset_uri__then_source_is_not_rewritten(self):
        dataset = "hf://policyengine/policyengine-us-data/cps_2023.h5@1.73.0"

        mock_microsimulation = MagicMock()
        with (
            patch.dict(
                sys.modules,
                {
                    "policyengine_us": _country_module_with_microsimulation(
                        "policyengine_us",
                        mock_microsimulation,
                    )
                },
            ),
            patch(
                "policyengine.tax_benefit_models.us.model.materialize_dataset_source",
                return_value="/tmp/cps_2023.h5",
            ),
        ):
            microsim = managed_us_microsimulation(
                dataset=dataset,
                allow_unmanaged=True,
            )

        assert mock_microsimulation.call_args.kwargs["dataset"] == "/tmp/cps_2023.h5"
        assert microsim.policyengine_bundle["runtime_dataset_uri"] == dataset
        assert microsim.policyengine_bundle["runtime_dataset_source"] == (
            "/tmp/cps_2023.h5"
        )

    def test__given_uk_managed_dataset_name__then_resolves_within_bundle(self):
        mock_microsimulation = MagicMock()
        with (
            patch.dict(
                sys.modules,
                {
                    "policyengine_uk": _country_module_with_microsimulation(
                        "policyengine_uk",
                        mock_microsimulation,
                    )
                },
            ),
            patch(
                "policyengine.tax_benefit_models.uk.model.materialize_dataset_source",
                return_value="/tmp/populace_uk_2023.h5",
            ),
        ):
            microsim = managed_uk_microsimulation(dataset="populace_uk_2023")

        dataset = mock_microsimulation.call_args.kwargs["dataset"]
        assert dataset == "/tmp/populace_uk_2023.h5"
        assert (
            microsim.policyengine_bundle["policyengine_version"] == POLICYENGINE_VERSION
        )
        assert microsim.policyengine_bundle["runtime_dataset"] == "populace_uk_2023"
        assert microsim.policyengine_bundle["runtime_dataset_uri"] == (
            UK_CERTIFIED_DATASET_URI
        )
        dataset_source = microsim.policyengine_bundle["runtime_dataset_source"]
        assert dataset_source == "/tmp/populace_uk_2023.h5"

    def test__given_uk_unmanaged_dataset_uri__then_source_is_not_rewritten(self):
        dataset = "hf://policyengine/policyengine-uk-data-private/frs_2022_23.h5@1.40.4"

        mock_microsimulation = MagicMock()
        with (
            patch.dict(
                sys.modules,
                {
                    "policyengine_uk": _country_module_with_microsimulation(
                        "policyengine_uk",
                        mock_microsimulation,
                    )
                },
            ),
            patch(
                "policyengine.tax_benefit_models.uk.model.materialize_dataset_source",
                return_value="/tmp/frs_2022_23.h5",
            ),
        ):
            microsim = managed_uk_microsimulation(
                dataset=dataset,
                allow_unmanaged=True,
            )

        assert mock_microsimulation.call_args.kwargs["dataset"] == (
            "/tmp/frs_2022_23.h5"
        )
        assert microsim.policyengine_bundle["runtime_dataset_uri"] == dataset
        assert microsim.policyengine_bundle["runtime_dataset_source"] == (
            "/tmp/frs_2022_23.h5"
        )
