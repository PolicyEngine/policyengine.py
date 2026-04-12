import os
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

import requests
from pydantic import BaseModel, Field

HF_REQUEST_TIMEOUT_SECONDS = 30


class PackageVersion(BaseModel):
    name: str
    version: str


class DataPackageVersion(PackageVersion):
    repo_id: str
    repo_type: str = "model"
    release_manifest_path: str = "release_manifest.json"


class CompatibleModelPackage(BaseModel):
    name: str
    specifier: str


class BuiltWithModelPackage(PackageVersion):
    git_sha: str | None = None
    data_build_fingerprint: str | None = None


class DataBuildInfo(BaseModel):
    build_id: str | None = None
    built_at: str | None = None
    built_with_model_package: BuiltWithModelPackage | None = None


class ArtifactPathReference(BaseModel):
    path: str


class ArtifactPathTemplate(BaseModel):
    path_template: str

    def resolve(self, **kwargs: str) -> str:
        return self.path_template.format(**kwargs)


class DataReleaseArtifact(BaseModel):
    kind: str
    path: str
    repo_id: str
    revision: str
    sha256: str | None = None
    size_bytes: int | None = None

    @property
    def uri(self) -> str:
        return build_hf_uri(
            repo_id=self.repo_id,
            path_in_repo=self.path,
            revision=self.revision,
        )


class DataReleaseManifest(BaseModel):
    schema_version: int
    data_package: PackageVersion
    compatible_model_packages: list[CompatibleModelPackage] = Field(
        default_factory=list
    )
    default_datasets: dict[str, str] = Field(default_factory=dict)
    build: DataBuildInfo | None = None
    artifacts: dict[str, DataReleaseArtifact] = Field(default_factory=dict)


class DataCertification(BaseModel):
    compatibility_basis: str
    certified_for_model_version: str
    data_build_id: str | None = None
    built_with_model_version: str | None = None
    built_with_model_git_sha: str | None = None
    data_build_fingerprint: str | None = None
    certified_by: str | None = None


class CertifiedDataArtifact(BaseModel):
    data_package: PackageVersion | None = None
    dataset: str
    uri: str
    sha256: str | None = None
    build_id: str | None = None


class CountryReleaseManifest(BaseModel):
    schema_version: int = 1
    bundle_id: str | None = None
    published_at: str | None = None
    country_id: str
    policyengine_version: str
    model_package: PackageVersion
    data_package: DataPackageVersion
    default_dataset: str
    datasets: dict[str, ArtifactPathReference] = Field(default_factory=dict)
    region_datasets: dict[str, ArtifactPathTemplate] = Field(default_factory=dict)
    certified_data_artifact: CertifiedDataArtifact | None = None
    certification: DataCertification | None = None

    @property
    def default_dataset_uri(self) -> str:
        if (
            self.certified_data_artifact is not None
            and self.certified_data_artifact.dataset == self.default_dataset
        ):
            return self.certified_data_artifact.uri
        return resolve_dataset_reference(self.country_id, self.default_dataset)


def build_hf_uri(repo_id: str, path_in_repo: str, revision: str) -> str:
    return f"hf://{repo_id}/{path_in_repo}@{revision}"


@lru_cache
def get_release_manifest(country_id: str) -> CountryReleaseManifest:
    manifest_path = files("policyengine").joinpath(
        "data", "release_manifests", f"{country_id}.json"
    )
    if not manifest_path.is_file():
        raise ValueError(f"No bundled release manifest for country '{country_id}'")

    return CountryReleaseManifest.model_validate_json(manifest_path.read_text())


def _data_release_manifest_url(data_package: DataPackageVersion) -> str:
    return (
        "https://huggingface.co/"
        f"{data_package.repo_id}/resolve/{data_package.version}/"
        f"{data_package.release_manifest_path}"
    )


