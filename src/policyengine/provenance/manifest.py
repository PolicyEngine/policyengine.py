import hashlib
import json
import os
import re
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Literal, NoReturn, Optional
from urllib.parse import quote

import requests
from pydantic import BaseModel, Field, PrivateAttr

from policyengine.provenance.bundle_validation import (
    shadowed_dataset_overlays,
    shadowing_overlays_message,
)

HF_REQUEST_TIMEOUT_SECONDS = 30
PYPI_REQUEST_TIMEOUT_SECONDS = 30
# Producer paths for these artifacts are relative to the release directory.
RELEASE_SCOPED_ARTIFACT_KINDS = frozenset({"diagnostics", "evidence"})


class DataReleaseManifestUnavailableError(ValueError):
    """Raised when a data release manifest cannot be fetched or is absent."""


class PackageVersion(BaseModel):
    name: str
    version: str
    sha256: Optional[str] = None
    wheel_url: Optional[str] = None


class DataPackageVersion(PackageVersion):
    repo_id: str
    repo_type: Literal["model", "dataset"] = "model"
    release_manifest_path: str = "release_manifest.json"
    release_manifest_revision: Optional[str] = None


class CompatiblePackage(BaseModel):
    name: str
    specifier: str


CompatibleModelPackage = CompatiblePackage


class BuiltWithModelPackage(PackageVersion):
    git_sha: Optional[str] = None
    data_build_fingerprint: Optional[str] = None


class DataBuildInfo(BaseModel):
    build_id: Optional[str] = None
    cut_tag: Optional[str] = None
    """The immutable tag of one cut of a release line. Microcosm keeps
    ``build_id`` equal to the line name for every cut, so the cut tag is what
    tells two cuts apart (see ``release_build_id``)."""
    built_at: Optional[str] = None
    built_with_core_package: Optional[PackageVersion] = None
    built_with_model_package: Optional[BuiltWithModelPackage] = None


def release_build_id(build: Optional[DataBuildInfo]) -> Optional[str]:
    """Identify one data build: its cut tag when it has one, else its build id."""
    if build is None:
        return None
    return build.cut_tag or build.build_id


class ArtifactPathReference(BaseModel):
    path: str
    revision: Optional[str] = None
    sha256: Optional[str] = None
    metadata_sha256: Optional[str] = None
    # Set when the artifact is supplied by a different package than the
    # country release manifest's primary data package.
    data_package_name: Optional[str] = None
    # Set when the artifact lives outside the data package's repo (inherited
    # datasets keep their original repo + revision pins).
    repo_id: Optional[str] = None
    repo_type: Optional[Literal["model", "dataset"]] = None


class ArtifactPathTemplate(BaseModel):
    path_template: str

    def resolve(self, **kwargs: str) -> str:
        return self.path_template.format(**kwargs)


class PreservationMirror(BaseModel):
    """Durable mirror of a data artifact on a preservation-grade host.

    The primary host for PolicyEngine calibrated h5 files is Hugging
    Face, which is fast and integrated with the Python client but does
    not publish a preservation commitment. A ``PreservationMirror``
    records an additional copy on a host that *does* publish one
    (Zenodo, the Internet Archive, or an institutional archive), so a
    TRO citation URL can fall back if the primary location is ever
    unavailable.
    """

    kind: str
    """Short identifier for the preservation host: ``zenodo``, ``internet_archive``, ``archival_gcs``, etc."""

    url: str
    """Dereferenceable HTTPS URL for the mirrored artifact."""

    doi: Optional[str] = None
    """DOI for the preservation deposit, when the host assigns one (Zenodo always does)."""

    sha256: Optional[str] = None
    """Content hash of the mirrored bytes. When equal to the primary artifact's ``sha256``, the mirror is byte-identical and the hash can be reused for verification."""

    deposited_at: Optional[str] = None
    """ISO 8601 timestamp of when the mirror was deposited, if known."""


