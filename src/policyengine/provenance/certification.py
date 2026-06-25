"""Certify a data release directly from its HF release manifest.

This replaces the policyengine-bundles hop: the data release manifest
(published next to the artifacts, with per-artifact repo/revision/sha256
pins, build provenance, compatibility claims, and region templates) is
the source of truth, and certification derives the vendored country
manifest from it in one step.

The certification asserts that *this* policyengine bundle, with the
model package pinned in ``src/policyengine/data/bundle/manifest.json``,
serves the data release — an assertion the test suite then exercises on the
exact pair.

.. code-block:: python

    from policyengine.provenance.certification import certify_data_release

    result = certify_data_release(
        country="uk",
        data_producer="populace",
        manifest_uri=(
            "hf://dataset/policyengine/populace-uk-private"
            "@populace-uk-2023-0cdbb27-c239dfe51c11-20260615T201302Z"
            "/releases/populace-uk-2023-0cdbb27-c239dfe51c11-20260615T201302Z"
            "/release_manifest.json"
        ),
    )
    print(result.summary())

``scripts/bundle.py certify-data`` is the operator-facing wrapper. Network
access is required (HF manifest fetch + PyPI wheel metadata). Countries whose
data release predates release manifests need a dedicated data-producer strategy
before they can be updated through this path.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

from policyengine.provenance.manifest import (
    HF_REQUEST_TIMEOUT_SECONDS,
    DataReleaseManifest,
    _specifier_matches,
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

CERTIFIED_BY = "policyengine.py bundle certification"
BASIS_BUILT_WITH = "built_with_model_package"
BASIS_PUBLISHER_CLAIM = "compatible_model_packages"
POPULACE_US_SOURCE_COVERAGE_FILE = "us_source_coverage.json"
US_STATE_CODES = (
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "DC",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
)


class CertificationError(ValueError):
    """Raised when a data release cannot be certified."""


@dataclass
class CertificationResult:
    country: str
    data_producer: str
    manifest_uri: str
    manifest_sha256: str
    bundle_path: Path
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
            f"  data-producer: {self.data_producer}",
            f"  wrote: {self.bundle_path}",
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


def default_bundle_source_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "bundle" / "manifest.json"


def https_release_file_url(parts: dict, filename: str) -> str:
    prefix = "datasets/" if parts["repo_type"] == "dataset" else ""
    release_dir = release_manifest_dir(parts)
    return (
        f"https://huggingface.co/{prefix}{parts['repo_id']}/resolve/"
        f"{parts['revision']}/{release_dir}/{filename}"
    )


def release_manifest_dir(parts: dict) -> str:
    return parts["path"].rsplit("/", 1)[0]


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
) -> tuple[str, list[str]]:
    """Hard checks raise; returns ``(compatibility_basis, warnings)``.

    The certification gate (docs/release-bundles.md): a data release may
    be certified for a model version only when the model exactly matches
    the build-time model, or the publisher's ``compatible_model_packages``
    covers it. The publisher-claim basis is recorded and warned about —
    it is the data publisher's assertion, made good only by this repo's
    test suite passing on the pinned pair.
    """
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

    built_with = None
    if manifest.build is not None and manifest.build.built_with_model_package:
        build_pkg = manifest.build.built_with_model_package
        if build_pkg.name == model_package:
            built_with = build_pkg.version

    claim_specifiers = [
        package.specifier
        for package in manifest.compatible_model_packages
        if package.name == model_package
    ]
    claim_matches = any(
        _specifier_matches(model_version, specifier) for specifier in claim_specifiers
    )

    if built_with == model_version:
        return BASIS_BUILT_WITH, warnings
    if claim_matches:
        warnings.append(
            f"certifying {model_package} {model_version} on the publisher's "
            f"compatibility claim {claim_specifiers}; the data was built "
            f"with {built_with or 'an unrecorded model version'} — the test "
            "suite is the arbiter"
        )
        return BASIS_PUBLISHER_CLAIM, warnings
    raise CertificationError(
        f"{model_package} {model_version} matches neither the build-time "
        f"model ({built_with or 'unrecorded'}) nor any publisher "
        f"compatibility claim {claim_specifiers or '(none declared)'}; "
        "a new data build or a published compatibility claim is required."
    )


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


def head_release_file(
    uri_parts: dict, filename: str, token: Optional[str] = None
) -> bool:
    url = https_release_file_url(uri_parts, filename)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = requests.head(
            url,
            headers=headers,
            timeout=HF_REQUEST_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
    except requests.RequestException:
        return False
    return response.status_code == 200


def artifact_path_for_country_manifest(artifact, uri_parts: dict) -> str:
    path = artifact.path
    release_dir = release_manifest_dir(uri_parts)
    if (
        artifact.kind == "diagnostics"
        and artifact.repo_id == uri_parts["repo_id"]
        and artifact.revision == uri_parts["revision"]
        and not path.startswith(f"{release_dir}/")
    ):
        return f"{release_dir}/{path}"
    return path


def artifact_reference_url(
    reference: dict, uri_parts: dict, prefix: str = "datasets/"
) -> str:
    repo_id = reference.get("repo_id") or uri_parts["repo_id"]
    revision = reference.get("revision") or uri_parts["revision"]
    return (
        f"https://huggingface.co/{prefix}{repo_id}/resolve/"
        f"{revision}/{reference['path']}"
    )


def head_artifact_reference(
    reference: dict,
    uri_parts: dict,
    token: Optional[str] = None,
) -> bool:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for prefix in ("datasets/", ""):
        try:
            response = requests.head(
                artifact_reference_url(reference, uri_parts, prefix=prefix),
                headers=headers,
                timeout=HF_REQUEST_TIMEOUT_SECONDS,
                allow_redirects=True,
            )
        except requests.RequestException:
            continue
        if response.status_code == 200:
            return True
    return False


def required_supplemental_release_files(
    country: str,
    manifest: DataReleaseManifest,
    uri_parts: dict,
) -> tuple[str, ...]:
    if (
        country == "us"
        and manifest.data_package.name == "populace-data"
        and uri_parts["repo_id"] == "policyengine/populace-us"
    ):
        return (POPULACE_US_SOURCE_COVERAGE_FILE,)
    return ()


def should_validate_vendored_artifacts(
    country: str,
    manifest: DataReleaseManifest,
    uri_parts: dict,
) -> bool:
    return (
        country == "us"
        and manifest.data_package.name == "populace-data"
        and uri_parts["repo_id"] == "policyengine/populace-us"
    )


def _state_code_from_path(path: str, artifact_prefix: str) -> Optional[str]:
    prefix = artifact_prefix.rstrip("/") + "/"
    if not path.startswith(prefix):
        return None
    remainder = path.removeprefix(prefix)
    if "/" in remainder or not remainder.endswith(".h5"):
        return None
    state_code = remainder.removesuffix(".h5")
    if state_code not in US_STATE_CODES:
        return None
    return state_code


def merge_us_state_release_manifest(
    primary_manifest: DataReleaseManifest,
    state_manifest: DataReleaseManifest,
    *,
    artifact_prefix: str = "states/",
    path_template: str = "states/{state_code}.h5",
) -> DataReleaseManifest:
    """Add legacy US state artifacts to a primary Populace release manifest."""

    primary_payload = primary_manifest.model_dump(mode="json", exclude_none=True)
    merged_artifacts = primary_payload.setdefault("artifacts", {})
    found_states: dict[str, str] = {}
    prefix = artifact_prefix.rstrip("/") + "/"

    for name, artifact in state_manifest.artifacts.items():
        if not name.startswith(prefix) and not artifact.path.startswith(prefix):
            continue
        state_code = _state_code_from_path(artifact.path, artifact_prefix)
        if state_code is None:
            raise CertificationError(
                "US state artifact path must match "
                f"{artifact_prefix}<STATE>.h5; got {artifact.path!r}."
            )
        if not artifact.sha256:
            raise CertificationError(f"US state artifact {name!r} has no sha256.")
        if name in merged_artifacts:
            raise CertificationError(
                f"Regional artifact {name!r} conflicts with the primary manifest."
            )
        if state_code in found_states:
            warnings.warn(
                "Duplicate US state artifact for "
                f"{state_code}: ignoring {name!r}; already using "
                f"{found_states[state_code]!r}.",
                RuntimeWarning,
                stacklevel=2,
            )
            continue
        merged_artifacts[name] = artifact.model_dump(
            mode="json",
            exclude_none=True,
        )
        found_states[state_code] = name

    missing_states = sorted(set(US_STATE_CODES) - set(found_states))
    if missing_states:
        raise CertificationError(
            "Missing US state artifacts: " + ", ".join(missing_states)
        )

    metadata = primary_payload.setdefault("metadata", {})
    region_datasets = metadata.setdefault("region_datasets", {})
    default_dataset = primary_manifest.default_datasets["national"]
    default_artifact = primary_manifest.artifacts[default_dataset]
    region_datasets.setdefault(
        "national",
        {"path_template": default_artifact.path},
    )
    region_datasets["state"] = {"path_template": path_template}

    return DataReleaseManifest.model_validate(primary_payload)


def build_country_manifest_payload(
    *,
    country: str,
    manifest: DataReleaseManifest,
    uri_parts: dict,
    policyengine_version: str,
    model_package: str,
    model_version: str,
    model_wheel: dict,
    compatibility_basis: str = BASIS_BUILT_WITH,
) -> dict:
    """Map the data release manifest to the vendored country manifest."""
    default_dataset = manifest.default_datasets["national"]
    default_artifact = manifest.artifacts[default_dataset]
    # The data package's repo is where the release manifest itself lives —
    # runtime re-fetches resolve against it. Artifacts (including the
    # default) may be inherited from other repos and carry their own pins.
    primary_repo_id = uri_parts["repo_id"]
    repo_type = uri_parts["repo_type"]

    datasets: dict[str, dict] = {}
    for name, artifact in manifest.artifacts.items():
        payload: dict = {
            "path": artifact_path_for_country_manifest(artifact, uri_parts),
            "revision": artifact.revision,
        }
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
        "compatibility_basis": compatibility_basis,
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


def build_bundle_data_release_payload(
    *,
    country_payload: dict,
    data_producer: str,
    manifest_uri: str,
    uri_parts: dict,
    regional_manifest_uri: Optional[str] = None,
    regional_uri_parts: Optional[dict] = None,
) -> dict:
    """Map the country certification payload into bundle ``data_releases``."""
    payload = copy.deepcopy(country_payload)
    certified_artifact = payload.get("certified_data_artifact") or {}
    data_package = payload.get("data_package") or {}
    build_id = certified_artifact.get("build_id") or data_package.get("version")
    payload["data_producer"] = data_producer
    payload["version"] = build_id
    payload["build_id"] = build_id
    payload["source_manifest_uri"] = manifest_uri
    payload["release_manifest_uri"] = https_manifest_url(uri_parts)
    if regional_manifest_uri is not None:
        payload["regional_source_manifest_uri"] = regional_manifest_uri
    if regional_uri_parts is not None:
        payload["regional_release_manifest_uri"] = https_manifest_url(
            regional_uri_parts
        )
    payload["default_dataset_uri"] = certified_artifact.get("uri")
    return payload


class DataProducerCertificationStrategy:
    data_producer: str

    def certify(
        self,
        *,
        country: str,
        manifest_uri: str,
        model_package: str,
        model_version: str,
        token: Optional[str],
        check_artifacts: bool,
        regional_manifest_uri: Optional[str] = None,
        regional_artifact_prefix: str = "states/",
        regional_path_template: str = "states/{state_code}.h5",
    ) -> tuple[dict, str, list[str]]:
        raise NotImplementedError


class LegacyDataProducerCertificationStrategy(DataProducerCertificationStrategy):
    data_producer = "legacy"

    def certify(
        self,
        *,
        country: str,
        manifest_uri: str,
        model_package: str,
        model_version: str,
        token: Optional[str],
        check_artifacts: bool,
        regional_manifest_uri: Optional[str] = None,
        regional_artifact_prefix: str = "states/",
        regional_path_template: str = "states/{state_code}.h5",
    ) -> tuple[dict, str, list[str]]:
        raise CertificationError(
            "Legacy data-producer certification updates are not implemented in "
            "the bundle manifest workflow yet."
        )


class PopulaceDataProducerCertificationStrategy(DataProducerCertificationStrategy):
    data_producer = "populace"

    def certify(
        self,
        *,
        country: str,
        manifest_uri: str,
        model_package: str,
        model_version: str,
        token: Optional[str],
        check_artifacts: bool,
        regional_manifest_uri: Optional[str] = None,
        regional_artifact_prefix: str = "states/",
        regional_path_template: str = "states/{state_code}.h5",
    ) -> tuple[dict, str, list[str]]:
        manifest, manifest_sha256, uri_parts = fetch_release_manifest(
            manifest_uri, token=token
        )
        regional_uri_parts = None
        if regional_manifest_uri is not None:
            if country != "us":
                raise CertificationError(
                    "Regional data release overlays are only supported for US "
                    "Populace certification."
                )
            state_manifest, _, regional_uri_parts = fetch_release_manifest(
                regional_manifest_uri, token=token
            )
            manifest = merge_us_state_release_manifest(
                manifest,
                state_manifest,
                artifact_prefix=regional_artifact_prefix,
                path_template=regional_path_template,
            )
        compatibility_basis, warnings = validate_release_manifest(
            manifest, model_package, model_version
        )

        for filename in required_supplemental_release_files(
            country, manifest, uri_parts
        ):
            if not head_release_file(uri_parts, filename, token=token):
                raise CertificationError(
                    "Required supplemental release file is not reachable: "
                    f"{filename} at {https_release_file_url(uri_parts, filename)}"
                )

        default_artifact = manifest.artifacts[manifest.default_datasets["national"]]
        if check_artifacts and not head_artifact(default_artifact, token=token):
            raise CertificationError(
                f"Certified dataset artifact is not reachable: {default_artifact.uri}"
            )

        model_wheel = fetch_pypi_wheel_metadata(model_package, model_version)
        country_payload = build_country_manifest_payload(
            country=country,
            manifest=manifest,
            uri_parts=uri_parts,
            policyengine_version=policyengine_version(),
            model_package=model_package,
            model_version=model_version,
            model_wheel=model_wheel or {},
            compatibility_basis=compatibility_basis,
        )
        if check_artifacts and should_validate_vendored_artifacts(
            country, manifest, uri_parts
        ):
            for name, reference in country_payload["datasets"].items():
                if not head_artifact_reference(reference, uri_parts, token=token):
                    raise CertificationError(
                        f"Vendored artifact {name!r} is not reachable at "
                        f"{artifact_reference_url(reference, uri_parts)}"
                    )

        return (
            build_bundle_data_release_payload(
                country_payload=country_payload,
                data_producer=self.data_producer,
                manifest_uri=manifest_uri,
                uri_parts=uri_parts,
                regional_manifest_uri=regional_manifest_uri,
                regional_uri_parts=regional_uri_parts,
            ),
            manifest_sha256,
            warnings,
        )


def certification_strategy(
    country: str, data_producer: Optional[str] = None
) -> DataProducerCertificationStrategy:
    producer = data_producer or ("populace" if country == "uk" else "legacy")
    if producer == "populace":
        return PopulaceDataProducerCertificationStrategy()
    if producer == "legacy":
        return LegacyDataProducerCertificationStrategy()
    raise CertificationError(f"Unknown data-producer {producer!r}.")


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
    data_producer: Optional[str] = None,
    model_version: Optional[str] = None,
    token: Optional[str] = None,
    bundle_path: Optional[Path] = None,
    check_artifacts: bool = True,
    regional_manifest_uri: Optional[str] = None,
    regional_artifact_prefix: str = "states/",
    regional_path_template: str = "states/{state_code}.h5",
) -> CertificationResult:
    if country not in COUNTRY_MODEL_PACKAGES:
        raise CertificationError(f"Unknown country {country!r}.")
    model_package = COUNTRY_MODEL_PACKAGES[country]
    model_version = model_version or installed_model_version(model_package)
    strategy = certification_strategy(country, data_producer)

    data_release, manifest_sha256, warnings = strategy.certify(
        country=country,
        manifest_uri=manifest_uri,
        model_package=model_package,
        model_version=model_version,
        token=token,
        check_artifacts=check_artifacts,
        regional_manifest_uri=regional_manifest_uri,
        regional_artifact_prefix=regional_artifact_prefix,
        regional_path_template=regional_path_template,
    )
    bundle_path = bundle_path or default_bundle_source_path()
    bundle = json.loads(bundle_path.read_text())
    bundle.setdefault("data_releases", {})[country] = data_release
    bundle.setdefault("countries", {}).setdefault(country, {})["model_package"] = (
        model_package
    )
    if model_package in bundle.get("packages", {}):
        bundle["packages"][model_package]["version"] = model_version
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")

    return CertificationResult(
        country=country,
        data_producer=strategy.data_producer,
        manifest_uri=manifest_uri,
        manifest_sha256=manifest_sha256,
        bundle_path=bundle_path,
        dataset_count=len(data_release["datasets"]),
        default_dataset=data_release["default_dataset"],
        build_id=data_release["certified_data_artifact"].get("build_id"),
        model_package=model_package,
        model_version=model_version,
        warnings=warnings,
    )
