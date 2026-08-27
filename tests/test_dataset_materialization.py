from pathlib import Path

import pytest

from policyengine.provenance.dataset_materialization import (
    BundleDatasetPlan,
    DatasetMaterializationError,
    MaterializedDataset,
    _dataset_package_strategy,
    resolve_bundle_dataset_plan,
)
from policyengine.provenance.manifest import CountryReleaseManifest


def _manifest() -> CountryReleaseManifest:
    return CountryReleaseManifest.model_validate(
        {
            "country_id": "uk",
            "policyengine_version": "5.0.4",
            "model_package": {"name": "policyengine-uk", "version": "2.90.2"},
            "data_package": {
                "name": "policyengine-uk-data",
                "version": "1.56.16",
                "repo_id": "policyengine/policyengine-uk-data-private",
                "repo_type": "model",
            },
            "default_dataset": "enhanced_frs_2024_25",
            "datasets": {
                "enhanced_frs_2024_25": {
                    "path": "enhanced_frs_2024_25.h5",
                    "revision": "uk-release",
                    "sha256": "a" * 64,
                },
                "populace_uk_2023": {
                    "data_package_name": "populace-data",
                    "path": "populace_uk_2023.h5",
                    "repo_id": "policyengine/populace-uk-private",
                    "repo_type": "model",
                    "revision": "populace-release",
                    "sha256": "b" * 64,
                },
            },
        }
    )


def test_resolve_bundle_dataset_plan_inherits_primary_package(tmp_path):
    plan = resolve_bundle_dataset_plan("uk", data_dir=tmp_path, manifest=_manifest())

    assert plan.data_package_name == "policyengine-uk-data"
    assert plan.repo_id == "policyengine/policyengine-uk-data-private"
    assert plan.repo_type == "model"
    assert plan.revision == "uk-release"
    assert plan.destination == tmp_path / "enhanced_frs_2024_25.h5"


def test_resolve_bundle_dataset_plan_uses_cross_package_overlay(tmp_path):
    plan = resolve_bundle_dataset_plan(
        "uk",
        "populace_uk_2023",
        data_dir=tmp_path,
        manifest=_manifest(),
    )

    assert plan.data_package_name == "populace-data"
    assert plan.repo_id == "policyengine/populace-uk-private"
    assert plan.repo_type == "model"
    assert plan.revision == "populace-release"


def test_bundle_dataset_models_round_trip_json():
    plan = resolve_bundle_dataset_plan("uk", manifest=_manifest())
    assert BundleDatasetPlan.model_validate_json(plan.model_dump_json()) == plan

    result = MaterializedDataset(
        **plan.model_dump(exclude={"path", "destination"}),
        actual_sha256=plan.expected_sha256,
        path=Path("data/enhanced_frs_2024_25.h5"),
        cache_hit=True,
    )
    assert MaterializedDataset.model_validate_json(result.model_dump_json()) == result


def test_unknown_data_package_is_rejected():
    with pytest.raises(DatasetMaterializationError, match="Unsupported bundle"):
        _dataset_package_strategy("unknown-data")