class DataReleaseArtifact(BaseModel):
    kind: str
    path: str
    repo_id: str
    revision: str
    repo_type: Optional[Literal["model", "dataset"]] = None
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    preservation_mirrors: list[PreservationMirror] = Field(default_factory=list)
    """Durable secondary locations for this artifact. Populated when the
    release pipeline mirrors the artifact to a preservation-grade host.
    Empty when no preservation deposit exists yet."""

    @property
    def uri(self) -> str:
        return build_hf_uri(
            repo_id=self.repo_id,
            path_in_repo=self.path,
            revision=self.revision,
        )


class DataReleaseManifest(BaseModel):
    _source_is_local: bool = PrivateAttr(default=False)
    schema_version: int
    data_package: PackageVersion
    dataset_role: Optional[str] = None
    """Producer-declared role for a release that supplements a default release."""
    is_default: Optional[bool] = None
    """Whether the producer intends this release to provide default datasets."""
    compatible_model_packages: list[CompatiblePackage] = Field(default_factory=list)
    compatible_core_packages: list[CompatiblePackage] = Field(default_factory=list)
    default_datasets: dict[str, str] = Field(default_factory=dict)
    build: Optional[DataBuildInfo] = None
    artifacts: dict[str, DataReleaseArtifact] = Field(default_factory=dict)
    preservation_dois: list[str] = Field(default_factory=list)
    """DOIs covering the release as a whole (Zenodo concept: one DOI
    can enclose the full set of artifacts published together). Distinct
    from per-artifact DOIs on ``DataReleaseArtifact.preservation_mirrors``.
    Populated when the release pipeline mirrors to a DOI-minting host."""
    metadata: dict = Field(default_factory=dict)
    """Producer-declared extras (e.g. ``region_datasets`` path templates
    consumed by certification)."""
    source_sha256: Optional[str] = Field(default=None, exclude=True)
    """Byte sha256 of the fetched manifest before runtime URI rewrites."""


class DataCertification(BaseModel):
    compatibility_basis: str
    certified_for_model_version: str
    data_build_id: Optional[str] = None
    built_with_model_version: Optional[str] = None
    built_with_model_git_sha: Optional[str] = None
    data_build_fingerprint: Optional[str] = None
    certified_by: Optional[str] = None
    certified_for_core_version: Optional[str] = None
    #: How the certificate covers policyengine-core. ``certified``: it names
    #: the core it was certified for (``certified_for_core_version``), and the
    #: bundle's core pin must equal it. ``bundle_pin``: it certifies whatever
    #: core the bundle pins, without holding the pin to the data release's
    #: core claims; certification and the strict check warn when the pin is
    #: outside them. Absent in certificates from before October 2026, which
    #: follow the pin the same way.
    core_binding: Optional[Literal["certified", "bundle_pin"]] = None
    qualification_pair_id: Optional[str] = None
    qualification_ledger_url: Optional[str] = None


#: Bases whose runtime model legitimately differs from the data's build-time
#: model, so the build fingerprint is not expected to match.
CLAIM_BASED_COMPATIBILITY = frozenset(
    {
        "legacy_compatible_model_package",
        "qualified_exact_pair",
        "legacy_compatible_model_package_local_manifest",
        "qualified_exact_pair_local_manifest",
    }
)


class CertifiedDataArtifact(BaseModel):
    data_package: Optional[PackageVersion] = None
    dataset: str
    uri: str
    sha256: Optional[str] = None
    build_id: Optional[str] = None


RegionalReleaseKind = Literal["local_area", "area_coded_national"]


class CountryReleaseManifest(BaseModel):
    schema_version: int = 1
    bundle_id: Optional[str] = None
    published_at: Optional[str] = None
    country_id: str
    policyengine_version: str
    model_package: PackageVersion
    data_package: DataPackageVersion
    default_dataset: str
    datasets: dict[str, ArtifactPathReference] = Field(default_factory=dict)
    region_datasets: dict[str, ArtifactPathTemplate] = Field(default_factory=dict)
    regional_release_kind: Optional[RegionalReleaseKind] = None
    """How certification routed the local region types, when it did:
    ``local_area`` for a non-default local-area release, and
    ``area_coded_national`` for another release's national dataset that
    carries area codes (and its area weight matrices)."""
    certified_data_artifact: Optional[CertifiedDataArtifact] = None
    certification: Optional[DataCertification] = None
    source_sha256: Optional[str] = Field(default=None, exclude=True)
    """Byte sha256 of the bundled manifest before Pydantic normalization."""

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


