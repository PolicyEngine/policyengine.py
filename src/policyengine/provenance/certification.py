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
            "@microcosm-uk-2024-25-national-20261002T230158Z-5c6b3f68"
            "/releases/microcosm-uk-2024-25-national/release_manifest.json"
        ),
    )
    print(result.summary())

Pin the cut tag (``@<cut-tag>``), never a branch: a release line's directory
(``releases/<release-id>/``) is rewritten by each cut.

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
from typing import Literal, Optional, cast, get_args

import requests

from policyengine.data.uk_geography_assets import (
    CONSTITUENCY_ASSET_SPEC,
    LOCAL_AUTHORITY_ASSET_SPEC,
)
from policyengine.provenance.manifest import (
    HF_REQUEST_TIMEOUT_SECONDS,
    DataReleaseArtifact,
    DataReleaseManifest,
    RegionalReleaseKind,
    _specifier_matches,
    fetch_pypi_wheel_metadata,
    release_build_id,
)

MANIFEST_URI_PATTERN = re.compile(
    r"^hf://(?P<repo_type>dataset|model)/(?P<repo_id>[^@]+)@(?P<revision>[^/]+)"
    r"/(?P<path>.+)$"
)

CertifiedCountry = Literal["us", "uk"]
COUNTRY_MODEL_PACKAGES: dict[CertifiedCountry, str] = {
    "us": "policyengine-us",
    "uk": "policyengine-uk",
}