@lru_cache
def get_data_release_manifest(country_id: str) -> DataReleaseManifest:
    country_manifest = get_release_manifest(country_id)
    data_package = country_manifest.data_package

    headers = {}
    token = os.environ.get("HUGGING_FACE_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(
        _data_release_manifest_url(data_package),
        headers=headers,
        timeout=HF_REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code in (401, 403):
        raise ValueError(
            "Could not fetch the data release manifest from Hugging Face. "
            "If this country uses a private data repo, set HUGGING_FACE_TOKEN."
        )
    response.raise_for_status()
    return DataReleaseManifest.model_validate_json(response.text)


def _specifier_matches(version: str, specifier: str) -> bool:
    if specifier.startswith("=="):
        return version == specifier[2:]
    return False


def certify_data_release_compatibility(
    country_id: str,
    runtime_model_version: str,
    runtime_data_build_fingerprint: str | None = None,
) -> DataCertification:
    country_manifest = get_release_manifest(country_id)
    data_release_manifest = get_data_release_manifest(country_id)
    built_with_model = (
        data_release_manifest.build.built_with_model_package
        if data_release_manifest.build is not None
        else None
    )

    if (
        built_with_model is not None
        and built_with_model.name != country_manifest.model_package.name
    ):
        raise ValueError(
            "Data release manifest was built with a different model package: "
            f"expected {country_manifest.model_package.name}, "
            f"got {built_with_model.name}."
        )

    if (
        built_with_model is not None
        and built_with_model.version == runtime_model_version
    ):
        return DataCertification(
            compatibility_basis="exact_build_model_version",
            certified_for_model_version=runtime_model_version,
            data_build_id=(
                data_release_manifest.build.build_id
                if data_release_manifest.build is not None
                else None
            ),
            built_with_model_version=built_with_model.version,
            built_with_model_git_sha=built_with_model.git_sha,
            data_build_fingerprint=built_with_model.data_build_fingerprint,
        )

    if (
        built_with_model is not None
        and built_with_model.data_build_fingerprint is not None
        and runtime_data_build_fingerprint is not None
        and built_with_model.data_build_fingerprint == runtime_data_build_fingerprint
    ):
        return DataCertification(
            compatibility_basis="matching_data_build_fingerprint",
            certified_for_model_version=runtime_model_version,
            data_build_id=(
                data_release_manifest.build.build_id
                if data_release_manifest.build is not None
                else None
            ),
            built_with_model_version=built_with_model.version,
            built_with_model_git_sha=built_with_model.git_sha,
            data_build_fingerprint=built_with_model.data_build_fingerprint,
        )

    for compatible_model_package in data_release_manifest.compatible_model_packages:
        if compatible_model_package.name != country_manifest.model_package.name:
            continue
        if _specifier_matches(
            version=runtime_model_version,
            specifier=compatible_model_package.specifier,
        ):
            return DataCertification(
                compatibility_basis="legacy_compatible_model_package",
                certified_for_model_version=runtime_model_version,
                data_build_id=(
                    data_release_manifest.build.build_id
                    if data_release_manifest.build is not None
                    else None
                ),
                built_with_model_version=(
                    built_with_model.version if built_with_model is not None else None
                ),
                built_with_model_git_sha=(
                    built_with_model.git_sha if built_with_model is not None else None
                ),
                data_build_fingerprint=(
                    built_with_model.data_build_fingerprint
                    if built_with_model is not None
                    else None
                ),
            )

    raise ValueError(
        "Data release manifest is not certified for the runtime model version "
        f"{runtime_model_version} in country '{country_id}'."
    )


def resolve_dataset_reference(country_id: str, dataset: str) -> str:
    if "://" in dataset:
        return dataset

    manifest = get_release_manifest(country_id)
    path_reference = manifest.datasets.get(dataset)
    if path_reference is not None:
        return build_hf_uri(
            repo_id=manifest.data_package.repo_id,
            path_in_repo=path_reference.path,
            revision=manifest.data_package.version,
        )

    data_release_manifest = get_data_release_manifest(country_id)
    artifact = data_release_manifest.artifacts.get(dataset)
    if artifact is None:
        raise ValueError(
            f"Unknown dataset '{dataset}' for country '{country_id}'. "
            f"Known datasets: {sorted(manifest.datasets)}"
        )

    return artifact.uri


def dataset_logical_name(dataset: str) -> str:
    return Path(dataset.rsplit("@", 1)[0]).stem


def resolve_default_datasets(country_id: str) -> list[str]:
    manifest = get_release_manifest(country_id)
    return list(manifest.datasets.keys())


def resolve_region_dataset_path(
    country_id: str,
    region_type: str,
    **kwargs: str,
) -> str | None:
    manifest = get_release_manifest(country_id)
    template = manifest.region_datasets.get(region_type)
    if template is None:
        return None

    resolved_path = template.resolve(**kwargs)
    if "://" in resolved_path:
        return resolved_path

    return build_hf_uri(
        repo_id=manifest.data_package.repo_id,
        path_in_repo=resolved_path,
        revision=manifest.data_package.version,
    )
