from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from policyengine.provenance.manifest import CountryReleaseManifest

from .hf import parse_hf_reference_if_present
from .io import required_dict, required_string, write_json
from .types import BundleImportError


def write_country_release_manifests(
    *,
    country_bundles: dict[str, dict],
    manifest_dir: Path,
) -> list[Path]:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    written_paths = []
    for country_id, country_bundle in sorted(country_bundles.items()):
        release_manifest = country_release_manifest(country_bundle)
        try:
            CountryReleaseManifest.model_validate(release_manifest)
        except ValidationError as exc:
            raise BundleImportError(
                f"Generated release manifest for {country_id} is invalid: {exc}"
            ) from exc
        output_path = manifest_dir / f"{country_id}.json"
        write_json(output_path, release_manifest)
        written_paths.append(output_path)
    return written_paths


def country_release_manifest(country_bundle: dict) -> dict:
    country_id = required_string(country_bundle, "country_id")
    bundle_version = required_string(country_bundle, "bundle_version")
    model_package = required_dict(country_bundle, "model_package")
    data_package = required_dict(country_bundle, "data_package")
    compatibility = required_dict(country_bundle, "compatibility")
    compatibility_metadata = compatibility.get("metadata")
    if not isinstance(compatibility_metadata, dict):
        compatibility_metadata = {}
    datasets = required_dict(country_bundle, "datasets")
    default_dataset = required_string(country_bundle, "default_dataset")
    default_artifact = required_dict(datasets, default_dataset)

    data_package_payload = data_package_version(data_package)
    certified_artifact = certified_data_artifact(
        default_dataset=default_dataset,
        default_artifact=default_artifact,
        data_package=data_package_payload,
        compatibility_metadata=compatibility_metadata,
    )
    certification = data_certification(
        model_package=model_package,
        compatibility=compatibility,
        compatibility_metadata=compatibility_metadata,
    )

    return {
        "schema_version": 1,
        "bundle_id": f"{country_id}-{bundle_version}",
        "country_id": country_id,
        "policyengine_version": bundle_version,
        "model_package": package_version(model_package),
        "data_package": data_package_payload,
        "default_dataset": default_dataset,
        "datasets": dataset_path_references(datasets),
        "region_datasets": region_dataset_templates(
            country_bundle.get("region_datasets", {})
        ),
        "certified_data_artifact": certified_artifact,
        "certification": certification,
    }


def data_package_version(data_package: dict) -> dict:
    payload = {
        "name": required_string(data_package, "name"),
        "version": required_string(data_package, "version"),
        "repo_id": required_string(data_package, "repo_id"),
        "repo_type": data_package.get("repo_type", "model"),
        "release_manifest_path": data_package.get(
            "release_manifest_path",
            "release_manifest.json",
        ),
    }
    release_manifest_revision = data_package.get("release_manifest_revision")
    if isinstance(release_manifest_revision, str) and release_manifest_revision:
        payload["release_manifest_revision"] = release_manifest_revision
    return payload


def certified_data_artifact(
    *,
    default_dataset: str,
    default_artifact: dict,
    data_package: dict,
    compatibility_metadata: dict,
) -> dict:
    payload = {
        "data_package": {
            "name": data_package["name"],
            "version": data_package["version"],
        },
        "dataset": default_dataset,
        "uri": artifact_uri(default_artifact),
    }
    if default_artifact.get("sha256"):
        payload["sha256"] = default_artifact["sha256"]
    build_id = compatibility_metadata.get("data_build_id")
    if isinstance(build_id, str) and build_id:
        payload["build_id"] = build_id
    return payload


def data_certification(
    *,
    model_package: dict,
    compatibility: dict,
    compatibility_metadata: dict,
) -> dict:
    payload = {
        "compatibility_basis": compatibility.get("basis", "bundle_candidate"),
        "certified_for_model_version": required_string(
            model_package,
            "version",
        ),
        "certified_by": compatibility.get("asserted_by", "policyengine-bundles"),
    }
    optional_fields = {
        "data_build_id": "data_build_id",
        "built_with_model_version": "built_with_model_version",
        "built_with_model_git_sha": "built_with_model_git_sha",
        "data_build_fingerprint": "data_build_fingerprint",
    }
    for output_key, metadata_key in optional_fields.items():
        value = compatibility_metadata.get(metadata_key)
        if isinstance(value, str) and value:
            payload[output_key] = value
    return payload


def package_version(package: dict) -> dict:
    payload = {
        "name": required_string(package, "name"),
        "version": required_string(package, "version"),
    }
    if package.get("sha256"):
        payload["sha256"] = package["sha256"]
    if package.get("wheel_url"):
        payload["wheel_url"] = package["wheel_url"]
    return payload


def dataset_path_references(datasets: dict) -> dict:
    path_references = {}
    for dataset, artifact in sorted(datasets.items()):
        if not isinstance(dataset, str) or not isinstance(artifact, dict):
            raise BundleImportError(
                "Country bundle datasets must map names to objects."
            )
        parsed_uri = parse_hf_reference_if_present(artifact.get("uri"))
        path = artifact.get("path") or (parsed_uri.path if parsed_uri else None)
        if not isinstance(path, str) or not path:
            raise BundleImportError(
                f"Dataset {dataset} does not include a path and its uri cannot "
                "be translated into a path reference."
            )
        payload = {"path": path}
        revision = artifact.get("revision") or (
            parsed_uri.revision if parsed_uri else None
        )
        if isinstance(revision, str) and revision:
            payload["revision"] = revision
        if artifact.get("sha256"):
            payload["sha256"] = artifact["sha256"]
        if artifact.get("metadata_sha256"):
            payload["metadata_sha256"] = artifact["metadata_sha256"]
        # Inherited artifacts may live in a different repo than the data
        # package (e.g. long-term datasets pinned to policyengine-us-data
        # while populace-data is the package); carry the pin through.
        if artifact.get("repo_id"):
            payload["repo_id"] = artifact["repo_id"]
        if artifact.get("repo_type"):
            payload["repo_type"] = artifact["repo_type"]
        path_references[dataset] = payload
    return path_references


def region_dataset_templates(region_datasets: dict) -> dict:
    templates = {}
    if not isinstance(region_datasets, dict):
        raise BundleImportError("Country bundle region_datasets must be an object.")
    for region, template in sorted(region_datasets.items()):
        if not isinstance(region, str) or not isinstance(template, dict):
            raise BundleImportError(
                "Country bundle region_datasets must map names to objects."
            )
        path_template = template.get("path_template")
        if isinstance(path_template, str) and path_template:
            templates[region] = {"path_template": path_template}
    return templates


def artifact_uri(artifact: dict) -> str:
    parsed_uri = parse_hf_reference_if_present(artifact.get("uri"))
    repo_id = artifact.get("repo_id") or (parsed_uri.repo_id if parsed_uri else None)
    path = artifact.get("path") or (parsed_uri.path if parsed_uri else None)
    revision = artifact.get("revision") or (parsed_uri.revision if parsed_uri else None)
    if (
        isinstance(repo_id, str)
        and repo_id
        and isinstance(path, str)
        and path
        and isinstance(revision, str)
        and revision
    ):
        return f"hf://{repo_id}/{path}@{revision}"

    uri = artifact.get("uri")
    if isinstance(uri, str) and uri:
        return uri
    raise BundleImportError("Artifact does not include a resolvable uri.")