CERTIFIED_BY = "policyengine.py bundle certification"
BASIS_BUILT_WITH = "built_with_model_package"
# Must match the runtime claims basis in provenance/manifest.py: the offline
# fallback there exempts exactly this string from the fingerprint identity
# check, so a claims-certified bundle stays importable without network access.
BASIS_PUBLISHER_CLAIM = "legacy_compatible_model_package"
# The pair passed policyengine.py's automated candidate qualification. The
# claim is exact (``==`` model and core versions, one data release) and is
# valid only with a promotable qualification receipt for ``qualification_pair_id``
# in the ledger; ``tests/test_certification_evidence.py`` refuses it otherwise.
BASIS_QUALIFIED_PAIR = "qualified_exact_pair"
QUALIFICATION_LEDGER_URL = (
    "https://github.com/PolicyEngine/policyengine.py/tree/uk-qualification-ledger"
)
POPULACE_US_SOURCE_COVERAGE_FILE = "us_source_coverage.json"
# The Populace US producer publishes under `microcosm-data` since the
# source-enrichment releases; `populace-data` is its earlier name. Both denote
# the same producer, so every Populace-specific rule below must accept either.
POPULACE_DATA_PACKAGES = frozenset({"populace-data", "microcosm-data"})
# The Hugging Face repos each country's Populace/Microcosm releases publish to.
POPULACE_RELEASE_REPOS = {
    "us": "policyengine/populace-us",
    "uk": "policyengine/populace-uk-private",
}
# Region types a regional release serves. Their regions load the routed dataset
# and keep row-filtering it on their own geography column.
LOCAL_AREA_REGION_TYPES: dict[CertifiedCountry, tuple[str, ...]] = {
    "us": ("state", "congressional_district"),
    "uk": ("constituency", "local_authority"),
}
REGIONAL_RELEASE_KINDS: tuple[RegionalReleaseKind, ...] = get_args(RegionalReleaseKind)
# A UK area-coded national release (the enhanced FRS) serves constituency and
# local-authority runs with these weight matrices as well as its households.
# Consumers bind a matrix only to the release of the dataset it reweights, so
# they travel with that dataset.
UK_AREA_WEIGHT_MATRIX_PATHS = (
    CONSTITUENCY_ASSET_SPEC.weight_matrix_filename,
    LOCAL_AUTHORITY_ASSET_SPEC.weight_matrix_filename,
)
# Artifact kinds published beside the release manifest rather than at the repo
# root, so their manifest paths are relative to the release directory.
RELEASE_SCOPED_ARTIFACT_KINDS = frozenset({"diagnostics", "evidence"})
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
    *,
    core_version: Optional[str] = None,
    qualified_pair_id: Optional[str] = None,
) -> tuple[str, list[str]]:
    """Hard checks raise; returns ``(compatibility_basis, warnings)``.

    The certification gate (docs/release-bundles.md): a data release may
    be certified for a model version only when the model exactly matches
    the build-time model, the publisher's ``compatible_model_packages``
    covers it, or (``qualified_pair_id``) policyengine.py's automated
    qualification tested exactly this model, core and data release. The
    publisher-claim basis is recorded and warned about — it is the data
    publisher's assertion, made good only by this repo's test suite passing
    on the pinned pair. A qualified pair is never widened into a range.

    When ``core_version`` is given, the core must also be the build-time
    core, be covered by ``compatible_core_packages``, or be part of the
    qualified pair. A core admitted only by the qualification makes the
    basis ``qualified_exact_pair`` whatever the model's own claim, so the
    certificate names the pair and its ledger evidence is enforced.
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

    basis, basis_warning, refusal = _release_model_basis(
        manifest, model_package, model_version
    )

    core_rests_on_qualification = core_version is not None and (
        _check_core_compatibility(manifest, core_version, qualified_pair_id, warnings)
    )
    if core_rests_on_qualification:
        # The publisher never claimed this core, so the model's own claim
        # cannot carry the certificate: it is the exact pair that was tested,
        # and the certificate must name it so its evidence is checked.
        warnings.append(
            f"certifying exactly {model_package}=={model_version} with "
            f"policyengine-core=={core_version} on automated qualification of "
            f"pair {qualified_pair_id}; the certificate stands only with a "
            "promotable qualification receipt for that pair in the ledger"
        )
        return BASIS_QUALIFIED_PAIR, warnings

    if basis is not None:
        if basis_warning is not None:
            warnings.append(basis_warning)
        return basis, warnings
    if qualified_pair_id is not None:
        if core_version is None:
            raise CertificationError(
                "A qualified exact pair names its core version; pass core_version."
            )
        warnings.append(
            f"certifying exactly {model_package}=={model_version} with "
            f"policyengine-core=={core_version} on automated qualification of "
            f"pair {qualified_pair_id}; the certificate stands only with a "
            "promotable qualification receipt for that pair in the ledger"
        )
        return BASIS_QUALIFIED_PAIR, warnings
    raise CertificationError(
        f"{refusal}; a new data build, a published compatibility claim or an "
        "automated qualification of the exact pair is required."
    )


def _release_model_basis(
    manifest: DataReleaseManifest,
    model_package: str,
    model_version: str,
) -> tuple[Optional[str], Optional[str], str]:
    """How a release serves ``model_version`` by its own build or claims.

    Returns ``(basis, warning, refusal)``. ``basis`` is the built-with or
    publisher-claim basis, or ``None`` when neither covers the version;
    ``warning`` goes with the publisher-claim basis; ``refusal`` says why
    neither applies, for the caller to complete with its remedy.
    """
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
    if built_with == model_version:
        return BASIS_BUILT_WITH, None, ""
    if any(
        _specifier_matches(model_version, specifier) for specifier in claim_specifiers
    ):
        return (
            BASIS_PUBLISHER_CLAIM,
            f"certifying {model_package} {model_version} on the publisher's "
            f"compatibility claim {claim_specifiers}; the data was built "
            f"with {built_with or 'an unrecorded model version'} — the test "
            "suite is the arbiter",
            "",
        )
    return (
        None,
        None,
        f"{model_package} {model_version} matches neither the build-time "
        f"model ({built_with or 'unrecorded'}) nor any publisher "
        f"compatibility claim {claim_specifiers or '(none declared)'}",
    )


def model_compatibility_basis(
    manifest: DataReleaseManifest,
    model_package: str,
    model_version: str,
) -> tuple[str, list[str]]:
    """Return the basis on which a release serves a model version by itself.

    The release must be built with ``model_version`` or claim compatibility
    with it; automated qualification of a pair does not apply. Certification
    uses this for a regional release, which no qualification names. Returns
    ``(compatibility_basis, warnings)``.
    """
    basis, warning, refusal = _release_model_basis(
        manifest, model_package, model_version
    )
    if basis is None:
        raise CertificationError(
            f"{refusal}; a new data build or a published compatibility claim "
            "is required."
        )
    return basis, [] if warning is None else [warning]


def _check_core_compatibility(
    manifest: DataReleaseManifest,
    core_version: str,
    qualified_pair_id: Optional[str],
    warnings: list[str],
) -> bool:
    """The core must be the build core, publisher-claimed, or qualified.

    Returns whether the core is admitted only by the qualification, in which
    case the certificate's basis must be the qualified exact pair.
    """

    build = manifest.build
    built_with_core = (
        build.built_with_core_package.version
        if build is not None and build.built_with_core_package is not None
        else None
    )
    core_claims = [
        package.specifier
        for package in manifest.compatible_core_packages
        if package.name == "policyengine-core"
    ]
    if built_with_core == core_version or any(
        _specifier_matches(core_version, specifier) for specifier in core_claims
    ):
        return False
    if qualified_pair_id is not None:
        warnings.append(
            f"policyengine-core {core_version} is outside the publisher's core "
            f"claims {core_claims or '(none declared)'}; covered by qualification "
            f"of pair {qualified_pair_id}"
        )
        return True
    raise CertificationError(
        f"policyengine-core {core_version} matches neither the build-time core "
        f"({built_with_core or 'unrecorded'}) nor any publisher core claim "
        f"{core_claims or '(none declared)'}."
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
        artifact.kind in RELEASE_SCOPED_ARTIFACT_KINDS
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
        and manifest.data_package.name in POPULACE_DATA_PACKAGES
        and uri_parts["repo_id"] == "policyengine/populace-us"
    ):
        return (POPULACE_US_SOURCE_COVERAGE_FILE,)
    return ()


def should_validate_vendored_artifacts(
    country: str,
    manifest: DataReleaseManifest,
    uri_parts: dict,
) -> bool:
    return manifest.data_package.name in POPULACE_DATA_PACKAGES and uri_parts[
        "repo_id"
    ] == POPULACE_RELEASE_REPOS.get(country)


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


def _certified_country(country: str) -> CertifiedCountry:
    """``country`` as a certified country id; any other value is refused."""
    if country not in get_args(CertifiedCountry):
        raise CertificationError(f"Unknown country {country!r}.")
    return cast(CertifiedCountry, country)


def _local_area_region_types(country: CertifiedCountry) -> tuple[str, ...]:
    try:
        return LOCAL_AREA_REGION_TYPES[country]
    except KeyError:
        raise CertificationError(
            f"Regional data releases are not supported for country {country!r}."
        ) from None


def _route_region_types(
    country: CertifiedCountry,
    primary_manifest: DataReleaseManifest,
    primary_payload: dict,
    path: str,
    release_label: str,
) -> None:
    """Point the country's local region types at ``path`` in the payload."""
    metadata = primary_payload.setdefault("metadata", {})
    region_datasets = metadata.setdefault("region_datasets", {})
    default_dataset = primary_manifest.default_datasets["national"]
    default_artifact = primary_manifest.artifacts[default_dataset]
    region_datasets.setdefault(
        "national",
        {"path_template": default_artifact.path},
    )
    regional_template = {"path_template": path}
    for region_type in _local_area_region_types(country):
        existing = region_datasets.get(region_type)
        if existing is not None and existing != regional_template:
            raise CertificationError(
                f"{release_label} conflicts with the {region_type!r} "
                "dataset template in the primary manifest."
            )
        region_datasets[region_type] = regional_template


