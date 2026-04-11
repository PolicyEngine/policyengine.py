"""Tests for bundled compatibility manifests and data release manifests."""

import json
from unittest.mock import MagicMock, patch

from policyengine.core.release_manifest import (
    dataset_logical_name,
    get_data_release_manifest,
    get_release_manifest,
    resolve_dataset_reference,
)


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

        assert manifest.country_id == "us"
        assert manifest.policyengine_version == "3.4.0"
        assert manifest.model_package.name == "policyengine-us"
        assert manifest.model_package.version == "1.602.0"
        assert manifest.data_package.name == "policyengine-us-data"
        assert manifest.data_package.version == "1.73.0"
        assert manifest.data_package.repo_id == "policyengine/policyengine-us-data"

    def test__given_uk_manifest__then_has_pinned_model_and_data_packages(self):
        manifest = get_release_manifest("uk")

        assert manifest.country_id == "uk"
        assert manifest.policyengine_version == "3.4.0"
        assert manifest.model_package.name == "policyengine-uk"
        assert manifest.model_package.version == "2.74.0"
        assert manifest.data_package.name == "policyengine-uk-data"
        assert manifest.data_package.version == "1.40.4"
        assert manifest.data_package.repo_id == "policyengine/policyengine-uk-data"

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
            == "hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5@1.40.4"
        )

    def test__given_explicit_url__then_resolution_is_noop(self):
        url = "hf://policyengine/policyengine-us-data/cps_2023.h5@1.73.0"

        assert resolve_dataset_reference("us", url) == url

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
        assert (
            manifest.artifacts["enhanced_cps_2024"].uri
            == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.73.0"
        )
        assert mock_get.call_count == 1
