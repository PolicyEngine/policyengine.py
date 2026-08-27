"""Resolve and materialize datasets certified by a PolicyEngine.py bundle."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

from .manifest import (
    CountryReleaseManifest,
    _artifact_revision,
    build_hf_uri,
    get_release_manifest,
)

DEFAULT_DATA_DIR = Path("./data")


class DatasetMaterializationError(ValueError):
    """Raised when a dataset cannot be resolved or materialized safely."""


class BundleDatasetPlan(BaseModel):
    """Exact bundle metadata needed to materialize one managed dataset."""

    country_id: str
    dataset: str
    data_package_name: str
    repo_id: str
    repo_type: Literal["model", "dataset"]
    path: str
    revision: str
    expected_sha256: str
    source_uri: str
    destination: Path
    build_id: Optional[str] = None


class MaterializedDataset(BaseModel):
    """Verified local representation of one bundle-managed dataset."""

    country_id: str
    dataset: str
    data_package_name: str
    repo_id: str
    repo_type: Literal["model", "dataset"]
    revision: str
    source_uri: str
    expected_sha256: str
    actual_sha256: str
    path: Path
    cache_hit: bool
    build_id: Optional[str] = None


class _DatasetPackageStrategy:
    """Package-specific validation for a bundle dataset source."""

    def validate(self, plan: BundleDatasetPlan) -> None:
        raise NotImplementedError


class _CountryDataPackageStrategy(_DatasetPackageStrategy):
    def validate(self, plan: BundleDatasetPlan) -> None:
        package_name = plan.data_package_name
        if not (
            package_name.startswith("policyengine-") and package_name.endswith("-data")
        ):
            raise DatasetMaterializationError(
                f"Unsupported country data package: {package_name!r}."
            )


class _PopulaceDataPackageStrategy(_DatasetPackageStrategy):
    def validate(self, plan: BundleDatasetPlan) -> None:
        if plan.data_package_name != "populace-data":
            raise DatasetMaterializationError(
                f"Unsupported Populace data package: {plan.data_package_name!r}."
            )


def _dataset_package_strategy(data_package_name: str) -> _DatasetPackageStrategy:
    if data_package_name == "populace-data":
        return _PopulaceDataPackageStrategy()
    if data_package_name.startswith("policyengine-") and data_package_name.endswith(
        "-data"
    ):
        return _CountryDataPackageStrategy()
    raise DatasetMaterializationError(
        "Unsupported bundle data package "
        f"{data_package_name!r}; expected 'populace-data' or "
        "'policyengine-<country>-data'."
    )


def resolve_bundle_dataset_plan(
    country_id: str,
    dataset: Optional[str] = None,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    manifest: Optional[CountryReleaseManifest] = None,
) -> BundleDatasetPlan:
    """Resolve one logical dataset to its exact bundle-certified source."""

    country_manifest = manifest or get_release_manifest(country_id)
    dataset_name = dataset or country_manifest.default_dataset
    reference = country_manifest.datasets.get(dataset_name)
    if reference is None:
        raise DatasetMaterializationError(
            f"Unknown managed dataset {dataset_name!r} for country "
            f"{country_id!r}. Known datasets: "
            f"{sorted(country_manifest.datasets)}"
        )

    data_package_name = (
        reference.data_package_name or country_manifest.data_package.name
    )
    repo_id = reference.repo_id or country_manifest.data_package.repo_id
    repo_type = reference.repo_type or country_manifest.data_package.repo_type
    revision = reference.revision or _artifact_revision(country_manifest.data_package)
    if repo_type not in {"model", "dataset"}:
        raise DatasetMaterializationError(
            f"Dataset {dataset_name!r} has unsupported Hugging Face repository "
            f"type {repo_type!r}."
        )
    if not reference.sha256:
        raise DatasetMaterializationError(
            f"Managed dataset {dataset_name!r} is missing a certified sha256."
        )

    plan = BundleDatasetPlan(
        country_id=country_id,
        dataset=dataset_name,
        data_package_name=data_package_name,
        repo_id=repo_id,
        repo_type=repo_type,
        path=reference.path,
        revision=revision,
        expected_sha256=reference.sha256,
        source_uri=build_hf_uri(repo_id, reference.path, revision),
        destination=data_dir / Path(reference.path).name,
        build_id=(
            country_manifest.certified_data_artifact.build_id
            if country_manifest.certified_data_artifact is not None
            else None
        ),
    )
    _dataset_package_strategy(data_package_name).validate(plan)
    return plan