def _add_regional_artifact(
    merged_artifacts: dict[str, dict],
    name: str,
    artifact: DataReleaseArtifact,
    regional_repo_type: Optional[Literal["model", "dataset"]],
) -> None:
    if name in merged_artifacts:
        raise CertificationError(
            f"Regional artifact {name!r} conflicts with the primary manifest."
        )
    if any(item.get("path") == artifact.path for item in merged_artifacts.values()):
        raise CertificationError(
            f"Regional artifact path {artifact.path!r} conflicts with the primary manifest."
        )
    artifact_payload = artifact.model_dump(mode="json", exclude_none=True)
    if regional_repo_type is not None:
        artifact_payload["repo_type"] = regional_repo_type
    merged_artifacts[name] = artifact_payload


def merge_local_area_release_manifest(
    country: CertifiedCountry,
    primary_manifest: DataReleaseManifest,
    regional_manifest: DataReleaseManifest,
    *,
    regional_repo_type: Optional[Literal["model", "dataset"]] = None,
) -> DataReleaseManifest:
    """Add one certified local-area dataset to a primary release.

    The supplemental release remains non-default nationally. The country's
    local region types (US states and congressional districts, UK
    constituencies and local authorities) load the shared artifact and apply
    their existing row-filtering strategy at runtime.
    """

    label = f"{country.upper()} local-area release"
    _local_area_region_types(country)
    if regional_manifest.dataset_role != "non_default_local_area":
        raise CertificationError(
            f"{label} must declare dataset_role='non_default_local_area'."
        )
    if regional_manifest.is_default is not False:
        raise CertificationError(f"{label} must declare is_default=false.")
    if regional_manifest.default_datasets:
        raise CertificationError(f"{label} must not declare default datasets.")

    local_area_artifacts = [
        (name, artifact)
        for name, artifact in regional_manifest.artifacts.items()
        if artifact.kind == "microdata"
    ]
    if len(local_area_artifacts) != 1:
        raise CertificationError(
            f"{label} must contain exactly one microdata artifact."
        )
    artifact_name, artifact = local_area_artifacts[0]
    if not artifact.path.endswith(".h5"):
        raise CertificationError(
            f"{country.upper()} local-area artifact must be an H5 file."
        )
    if not artifact.repo_id or not artifact.revision or not artifact.sha256:
        raise CertificationError(
            f"{country.upper()} local-area artifact must declare repo_id, "
            "revision, and sha256."
        )

    primary_payload = primary_manifest.model_dump(mode="json", exclude_none=True)
    merged_artifacts = primary_payload.setdefault("artifacts", {})
    _add_regional_artifact(
        merged_artifacts, artifact_name, artifact, regional_repo_type
    )
    _route_region_types(
        country, primary_manifest, primary_payload, artifact.path, label
    )

    return DataReleaseManifest.model_validate(primary_payload)