def https_dataset_uri(
    repo_id: str,
    path_in_repo: str,
    revision: str,
    *,
    repo_type: str = "model",
) -> str:
    """Return a dereferenceable HTTPS URI for a Hugging Face dataset artifact."""
    prefix = "datasets/" if repo_type == "dataset" else ""
    return (
        f"https://huggingface.co/{prefix}{repo_id}/resolve/"
        f"{quote(revision, safe='')}/{quote(path_in_repo)}"
    )


def hugging_face_auth_headers() -> dict[str, str]:
    """Return authentication headers for Hugging Face requests."""

    token = (
        os.environ.get("HUGGING_FACE_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    )
    return {"Authorization": f"Bearer {token}"} if token else {}


def _artifact_revision(data_package: "DataPackageVersion") -> str:
    return data_package.release_manifest_revision or data_package.version


def https_release_manifest_uri(data_package: "DataPackageVersion") -> str:
    """Return a dereferenceable HTTPS URI for a data release manifest."""
    revision = _artifact_revision(data_package)
    # Dataset-type repos resolve under /datasets/; model repos at the root.
    repo_type = getattr(data_package, "repo_type", None) or "model"
    prefix = "datasets/" if repo_type == "dataset" else ""
    return (
        f"https://huggingface.co/{prefix}{data_package.repo_id}/resolve/"
        f"{revision}/{data_package.release_manifest_path}"
    )


@lru_cache
def fetch_pypi_wheel_metadata(name: str, version: str) -> dict[str, Optional[str]]:
    """Fetch wheel sha256 and URL from PyPI for a package version.

    Returns a dict with ``sha256`` and ``url`` keys. Missing keys are
    returned as ``None`` rather than raising, so TRO construction can
    degrade gracefully when PyPI is unreachable or the package lacks
    a wheel distribution.
    """
    response = requests.get(
        f"https://pypi.org/pypi/{name}/{version}/json",
        timeout=PYPI_REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        return {"sha256": None, "url": None}
    payload = response.json()
    urls = payload.get("urls") or []
    for entry in urls:
        if entry.get("packagetype") == "bdist_wheel":
            return {
                "sha256": entry.get("digests", {}).get("sha256"),
                "url": entry.get("url"),
            }
    if urls:
        entry = urls[0]
        return {
            "sha256": entry.get("digests", {}).get("sha256"),
            "url": entry.get("url"),
        }
    return {"sha256": None, "url": None}


DATASET_OVERLAYS_KEY = "dataset_overlays"


def _apply_dataset_overlays(
    country_id: str,
    release_payload: dict,
    bundle: dict,
) -> dict:
    """Merge hand-curated ``dataset_overlays`` into the certified datasets.

    ``data_releases.{country}`` is regenerated wholesale by
    ``certify_data_release`` every time a release is certified, so a
    certified dataset always originates from the certified release
    manifest. ``dataset_overlays.{country}`` is a sibling, hand-maintained
    registry of *additional* named datasets that resolution should expose
    without ever certifying them as the default — for example a staged
    artifact published in its own immutable release (see
    ``docs/release-bundles.md``). Certification keeps every overlay except
    one whose name the new release certifies itself, which it removes and
    reports; re-add such an overlay if a later release stops certifying it.

    Overlays are strictly additive (``shadowed_dataset_overlays``): an overlay
    may not shadow the certified default dataset or any certified dataset
    entry, so it can never alter default resolution.
    """
    overlays = (bundle.get(DATASET_OVERLAYS_KEY) or {}).get(country_id) or {}
    if not overlays:
        return release_payload

    shadowed = shadowed_dataset_overlays(release_payload, overlays)
    if shadowed:
        raise ValueError(shadowing_overlays_message(country_id, shadowed))
    certified_datasets = dict(release_payload.get("datasets") or {})
    certified_datasets.update(overlays)

    return {**release_payload, "datasets": certified_datasets}


@lru_cache
def get_release_manifest(country_id: str) -> CountryReleaseManifest:
    manifest_path = files("policyengine").joinpath("data", "bundle", "manifest.json")
    if not manifest_path.is_file():
        raise ValueError("No bundled PolicyEngine bundle manifest found.")

    source_bytes = manifest_path.read_text().encode()
    bundle = json.loads(source_bytes)
    try:
        release_payload = bundle["data_releases"][country_id]
    except KeyError as exc:
        raise ValueError(f"No bundled data release for country '{country_id}'") from exc
    release_payload = _apply_dataset_overlays(country_id, release_payload, bundle)
    manifest = CountryReleaseManifest.model_validate(release_payload)
    manifest.source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    return manifest


def _tro_nodes_with_id(value: object, node_id: str) -> list[dict]:
    """Collect node definitions and references wherever JSON-LD nests them."""
    nodes: list[dict] = []
    if isinstance(value, dict):
        if value.get("@id") == node_id:
            nodes.append(value)
        for child in value.values():
            nodes.extend(_tro_nodes_with_id(child, node_id))
    elif isinstance(value, list):
        for child in value:
            nodes.extend(_tro_nodes_with_id(child, node_id))
    return nodes


def bundled_data_release_manifest_sha256(country_id: str) -> str:
    """Read the manifest's byte digest from the installed country bundle TRO.

    The artifact and its arrangement must describe the release this bundle
    serves. All assertions for the artifact's JSON-LD identifier must agree,
    including definitions outside the inline composition. A missing or stale
    sidecar cannot authorise a local manifest.
    """
    country_manifest = get_release_manifest(country_id)
    tro_path = files("policyengine").joinpath(
        "data", "bundle", f"{country_id}.trace.tro.jsonld"
    )
    artifact_id = "composition/1/artifact/data_release_manifest"
    try:
        tro = json.loads(tro_path.read_bytes())
        artifacts = [
            artifact
            for node in tro["@graph"]
            for artifact in node.get("trov:hasComposition", {}).get(
                "trov:hasArtifact", []
            )
            if artifact.get("@id") == artifact_id
        ]
        locations = [
            location.get("trov:hasLocation")
            for node in tro["@graph"]
            for arrangement in node.get("trov:hasArrangement", [])
            for location in arrangement.get("trov:hasArtifactLocation", [])
            if location.get("trov:hasArtifact", {}).get("@id") == artifact_id
        ]
        digest = artifacts[0].get("trov:sha256") if len(artifacts) == 1 else None
        if (
            not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None
            or locations != [https_release_manifest_uri(country_manifest.data_package)]
        ):
            raise ValueError("missing, ambiguous, malformed, or stale manifest pin")
        asserted_digests = set()
        for node in _tro_nodes_with_id(tro, artifact_id):
            if "trov:sha256" not in node:
                continue
            assertion = node["trov:sha256"]
            if (
                not isinstance(assertion, str)
                or re.fullmatch(r"[0-9a-fA-F]{64}", assertion) is None
            ):
                raise ValueError("malformed manifest pin assertion")
            asserted_digests.add(assertion.lower())
        if asserted_digests != {digest.lower()}:
            raise ValueError("conflicting manifest pin assertions")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError(
            f"Cannot use a local data release manifest for country '{country_id}': "
            f"no valid SHA-256 pin in the installed bundle TRO {tro_path}. "
            "Expected SHA-256: unavailable; actual SHA-256: unavailable."
        ) from exc
    return digest.lower()


def _load_data_release_manifest(country_id: str) -> DataReleaseManifest:
    """Load an explicitly configured, bundle-pinned file or the cached fetch.

    Local files are read and verified on every call, including after a remote
    manifest was cached. Configure the setting before importing country models.
    """
    env_name = f"POLICYENGINE_{country_id.upper()}_DATA_MANIFEST_FILE"
    local_file = os.environ.get(env_name)
    if local_file is None:
        return _fetch_data_release_manifest(country_id)

    expected = bundled_data_release_manifest_sha256(country_id)
    try:
        source_bytes = Path(local_file).expanduser().read_bytes()
    except (OSError, ValueError, RuntimeError) as exc:
        raise ValueError(
            f"Cannot read {env_name}={local_file!r}: {exc}. "
            f"Expected SHA-256: {expected}; actual SHA-256: unavailable."
        ) from exc
    actual = hashlib.sha256(source_bytes).hexdigest()
    if actual != expected:
        raise ValueError(
            f"Local data release manifest {env_name}={local_file!r} "
            f"does not match the installed bundle. Expected SHA-256: {expected}; "
            f"actual SHA-256: {actual}."
        )
    manifest = DataReleaseManifest.model_validate_json(source_bytes)
    manifest.source_sha256 = actual
    manifest._source_is_local = True
    country_manifest = get_release_manifest(country_id)
    _apply_release_revision(manifest, country_manifest)
    _validate_bundle_artifacts(manifest, country_manifest)
    return manifest


@lru_cache
def _fetch_data_release_manifest(country_id: str) -> DataReleaseManifest:
    country_manifest = get_release_manifest(country_id)

    try:
        response = requests.get(
            https_release_manifest_uri(country_manifest.data_package),
            headers=hugging_face_auth_headers(),
            timeout=HF_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise DataReleaseManifestUnavailableError(
            "Could not fetch the data release manifest from Hugging Face."
        ) from exc

    if response.status_code in (401, 403):
        raise DataReleaseManifestUnavailableError(
            "Could not fetch the data release manifest from Hugging Face. "
            "If this country uses a private data repo, set HUGGING_FACE_TOKEN."
        )
    if response.status_code == 404:
        raise DataReleaseManifestUnavailableError(
            "No data release manifest was published for this data package."
        )
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DataReleaseManifestUnavailableError(
            "Could not fetch the data release manifest from Hugging Face."
        ) from exc
    data_release_manifest = DataReleaseManifest.model_validate_json(response.text)
    source_bytes = response.content
    if not isinstance(source_bytes, bytes):
        source_bytes = response.text.encode("utf-8")
    data_release_manifest.source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    _apply_release_revision(data_release_manifest, country_manifest)
    _validate_bundle_artifacts(data_release_manifest, country_manifest)
    return data_release_manifest


def _apply_release_revision(
    data_release_manifest: DataReleaseManifest,
    country_manifest: CountryReleaseManifest,
) -> DataReleaseManifest:
    release_revision = country_manifest.data_package.release_manifest_revision
    if release_revision is not None:
        for artifact in data_release_manifest.artifacts.values():
            if (
                artifact.repo_id == country_manifest.data_package.repo_id
                and artifact.revision == country_manifest.data_package.version
            ):
                artifact.revision = release_revision
    return data_release_manifest


def artifact_path_for_country_manifest(
    artifact: DataReleaseArtifact, uri_parts: dict
) -> str:
    """Resolve producer-relative evidence paths as bundle certification does."""
    path = artifact.path
    release_dir = uri_parts["path"].rsplit("/", 1)[0]
    if (
        artifact.kind in RELEASE_SCOPED_ARTIFACT_KINDS
        and artifact.repo_id == uri_parts["repo_id"]
        and artifact.revision == uri_parts["revision"]
        and not path.startswith(f"{release_dir}/")
    ):
        return f"{release_dir}/{path}"
    return path


def _validate_bundle_artifacts(
    manifest: DataReleaseManifest, country: CountryReleaseManifest
) -> None:
    """Bind a loaded manifest to the artifacts this installed bundle serves.

    Run after revision rewriting. Regional releases and additive overlays may
    supply records absent from the primary manifest; every overlapping record
    must agree, and the certified/default artifact must always be present.
    """

    def refuse(dataset: str, detail: str) -> NoReturn:
        raise ValueError(
            f"Data release manifest artifact {dataset!r} does not match the "
            f"installed bundle for country {country.country_id!r}: {detail}."
        )

    default = country.default_dataset
    declared_default = manifest.default_datasets.get("national")
    if declared_default is not None and declared_default != default:
        refuse(default, f"manifest declares default {declared_default!r}")
    if default not in manifest.artifacts:
        refuse(default, "missing default dataset artifact")
    certified = country.certified_data_artifact
    if certified is not None:
        artifact = manifest.artifacts.get(certified.dataset)
        if artifact is None:
            refuse(certified.dataset, "missing certified dataset artifact")
        try:
            location, revision = certified.uri.removeprefix("hf://").rsplit("@", 1)
            owner, repo, path = location.split("/", 2)
        except ValueError:
            refuse(certified.dataset, "invalid bundled certified artifact URI")
        expected_identity = (f"{owner}/{repo}", path, revision)
        actual_identity = (artifact.repo_id, artifact.path, artifact.revision)
        if (
            not certified.uri.startswith("hf://")
            or actual_identity != expected_identity
        ):
            refuse(
                certified.dataset,
                f"expected {expected_identity!r}, got {actual_identity!r}",
            )
        if certified.sha256 is not None and artifact.sha256 != certified.sha256:
            refuse(certified.dataset, "certified SHA-256 pin differs")
    if default not in country.datasets and (
        certified is None or certified.dataset != default
    ):
        refuse(default, "missing bundled default artifact record")

    uri_parts = {
        "repo_id": country.data_package.repo_id,
        "revision": _artifact_revision(country.data_package),
        "path": country.data_package.release_manifest_path,
    }
    for name, artifact in manifest.artifacts.items():
        reference = country.datasets.get(name)
        if reference is None:
            continue
        expected_identity = (
            reference.repo_id or country.data_package.repo_id,
            reference.path,
            reference.revision or _artifact_revision(country.data_package),
        )
        actual_identity = (
            artifact.repo_id,
            artifact_path_for_country_manifest(artifact, uri_parts),
            artifact.revision,
        )
        if actual_identity != expected_identity:
            refuse(name, f"expected {expected_identity!r}, got {actual_identity!r}")
        if (artifact.repo_type or country.data_package.repo_type) != (
            reference.repo_type or country.data_package.repo_type
        ):
            refuse(name, "repository type differs")
        if reference.sha256 is not None and artifact.sha256 != reference.sha256:
            refuse(name, "managed SHA-256 pin differs")


class _DataReleaseManifestLoader:
    """Callable loader retaining the fetched manifest's typed cache controls."""

    def __call__(self, country_id: str) -> DataReleaseManifest:
        return _load_data_release_manifest(country_id)

    cache_clear = staticmethod(_fetch_data_release_manifest.cache_clear)
    cache_info = staticmethod(_fetch_data_release_manifest.cache_info)


get_data_release_manifest = _DataReleaseManifestLoader()


def _specifier_matches(version: str, specifier: str) -> bool:
    """Match a PEP 440 version specifier (``==``, ``>=``, ``<``, ``,``-joined)."""
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version

    try:
        return Version(version) in SpecifierSet(specifier)
    except (InvalidSpecifier, InvalidVersion):
        return False


def _runtime_core_is_certified(
    certification: DataCertification, runtime_core_version: Optional[str]
) -> bool:
    """Whether the running core is the one an exact-pair certificate tested.

    Other bases make no claim about the core at run time. An exact pair was
    tested with one core, so it holds only for that core.
    """

    if certification.compatibility_basis not in {
        "qualified_exact_pair",
        "qualified_exact_pair_local_manifest",
    }:
        return True
    if runtime_core_version is None:
        from importlib import metadata

        try:
            runtime_core_version = metadata.version("policyengine-core")
        except metadata.PackageNotFoundError:
            return False
    return certification.certified_for_core_version == runtime_core_version


def certify_data_release_compatibility(
    country_id: str,
    runtime_model_version: str,
    runtime_data_build_fingerprint: Optional[str] = None,
    runtime_core_version: Optional[str] = None,
) -> DataCertification:
    country_manifest = get_release_manifest(country_id)
    try:
        data_release_manifest = get_data_release_manifest(country_id)
    except DataReleaseManifestUnavailableError as exc:
        bundled_certification = country_manifest.certification
        if bundled_certification is not None:
            if (
                runtime_data_build_fingerprint is not None
                and bundled_certification.data_build_fingerprint is not None
                and bundled_certification.compatibility_basis
                not in CLAIM_BASED_COMPATIBILITY
                and runtime_data_build_fingerprint
                != bundled_certification.data_build_fingerprint
            ):
                raise ValueError(
                    "Runtime data build fingerprint does not match the bundled "
                    "data certification."
                )
            if (
                bundled_certification.certified_for_model_version
                == runtime_model_version
                and _runtime_core_is_certified(
                    bundled_certification, runtime_core_version
                )
            ):
                return bundled_certification
            return DataCertification(
                compatibility_basis="unverified_data_release_manifest_unavailable",
                certified_for_model_version=runtime_model_version,
                data_build_id=bundled_certification.data_build_id,
                built_with_model_version=(
                    bundled_certification.built_with_model_version
                ),
                built_with_model_git_sha=(
                    bundled_certification.built_with_model_git_sha
                ),
                data_build_fingerprint=(bundled_certification.data_build_fingerprint),
                certified_by=bundled_certification.certified_by,
            )
        raise exc

    certification = _certify_available_data_release(
        country_id,
        country_manifest,
        data_release_manifest,
        runtime_model_version,
        runtime_data_build_fingerprint,
        runtime_core_version,
    )
    if data_release_manifest._source_is_local:
        return certification.model_copy(
            update={
                "compatibility_basis": (
                    f"{certification.compatibility_basis}_local_manifest"
                )
            }
        )
    return certification


def _certify_available_data_release(
    country_id: str,
    country_manifest: CountryReleaseManifest,
    data_release_manifest: DataReleaseManifest,
    runtime_model_version: str,
    runtime_data_build_fingerprint: Optional[str],
    runtime_core_version: Optional[str],
) -> DataCertification:
    # A remote build-model, fingerprint or publisher claim cannot broaden an
    # exact-pair certificate beyond the model, core and recorded data build
    # that qualification tested. Check them before any acceptance path returns.
    bundled_certification = country_manifest.certification
    # Named as certification names it: the cut tag when the release has one.
    remote_build_id = release_build_id(data_release_manifest.build)
    if (
        bundled_certification is not None
        and bundled_certification.compatibility_basis == "qualified_exact_pair"
    ):
        if bundled_certification.certified_for_model_version != runtime_model_version:
            raise ValueError(
                "Data release manifest is not certified for the runtime model "
                f"version {runtime_model_version} in country '{country_id}'; "
                "the exact pair requires "
                f"{bundled_certification.certified_for_model_version}."
            )
        if not _runtime_core_is_certified(bundled_certification, runtime_core_version):
            raise ValueError(
                "Data release manifest is not certified for the runtime core "
                f"version {runtime_core_version} in country '{country_id}'; "
                "the exact pair requires "
                f"{bundled_certification.certified_for_core_version}."
            )
        if (
            bundled_certification.data_build_id is not None
            and bundled_certification.data_build_id != remote_build_id
        ):
            raise ValueError(
                "Data release manifest is not certified for the remote data "
                f"build {remote_build_id} in country '{country_id}'; the exact "
                f"pair requires {bundled_certification.data_build_id}."
            )
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
            data_build_id=release_build_id(data_release_manifest.build),
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
            data_build_id=release_build_id(data_release_manifest.build),
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
                data_build_id=release_build_id(data_release_manifest.build),
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

    # An automated qualification of exactly this model and data build: the
    # bundled certificate names the pair, and the ledger evidence for it is
    # enforced when the bundle is built (tests/test_certification_evidence.py).
    bundled_certification = country_manifest.certification
    if (
        bundled_certification is not None
        and bundled_certification.compatibility_basis == "qualified_exact_pair"
        and bundled_certification.certified_for_model_version == runtime_model_version
        and bundled_certification.qualification_pair_id is not None
        and bundled_certification.data_build_id == remote_build_id
        and _runtime_core_is_certified(bundled_certification, runtime_core_version)
    ):
        return bundled_certification

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
            repo_id=path_reference.repo_id or manifest.data_package.repo_id,
            path_in_repo=path_reference.path,
            revision=path_reference.revision
            or _artifact_revision(manifest.data_package),
        )

    local_path = Path(dataset).expanduser()
    if local_path.exists():
        return str(local_path)

    data_release_manifest = get_data_release_manifest(country_id)
    artifact = data_release_manifest.artifacts.get(dataset)
    if artifact is None:
        raise ValueError(
            f"Unknown dataset '{dataset}' for country '{country_id}'. "
            f"Known datasets: {sorted(manifest.datasets)}"
        )

    return artifact.uri


def resolve_managed_dataset_reference(
    country_id: str,
    dataset: Optional[str] = None,
    *,
    allow_unmanaged: bool = False,
) -> str:
    """Resolve a dataset reference under policyengine.py bundle enforcement.

    Managed mode pins dataset selection to the bundled `policyengine.py`
    release manifest. Callers can:

    - omit `dataset` to use the certified default dataset for the bundle
    - pass a logical dataset name present in the bundled/data-release manifests

    Direct URLs or raw Hugging Face references are treated as unmanaged unless
    `allow_unmanaged=True` is set explicitly.
    """

    manifest = get_release_manifest(country_id)
    if dataset is None:
        return manifest.default_dataset_uri

    if dataset in manifest.datasets:
        return resolve_dataset_reference(country_id, dataset)

    local_path = Path(dataset).expanduser()
    if local_path.exists():
        if allow_unmanaged:
            return str(local_path)
        raise ValueError(
            "Explicit local dataset paths bypass the policyengine.py release "
            "bundle. Pass a manifest dataset name or omit `dataset` to use the "
            "certified default dataset. Set `allow_unmanaged=True` only if you "
            "intend to bypass bundle enforcement."
        )

    if "://" in dataset:
        if dataset == manifest.default_dataset_uri:
            return dataset
        if allow_unmanaged:
            return dataset
        raise ValueError(
            "Explicit dataset URIs bypass the policyengine.py release bundle. "
            "Pass a manifest dataset name or omit `dataset` to use the certified "
            "default dataset. Set `allow_unmanaged=True` only if you intend to "
            "bypass bundle enforcement."
        )

    if allow_unmanaged:
        return resolve_dataset_reference(country_id, dataset)
    raise ValueError(
        f"Unknown managed dataset {dataset!r} for country {country_id!r}. "
        f"Known bundled datasets: {sorted(manifest.datasets)}. Set "
        "`allow_unmanaged=True` only if you intend to resolve a dataset "
        "outside the policyengine.py release bundle."
    )


def dataset_logical_name(dataset: str) -> str:
    return Path(dataset.rsplit("@", 1)[0]).stem


def resolve_default_datasets(country_id: str) -> list[str]:
    manifest = get_release_manifest(country_id)
    return list(manifest.datasets.keys())


def region_dataset_name(country_id: str, region_type: str) -> Optional[str]:
    """The certified dataset that ``region_type`` regions are routed to, if any."""

    manifest = get_release_manifest(country_id)
    template = manifest.region_datasets.get(region_type)
    if template is None:
        return None
    return next(
        (
            name
            for name, reference in manifest.datasets.items()
            if reference.path == template.path_template
        ),
        None,
    )


def uk_area_dataset_hint(region_type: str) -> str:
    """A sentence naming the dataset whose households carry an area's codes.

    The Microcosm national default has no constituency or local-authority
    codes; the local-area release the bundle routes those regions to does.
    """

    try:
        name = region_dataset_name("uk", region_type)
    except ValueError:
        return ""
    if name is None:
        return ""
    return (
        f"The certified bundle routes {region_type} regions to the dataset "
        f"{name!r}, whose households carry these codes: run the simulations "
        "on that dataset."
    )


def resolve_region_dataset_path(
    country_id: str,
    region_type: str,
    **kwargs: str,
) -> Optional[str]:
    manifest = get_release_manifest(country_id)
    template = manifest.region_datasets.get(region_type)
    if template is None:
        return None

    resolved_path = template.resolve(**kwargs)
    if "://" in resolved_path:
        return resolved_path

    # Region datasets may be inherited artifacts pinned to a different
    # repo + revision than the data package; prefer the artifact pin.
    reference = next(
        (ref for ref in manifest.datasets.values() if ref.path == resolved_path),
        None,
    )
    if reference is not None:
        return build_hf_uri(
            repo_id=reference.repo_id or manifest.data_package.repo_id,
            path_in_repo=reference.path,
            revision=reference.revision or _artifact_revision(manifest.data_package),
        )

    return build_hf_uri(
        repo_id=manifest.data_package.repo_id,
        path_in_repo=resolved_path,
        revision=_artifact_revision(manifest.data_package),
    )
