"""Certify a data release directly from its HF release manifest.

This replaces the policyengine-bundles hop: the data release manifest
(published next to the artifacts, with per-artifact repo/revision/sha256
pins, build provenance, compatibility claims, and region templates) is
the source of truth, and certification derives the vendored country
manifest from it in one step.

The certification asserts that *this* policyengine release, with the
model package pinned in ``pyproject.toml``, serves the data release —
an assertion the test suite then exercises on the exact pair.

.. code-block:: python

    from policyengine.provenance.certification import certify_data_release

    result = certify_data_release(
        country="us",
        manifest_uri=(
            "hf://dataset/policyengine/populace-us"
            "@populace-us-2024-5da5a95-20260611"
            "/releases/populace-us-2024-5da5a95-20260611/release_manifest.json"
        ),
    )
    print(result.summary())

``scripts/certify_data_release.py`` is the argparse wrapper. Network
access is required (HF manifest fetch + PyPI wheel metadata). Countries
whose data release predates release manifests (UK's enhanced FRS) keep
using :mod:`policyengine.provenance.bundle` until their next release.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Optional

import requests

from policyengine.provenance.manifest import (
    HF_REQUEST_TIMEOUT_SECONDS,
    DataReleaseManifest,
    fetch_pypi_wheel_metadata,
)

MANIFEST_URI_PATTERN = re.compile(
    r"^hf://(?P<repo_type>dataset|model)/(?P<repo_id>[^@]+)@(?P<revision>[^/]+)"
    r"/(?P<path>.+)$"
)

COUNTRY_MODEL_PACKAGES = {
    "us": "policyengine-us",
    "uk": "policyengine-uk",
}

CERTIFIED_BY = "policyengine.py certification"
COMPATIBILITY_BASIS = "data_release_manifest"


class CertificationError(ValueError):
    """Raised when a data release cannot be certified."""


@dataclass
class CertificationResult:
    country: str
    manifest_uri: str
    manifest_sha256: str
    country_manifest_path: Path
    dataset_count: int
    default_dataset: str
    build_id: Optional[str]
    model_package: str
    model_version: str
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"certified {self.country}: {self.default_dataset} "
            f"({self.dataset_count} datasets, build {self.build_id})",
            f"  manifest: {self.manifest_uri}",
            f"  manifest sha256: {self.manifest_sha256}",
            f"  model: {self.model_package}=={self.model_version}",
            f"  wrote: {self.country_manifest_path}",
        ]
        for warning in self.warnings:
            lines.append(f"  WARNING: {warning}")
        return "\n".join(lines)


def parse_manifest_uri(manifest_uri: str) -> dict:
    match = MANIFEST_URI_PATTERN.match(manifest_uri)
    if match is None:
        raise CertificationError(
            "Manifest URI must look like "
            "hf://dataset/<repo_id>@<revision>/<path>, got "
            f"{manifest_uri!r}."
        )
    return match.groupdict()


def https_manifest_url(parts: dict) -> str:
    prefix = "datasets/" if parts["repo_type"] == "dataset" else ""
    return (
        f"https://huggingface.co/{prefix}{parts['repo_id']}/resolve/"
        f"{parts['revision']}/{parts['path']}"
    )


def fetch_release_manifest(
    manifest_uri: str,
    token: Optional[str] = None,
) -> tuple[DataReleaseManifest, str, dict]:
    """Fetch and parse the data release manifest; returns
    (manifest, sha256 of the fetched bytes, parsed URI parts)."""
    parts = parse_manifest_uri(manifest_uri)
    url = https_manifest_url(parts)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.get(url, headers=headers, timeout=HF_REQUEST_TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise CertificationError(
            f"Could not fetch data release manifest ({response.status_code}) "
            f"from {url}."
        )
    sha256 = hashlib.sha256(response.content).hexdigest()
    payload = json.loads(response.content)
    manifest = DataReleaseManifest.model_validate(payload)
    return manifest, sha256, parts


def validate_release_manifest(
    manifest: DataReleaseManifest,
    model_package: str,
    model_version: str,
) -> list[str]:
    """Hard checks raise; soft findings are returned as warnings."""
    warnings: list[str] = []
    if "national" not in manifest.default_datasets:
        raise CertificationError(
            "Release manifest declares no national default dataset."
        )
    default = manifest.default_datasets["national"]
    if default not in manifest.artifacts:
        raise CertificationError(
            f"Default dataset {default!r} is not among the manifest artifacts."
        )
    for name, artifact in manifest.artifacts.items():
        if not artifact.revision:
            raise CertificationError(f"Artifact {name!r} has no revision pin.")
        if not artifact.sha256:
            warnings.append(f"artifact {name!r} has no sha256")

    compat = [
        package.specifier
        for package in manifest.compatible_model_packages
        if package.name == model_package
    ]
    pinned = f"=={model_version}"
    if compat and pinned not in compat:
        warnings.append(
            f"{model_package} {model_version} is not among the manifest's "
            f"compatible versions {compat}; certification asserts the pair "
            "anyway — the test suite is the arbiter"
        )
    return warnings


def head_artifact(artifact, token: Optional[str] = None) -> bool:
    # Repo type is not recorded per artifact in the schema; try dataset
    # first (the publishing convention), then model-style.
    for prefix in ("datasets/", ""):
        url = (
            f"https://huggingface.co/{prefix}{artifact.repo_id}/resolve/"
            f"{artifact.revision}/{artifact.path}"
        )
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            response = requests.head(
                url,
                headers=headers,
                timeout=HF_REQUEST_TIMEOUT_SECONDS,
                allow_redirects=True,
            )
        except requests.RequestException:
            continue
        if response.status_code == 200:
            return True
    return False


def build_country_manifest_payload(
    *,
    country: str,
    manifest: DataReleaseManifest,
    manifest_sha256: str,
    uri_parts: dict,
    policyengine_version: str,
    model_package: str,
    model_version: str,
    model_wheel: dict,
) -> dict:
    """Map the data release manifest to the vendored country manifest."""
    default_dataset = manifest.default_datasets["national"]
    default_artifact = manifest.artifacts[default_dataset]
    primary_repo_id = default_artifact.repo_id
    repo_type = uri_parts["repo_type"]

    datasets: dict[str, dict] = {}
    for name, artifact in manifest.artifacts.items():
        payload: dict = {"path": artifact.path, "revision": artifact.revision}
        if artifact.sha256:
            payload["sha256"] = artifact.sha256
        if artifact.repo_id:
            payload["repo_id"] = artifact.repo_id
        datasets[name] = payload

    region_datasets = {}
    raw_regions = manifest.metadata.get("region_datasets")
    if isinstance(raw_regions, dict):
        for region, template in sorted(raw_regions.items()):
            if isinstance(template, dict) and "path_template" in template:
                region_datasets[region] = {"path_template": template["path_template"]}

    certification: dict = {
        "compatibility_basis": COMPATIBILITY_BASIS,
        "certified_for_model_version": model_version,
        "certified_by": CERTIFIED_BY,
    }
    certified_artifact: dict = {
        "data_package": {
            "name": manifest.data_package.name,
            "version": manifest.data_package.version,
        },
        "dataset": default_dataset,
        "uri": default_artifact.uri,
    }
    if default_artifact.sha256:
        certified_artifact["sha256"] = default_artifact.sha256
    build = manifest.build
    if build is not None:
        if build.build_id:
            certification["data_build_id"] = build.build_id
            certified_artifact["build_id"] = build.build_id
        model_build = build.built_with_model_package
        if model_build is not None:
            certification["built_with_model_version"] = model_build.version
            if model_build.git_sha:
                certification["built_with_model_git_sha"] = model_build.git_sha
            if model_build.data_build_fingerprint:
                certification["data_build_fingerprint"] = (
                    model_build.data_build_fingerprint
                )

    return {
        "schema_version": 1,
        "bundle_id": f"{country}-{policyengine_version}",
        "country_id": country,
        "policyengine_version": policyengine_version,
        "model_package": {
            "name": model_package,
            "version": model_version,
            **({"sha256": model_wheel["sha256"]} if model_wheel.get("sha256") else {}),
            **({"wheel_url": model_wheel["url"]} if model_wheel.get("url") else {}),
        },
        "data_package": {
            "name": manifest.data_package.name,
            "version": manifest.data_package.version,
            "repo_id": primary_repo_id,
            "repo_type": repo_type,
            "release_manifest_path": uri_parts["path"],
            "release_manifest_revision": uri_parts["revision"],
        },
        "default_dataset": default_dataset,
        "datasets": datasets,
        "region_datasets": region_datasets,
        "certified_data_artifact": certified_artifact,
        "certification": certification,
    }


def installed_model_version(model_package: str) -> str:
    from importlib.metadata import version

    return version(model_package)


def policyengine_version() -> str:
    from importlib.metadata import version

    return version("policyengine")


def certify_data_release(
    *,
    country: str,
    manifest_uri: str,
    model_version: Optional[str] = None,
    token: Optional[str] = None,
    output_dir: Optional[Path] = None,
    check_artifacts: bool = True,
) -> CertificationResult:
    if country not in COUNTRY_MODEL_PACKAGES:
        raise CertificationError(f"Unknown country {country!r}.")
    model_package = COUNTRY_MODEL_PACKAGES[country]
    model_version = model_version or installed_model_version(model_package)

    manifest, manifest_sha256, uri_parts = fetch_release_manifest(
        manifest_uri, token=token
    )
    warnings = validate_release_manifest(manifest, model_package, model_version)

    default_artifact = manifest.artifacts[manifest.default_datasets["national"]]
    if check_artifacts and not head_artifact(default_artifact, token=token):
        raise CertificationError(
            f"Certified dataset artifact is not reachable: {default_artifact.uri}"
        )

    model_wheel = fetch_pypi_wheel_metadata(model_package, model_version)

    payload = build_country_manifest_payload(
        country=country,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        uri_parts=uri_parts,
        policyengine_version=policyengine_version(),
        model_package=model_package,
        model_version=model_version,
        model_wheel=model_wheel or {},
    )

    if output_dir is None:
        output_dir = Path(str(files("policyengine"))) / "data" / "release_manifests"
    output_path = output_dir / f"{country}.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    return CertificationResult(
        country=country,
        manifest_uri=manifest_uri,
        manifest_sha256=manifest_sha256,
        country_manifest_path=output_path,
        dataset_count=len(payload["datasets"]),
        default_dataset=payload["default_dataset"],
        build_id=payload["certified_data_artifact"].get("build_id"),
        model_package=model_package,
        model_version=model_version,
        warnings=warnings,
    )