def merge_us_local_area_release_manifest(
    primary_manifest: DataReleaseManifest,
    regional_manifest: DataReleaseManifest,
    *,
    regional_repo_type: Optional[Literal["model", "dataset"]] = None,
) -> DataReleaseManifest:
    """Add one certified local-area dataset to a primary US release."""

    return merge_local_area_release_manifest(
        "us",
        primary_manifest,
        regional_manifest,
        regional_repo_type=regional_repo_type,
    )


def merge_area_coded_national_release_manifest(
    country: CertifiedCountry,
    primary_manifest: DataReleaseManifest,
    regional_manifest: DataReleaseManifest,
    *,
    regional_repo_type: Optional[Literal["model", "dataset"]] = None,
) -> DataReleaseManifest:
    """Route UK area regions to another release's national dataset.

    This serves a national-first switch: the primary release's national
    dataset carries no area codes, and the regional manifest is a certified
    national release (the enhanced FRS) whose households do. Its national
    dataset and its area weight matrices join the certified datasets with
    their own repo and revision pins, and constituency and local-authority
    regions load that dataset. The regional release's own default stays
    non-default here.
    """

    label = f"{country.upper()} area-coded national release"
    if country != "uk":
        raise CertificationError(
            "Area-coded national regional releases are only supported for the UK."
        )
    if regional_manifest.dataset_role not in (None, "national_default"):
        raise CertificationError(
            f"{label} must be a national release, not "
            f"dataset_role={regional_manifest.dataset_role!r}. Certify a "
            "local-area release with --regional-release-kind local_area."
        )
    area_dataset = regional_manifest.default_datasets.get("national")
    if area_dataset is None or area_dataset not in regional_manifest.artifacts:
        raise CertificationError(
            f"{label} must declare a national default dataset among its artifacts."
        )
    area_artifact = regional_manifest.artifacts[area_dataset]
    if area_artifact.kind != "microdata" or not area_artifact.path.endswith(".h5"):
        raise CertificationError(
            f"{label} national dataset {area_dataset!r} must be an H5 microdata "
            "artifact."
        )

    carried = {area_dataset: area_artifact}
    weights = {
        name: artifact
        for name, artifact in regional_manifest.artifacts.items()
        if artifact.kind == "weights"
    }
    weight_paths = {artifact.path for artifact in weights.values()}
    missing = [path for path in UK_AREA_WEIGHT_MATRIX_PATHS if path not in weight_paths]
    if missing:
        raise CertificationError(
            f"{label} must carry the area weight matrices {missing}."
        )
    carried.update(weights)
    for name, artifact in carried.items():
        if not artifact.repo_id or not artifact.revision or not artifact.sha256:
            raise CertificationError(
                f"{label} artifact {name!r} must declare repo_id, revision, and sha256."
            )

    primary_payload = primary_manifest.model_dump(mode="json", exclude_none=True)
    merged_artifacts = primary_payload.setdefault("artifacts", {})
    for name, artifact in carried.items():
        _add_regional_artifact(merged_artifacts, name, artifact, regional_repo_type)
    _route_region_types(
        country, primary_manifest, primary_payload, area_artifact.path, label
    )

    return DataReleaseManifest.model_validate(primary_payload)


