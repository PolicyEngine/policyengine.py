"""Tests for bundled compatibility manifests and data release manifests."""

import json
from unittest.mock import MagicMock, patch

from policyengine.core.release_manifest import (
    certify_data_release_compatibility,
    dataset_logical_name,
    get_data_release_manifest,
    get_release_manifest,
    resolve_dataset_reference,
    resolve_managed_dataset_reference,
)
from policyengine.core.tax_benefit_model import TaxBenefitModel
from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion
from policyengine.tax_benefit_models.uk import (
    managed_microsimulation as managed_uk_microsimulation,
)
from policyengine.tax_benefit_models.us import (
    managed_microsimulation as managed_us_microsimulation,
)
from policyengine.tax_benefit_models.us import us_latest


def _response_with_json(payload: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.text = json.dumps(payload)
    response.raise_for_status.return_value = None
    return response


class TestReleaseManifests:
    """Tests for bundled country manifests."""

    def teardown_method(self):
        get_release_manifest.cache_clear()
        get_data_release_manifest.cache_clear()

    def test__given_us_manifest__then_has_pinned_model_and_data_packages(self):
        manifest = get_release_manifest("us")

        assert manifest.schema_version == 1
        assert manifest.bundle_id == "us-3.4.0"
        assert manifest.country_id == "us"
        assert manifest.policyengine_version == "3.4.0"
        assert manifest.model_package.name == "policyengine-us"
        assert manifest.model_package.version == "1.602.0"
        assert manifest.data_package.name == "policyengine-us-data"
        assert manifest.data_package.version == "1.73.0"
        assert manifest.data_package.repo_id == "policyengine/policyengine-us-data"
        assert manifest.certified_data_artifact is not None
        assert manifest.certified_data_artifact.build_id == "policyengine-us-data-1.73.0"
        assert manifest.certified_data_artifact.dataset == "enhanced_cps_2024"
        assert manifest.certification is not None
        assert manifest.certification.data_build_id == "policyengine-us-data-1.73.0"
        assert manifest.certification.built_with_model_version == "1.602.0"
        assert manifest.certification.certified_for_model_version == "1.602.0"

    def test__given_uk_manifest__then_has_pinned_model_and_data_packages(self):
        manifest = get_release_manifest("uk")

        assert manifest.schema_version == 1
        assert manifest.bundle_id == "uk-3.4.0"
        assert manifest.country_id == "uk"
        assert manifest.policyengine_version == "3.4.0"
        assert manifest.model_package.name == "policyengine-uk"
        assert manifest.model_package.version == "2.74.0"
        assert manifest.data_package.name == "policyengine-uk-data"
        assert manifest.data_package.version == "1.40.4"
        assert manifest.data_package.repo_id == "policyengine/policyengine-uk-data-private"
        assert manifest.certified_data_artifact is not None
        assert manifest.certified_data_artifact.build_id == "policyengine-uk-data-1.40.4"
        assert manifest.certified_data_artifact.dataset == "enhanced_frs_2023_24"
        assert manifest.certification is not None
        assert manifest.certification.data_build_id == "policyengine-uk-data-1.40.4"
        assert manifest.certification.built_with_model_version == "2.74.0"
        assert manifest.certification.certified_for_model_version == "2.74.0"

    def test__given_us_dataset_name__then_resolves_to_versioned_hf_url(self):
        resolved = resolve_dataset_reference("us", "enhanced_cps_2024")

        assert (
            resolved
            == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.73.0"
        )

    def test__given_uk_dataset_name__then_resolves_to_versioned_hf_url(self):
        resolved = resolve_dataset_reference("uk", "enhanced_frs_2023_24")

        assert (
            resolved
            == "hf://policyengine/policyengine-uk-data-private/enhanced_frs_2023_24.h5@1.40.4"
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
            resolve_managed_dataset_reference("us") == get_release_manifest("us").default_dataset_uri
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

    def test__given_country__then_can_fetch_data_release_manifest(self):
        get_data_release_manifest.cache_clear()
        payload = {
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
                    "version": "1.602.0",
                    "git_sha": "deadbeef",
                    "data_build_fingerprint": "sha256:fingerprint",
                }
            },
            "compatible_model_packages": [
                {"name": "policyengine-us", "specifier": "==1.602.0"}
            ],
            "default_datasets": {"national": "enhanced_cps_2024"},
            "artifacts": {
                "enhanced_cps_2024": {
                    "kind": "microdata",
                    "path": "enhanced_cps_2024.h5",
                    "repo_id": "policyengine/policyengine-us-data",
                    "revision": "1.73.0",
                    "sha256": "abc",
                    "size_bytes": 123,
                }
            },
        }

        with patch(
            "policyengine.core.release_manifest.requests.get",
            return_value=_response_with_json(payload),
        ) as mock_get:
            manifest = get_data_release_manifest("us")

        assert manifest.schema_version == 1
        assert manifest.data_package.name == "policyengine-us-data"
        assert manifest.default_datasets["national"] == "enhanced_cps_2024"
        assert manifest.build is not None
        assert manifest.build.build_id == "policyengine-us-data-1.73.0"
        assert manifest.build.built_at == "2026-04-10T12:00:00Z"
        assert manifest.build.built_with_model_package is not None
        assert manifest.build.built_with_model_package.version == "1.602.0"
        assert (
            manifest.artifacts["enhanced_cps_2024"].uri
            == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.73.0"
        )
        assert mock_get.call_count == 1

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
                }
            },
            "compatible_model_packages": [],
            "default_datasets": {"national": "enhanced_cps_2024"},
            "artifacts": {},
        }

        with patch(
            "policyengine.core.release_manifest.requests.get",
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
                }
            },
            "compatible_model_packages": [],
            "default_datasets": {"national": "enhanced_cps_2024"},
            "artifacts": {},
        }

        with patch(
            "policyengine.core.release_manifest.requests.get",
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

        assert bundle["bundle_id"] == "uk-3.4.0"
        assert bundle["default_dataset"] == "enhanced_frs_2023_24"
        assert bundle["default_dataset_uri"] == manifest.default_dataset_uri
        assert bundle["certified_data_build_id"] == "policyengine-uk-data-1.40.4"
        assert bundle["data_build_model_version"] == "2.74.0"
        assert bundle["compatibility_basis"] == "exact_build_model_version"
        assert bundle["certified_by"] == "policyengine.py bundled manifest"

    def test__given_runtime_certification__then_release_bundle_prefers_runtime_value(self):
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

    def test__given_us_managed_microsimulation__then_passes_certified_dataset_and_bundle(self):
        with patch("policyengine_us.Microsimulation") as mock_microsimulation:
            microsim = managed_us_microsimulation()

        dataset = mock_microsimulation.call_args.kwargs["dataset"]
        assert str(dataset).endswith(
            "policyengine_us_data/storage/enhanced_cps_2024.h5"
        )
        assert microsim.policyengine_bundle["policyengine_version"] == "3.4.0"
        assert microsim.policyengine_bundle["runtime_dataset"] == "enhanced_cps_2024"
        assert microsim.policyengine_bundle["runtime_dataset_uri"] == us_latest.default_dataset_uri
        assert str(microsim.policyengine_bundle["runtime_dataset_source"]).endswith(
            "policyengine_us_data/storage/enhanced_cps_2024.h5"
        )

    def test__given_uk_managed_dataset_name__then_resolves_within_bundle(self):
        with patch("policyengine_uk.Microsimulation") as mock_microsimulation:
            microsim = managed_uk_microsimulation(dataset="enhanced_frs_2023_24")

        dataset = mock_microsimulation.call_args.kwargs["dataset"]
        from policyengine_uk.data.dataset_schema import UKSingleYearDataset

        assert isinstance(dataset, UKSingleYearDataset)
        assert getattr(dataset, "time_period", None) == "2023"
        assert microsim.policyengine_bundle["policyengine_version"] == "3.4.0"
        assert microsim.policyengine_bundle["runtime_dataset"] == "enhanced_frs_2023_24"
        assert microsim.policyengine_bundle["runtime_dataset_uri"] == (
            "hf://policyengine/policyengine-uk-data-private/enhanced_frs_2023_24.h5@1.40.4"
        )
        assert str(microsim.policyengine_bundle["runtime_dataset_source"]).endswith(
            "policyengine_uk_data/storage/enhanced_frs_2023_24.h5"
        )