def merge_regional_release_manifest(
    country: CertifiedCountry,
    primary_manifest: DataReleaseManifest,
    regional_manifest: DataReleaseManifest,
    *,
    release_kind: RegionalReleaseKind = "local_area",
    regional_repo_type: Optional[Literal["model", "dataset"]] = None,
    artifact_prefix: str = "states/",
    path_template: str = "states/{state_code}.h5",
) -> tuple[DataReleaseManifest, Optional[RegionalReleaseKind]]:
    """Merge a regional release into a primary release.

    Returns the merged manifest and the routing kind to record. The kind is
    ``None`` only for a legacy US per-state release.
    """

    if release_kind not in REGIONAL_RELEASE_KINDS:
        raise CertificationError(
            f"Unknown regional release kind {release_kind!r}; expected one of "
            f"{list(REGIONAL_RELEASE_KINDS)}."
        )
    if release_kind == "area_coded_national":
        return (
            merge_area_coded_national_release_manifest(
                country,
                primary_manifest,
                regional_manifest,
                regional_repo_type=regional_repo_type,
            ),
            release_kind,
        )
    if regional_manifest.dataset_role == "non_default_local_area":
        return (
            merge_local_area_release_manifest(
                country,
                primary_manifest,
                regional_manifest,
                regional_repo_type=regional_repo_type,
            ),
            "local_area",
        )
    if country == "us" and regional_manifest.dataset_role is None:
        return (
            merge_us_state_release_manifest(
                primary_manifest,
                regional_manifest,
                artifact_prefix=artifact_prefix,
                path_template=path_template,
            ),
            None,
        )
    if country == "uk" and regional_manifest.dataset_role in (None, "national_default"):
        raise CertificationError(
            "UK regional release is a national release, not a local-area one. "
            "To route constituency and local-authority regions to its national "
            "dataset, pass --regional-release-kind area_coded_national."
        )
    raise CertificationError(
        f"Unsupported {country.upper()} regional release dataset_role "
        f"{regional_manifest.dataset_role!r}."
    )


def merge_us_regional_release_manifest(
    primary_manifest: DataReleaseManifest,
    regional_manifest: DataReleaseManifest,
    *,
    regional_repo_type: Optional[Literal["model", "dataset"]] = None,
    artifact_prefix: str = "states/",
    path_template: str = "states/{state_code}.h5",
) -> DataReleaseManifest:
    """Merge a typed shared local-area release or a legacy per-state release."""

    manifest, _ = merge_regional_release_manifest(
        "us",
        primary_manifest,
        regional_manifest,
        regional_repo_type=regional_repo_type,
        artifact_prefix=artifact_prefix,
        path_template=path_template,
    )
    return manifest


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
    core_version: Optional[str] = None,
    qualified_pair_id: Optional[str] = None,
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
        if (
            country == "us"
            and manifest.data_package.name in POPULACE_DATA_PACKAGES
            and artifact.path.endswith(".h5")
            and (
                artifact.path.startswith("states/")
                or artifact.path.startswith("districts/")
            )
        ):
            continue
        payload: dict = {
            "path": artifact_path_for_country_manifest(artifact, uri_parts),
            "revision": artifact.revision,
        }
        if artifact.sha256:
            payload["sha256"] = artifact.sha256
        if artifact.repo_id:
            payload["repo_id"] = artifact.repo_id
        if artifact.repo_type:
            payload["repo_type"] = artifact.repo_type
        datasets[name] = payload

    region_datasets = {}
    raw_regions = manifest.metadata.get("region_datasets")
    if isinstance(raw_regions, dict):
        for region, template in sorted(raw_regions.items()):
            if not isinstance(template, dict) or "path_template" not in template:
                continue
            path_template = template.get("path_template")
            if (
                country == "us"
                and manifest.data_package.name in POPULACE_DATA_PACKAGES
                and region in {"state", "congressional_district"}
                and isinstance(path_template, str)
                and "{" in path_template
            ):
                continue
            region_datasets[region] = {"path_template": template["path_template"]}
    region_datasets.setdefault(
        "national",
        {"path_template": default_artifact.path},
    )

    certification: dict = {
        "compatibility_basis": compatibility_basis,
        "certified_for_model_version": model_version,
        "certified_by": CERTIFIED_BY,
    }
    if core_version is not None:
        certification["certified_for_core_version"] = core_version
    if qualified_pair_id is not None:
        certification["qualification_pair_id"] = qualified_pair_id
        certification["qualification_ledger_url"] = (
            f"{QUALIFICATION_LEDGER_URL}/{country}/{qualified_pair_id}"
        )
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
        build_id = release_build_id(build)
        if build_id:
            certification["data_build_id"] = build_id
            certified_artifact["build_id"] = build_id
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
    regional_release_kind: Optional[RegionalReleaseKind] = None,
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
    if regional_release_kind is not None:
        payload["regional_release_kind"] = regional_release_kind
    payload["default_dataset_uri"] = certified_artifact.get("uri")
    return payload


class DataProducerCertificationStrategy:
    data_producer: str

    def certify(
        self,
        *,
        country: CertifiedCountry,
        manifest_uri: str,
        model_package: str,
        model_version: str,
        token: Optional[str],
        check_artifacts: bool,
        regional_manifest_uri: Optional[str] = None,
        regional_artifact_prefix: str = "states/",
        regional_path_template: str = "states/{state_code}.h5",
        regional_release_kind: RegionalReleaseKind = "local_area",
        core_version: Optional[str] = None,
        qualified_pair_id: Optional[str] = None,
    ) -> tuple[dict, str, list[str]]:
        raise NotImplementedError


class LegacyDataProducerCertificationStrategy(DataProducerCertificationStrategy):
    data_producer = "legacy"

    def certify(
        self,
        *,
        country: CertifiedCountry,
        manifest_uri: str,
        model_package: str,
        model_version: str,
        token: Optional[str],
        check_artifacts: bool,
        regional_manifest_uri: Optional[str] = None,
        regional_artifact_prefix: str = "states/",
        regional_path_template: str = "states/{state_code}.h5",
        regional_release_kind: RegionalReleaseKind = "local_area",
        core_version: Optional[str] = None,
        qualified_pair_id: Optional[str] = None,
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
        country: CertifiedCountry,
        manifest_uri: str,
        model_package: str,
        model_version: str,
        token: Optional[str],
        check_artifacts: bool,
        regional_manifest_uri: Optional[str] = None,
        regional_artifact_prefix: str = "states/",
        regional_path_template: str = "states/{state_code}.h5",
        regional_release_kind: RegionalReleaseKind = "local_area",
        core_version: Optional[str] = None,
        qualified_pair_id: Optional[str] = None,
    ) -> tuple[dict, str, list[str]]:
        manifest, manifest_sha256, uri_parts = fetch_release_manifest(
            manifest_uri, token=token
        )
        regional_uri_parts = None
        recorded_release_kind = None
        regional_artifacts: dict[str, DataReleaseArtifact] = {}
        regional_warnings: list[str] = []
        if regional_manifest_uri is not None:
            regional_manifest, _, regional_uri_parts = fetch_release_manifest(
                regional_manifest_uri, token=token
            )
            # The regional release runs on the same model and core, so it must
            # cover the pinned versions by its own build or claims. A qualified
            # pair names the primary release only, so it does not extend here.
            try:
                _, regional_warnings = model_compatibility_basis(
                    regional_manifest, model_package, model_version
                )
                if core_version is not None:
                    _check_core_compatibility(
                        regional_manifest, core_version, None, regional_warnings
                    )
            except CertificationError as exc:
                raise CertificationError(
                    f"Regional release {regional_manifest_uri}: {exc}"
                ) from exc
            regional_warnings = [
                f"regional release: {warning}" for warning in regional_warnings
            ]
            primary_artifact_names = set(manifest.artifacts)
            manifest, recorded_release_kind = merge_regional_release_manifest(
                country,
                manifest,
                regional_manifest,
                release_kind=regional_release_kind,
                regional_repo_type=regional_uri_parts["repo_type"],
                artifact_prefix=regional_artifact_prefix,
                path_template=regional_path_template,
            )
            regional_artifacts = {
                name: artifact
                for name, artifact in manifest.artifacts.items()
                if name not in primary_artifact_names
            }
        compatibility_basis, warnings = validate_release_manifest(
            manifest,
            model_package,
            model_version,
            core_version=core_version,
            qualified_pair_id=qualified_pair_id,
        )
        warnings = warnings + regional_warnings

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
        if check_artifacts and recorded_release_kind is not None:
            for name, artifact in regional_artifacts.items():
                if not head_artifact(artifact, token=token):
                    raise CertificationError(
                        f"Regional artifact {name!r} is not reachable: {artifact.uri}"
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
            core_version=core_version,
            qualified_pair_id=(
                qualified_pair_id
                if compatibility_basis == BASIS_QUALIFIED_PAIR
                else None
            ),
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
                regional_release_kind=recorded_release_kind,
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
    regional_release_kind: RegionalReleaseKind = "local_area",
    drop_regional_release: bool = False,
    core_version: Optional[str] = None,
    qualified_pair_id: Optional[str] = None,
) -> CertificationResult:
    """Certify a data release into the bundle manifest.

    ``core_version`` adds the core compatibility check and pins the core in
    the bundle's ``packages``. ``qualified_pair_id`` admits the exact model,
    core and data release when neither the build-time model nor a publisher
    claim covers them; the certificate then names the pair, whose promotable
    qualification receipt must be in the ledger.

    ``regional_manifest_uri`` routes the country's local region types to a
    regional release, read as ``regional_release_kind``. That release must
    serve the pinned model, and the pinned core when ``core_version`` is
    given, by its own build or claims: a qualified pair names the primary
    release only. While the bundle routes regions, a run without
    ``regional_manifest_uri`` is refused unless ``drop_regional_release``.
    """
    certified_country = _certified_country(country)
    if drop_regional_release and regional_manifest_uri is not None:
        raise CertificationError(
            "--drop-regional-release removes the bundle's regional routing, so it "
            "cannot be combined with --regional-manifest-uri."
        )
    model_package = COUNTRY_MODEL_PACKAGES[certified_country]
    model_version = model_version or installed_model_version(model_package)
    strategy = certification_strategy(country, data_producer)
    bundle_path = bundle_path or default_bundle_source_path()
    bundle = json.loads(bundle_path.read_text())

    # Certification rewrites data_releases.<country> wholesale, so a run
    # without the regional manifest would silently drop the regional routing.
    current_regional_uri = ((bundle.get("data_releases") or {}).get(country) or {}).get(
        "regional_source_manifest_uri"
    )
    if (
        current_regional_uri is not None
        and regional_manifest_uri is None
        and not drop_regional_release
    ):
        raise CertificationError(
            f"The bundle's {country.upper()} data release routes regions to "
            f"{current_regional_uri}. Pass --regional-manifest-uri (that release "
            "or its replacement) to keep regional routing, or "
            "--drop-regional-release to remove it."
        )

    data_release, manifest_sha256, warnings = strategy.certify(
        country=certified_country,
        manifest_uri=manifest_uri,
        model_package=model_package,
        model_version=model_version,
        token=token,
        check_artifacts=check_artifacts,
        regional_manifest_uri=regional_manifest_uri,
        regional_artifact_prefix=regional_artifact_prefix,
        regional_path_template=regional_path_template,
        regional_release_kind=regional_release_kind,
        core_version=core_version,
        qualified_pair_id=qualified_pair_id,
    )
    bundle.setdefault("data_releases", {})[country] = data_release
    bundle.setdefault("countries", {}).setdefault(country, {})["model_package"] = (
        model_package
    )
    if model_package in bundle.get("packages", {}):
        bundle["packages"][model_package]["version"] = model_version
    if core_version is not None and "policyengine-core" in bundle.get("packages", {}):
        bundle["packages"]["policyengine-core"]["version"] = core_version
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
