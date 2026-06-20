"""Refresh a country release manifest in place.

The release manifest at ``data/release_manifests/{country}.json`` pins
three artifacts by content hash:

- the country model wheel (sha256 + PyPI download URL),
- the certified microdata artifact (sha256 + HF resolve URL),
- the data package metadata used to compute the build fingerprint.

When a country bumps its PyPI wheel or HF dataset, every one of those
pins has to move together, and the TRACE TRO sidecar at
``data/release_manifests/{country}.trace.tro.jsonld`` must be
regenerated so replication reviewers see the right hashes.

This module exposes the refresh as a library function:

.. code-block:: python

    from policyengine.provenance.bundle import refresh_release_bundle

    result = refresh_release_bundle(
        country="us",
        model_version="1.653.3",
        data_version="1.83.4",
    )
    print(result.summary())

``scripts/refresh_release_bundle.py`` is a thin argparse wrapper for
operational use. Network access is required (PyPI JSON API + HF HEAD
against the dataset URI). Private country data (UK) additionally
needs ``HUGGING_FACE_TOKEN``.
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    get_release_manifest,
    https_dataset_uri,
)

# ---------------------------------------------------------------------------
# Paths inside the installed / source-tree wheel.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MANIFEST_DIR = REPO_ROOT / "src" / "policyengine" / "data" / "release_manifests"
PYPROJECT = REPO_ROOT / "pyproject.toml"
SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class _CriticalCalibrationTarget:
    name: str
    max_abs_relative_error: float


_US_POPULACE_CRITICAL_CALIBRATION_TARGETS = (
    _CriticalCalibrationTarget(
        name="irs_soi.ty2022.historic_table_2.us.all.income_tax_liability_amount@2024",
        max_abs_relative_error=0.05,
    ),
    _CriticalCalibrationTarget(
        name="irs_soi.ty2022.historic_table_2.us.all.income_tax_liability_returns@2024",
        max_abs_relative_error=0.10,
    ),
    _CriticalCalibrationTarget(
        name="ssa_supplement.cy2024.oasdi_ssi_payments.social_security_benefits.payment_amount@2024",
        max_abs_relative_error=0.05,
    ),
)


# ---------------------------------------------------------------------------
# policyengine.py bundle identity
# ---------------------------------------------------------------------------


def _pyproject_version(pyproject_path: Path) -> str:
    text = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"', text, re.MULTILINE)
    if match is None:
        raise ValueError(f"Could not find project version in {pyproject_path}")
    return match.group(1)


def sync_release_manifest_policyengine_version(
    *,
    policyengine_version: Optional[str] = None,
    manifest_dir: Path = MANIFEST_DIR,
    pyproject_path: Path = PYPROJECT,
) -> list[Path]:
    """Sync bundled release manifests to the current ``policyengine.py`` version.

    Country model/data refreshes and package release bumps move through
    different automation paths. This helper keeps the top-level bundle identity
    tied to the package release regardless of which path writes the manifest.
    """
    resolved_version = policyengine_version or _pyproject_version(pyproject_path)
    if not SEMVER_PATTERN.match(resolved_version):
        raise ValueError(f"Invalid policyengine version: {resolved_version}")

    updated_paths: list[Path] = []
    for manifest_path in sorted(manifest_dir.glob("*.json")):
        manifest_json = json.loads(manifest_path.read_text())
        country_id = manifest_json.get("country_id") or manifest_path.stem
        expected_bundle_id = f"{country_id}-{resolved_version}"
        if (
            manifest_json.get("policyengine_version") == resolved_version
            and manifest_json.get("bundle_id") == expected_bundle_id
        ):
            continue

        manifest_json["policyengine_version"] = resolved_version
        manifest_json["bundle_id"] = expected_bundle_id
        manifest_path.write_text(
            json.dumps(manifest_json, indent=2, sort_keys=False) + "\n"
        )
        updated_paths.append(manifest_path)

    return updated_paths


# ---------------------------------------------------------------------------
# PyPI metadata resolution
# ---------------------------------------------------------------------------


def _pypi_wheel_metadata(package: str, version: str) -> dict:
    """Return ``{"url": ..., "sha256": ...}`` for the py3-none-any wheel
    of ``package==version`` on PyPI.

    Raises if PyPI reports no matching wheel, or if multiple matching
    wheels exist with different sha256s (i.e. the release is
    unambiguous).
    """
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    with urlopen(Request(url, headers={"User-Agent": "policyengine.py"})) as f:
        payload = json.load(f)
    wheels = [
        f
        for f in payload.get("urls", [])
        if f.get("packagetype") == "bdist_wheel"
        and "py3-none-any" in f.get("filename", "")
    ]
    if not wheels:
        raise ValueError(
            f"No py3-none-any wheel found on PyPI for {package}=={version}"
        )
    sha256s = {f["digests"]["sha256"] for f in wheels}
    if len(sha256s) > 1:
        raise ValueError(
            f"Multiple distinct py3-none-any wheels for {package}=={version}: {sha256s}"
        )
    wheel = wheels[0]
    return {"url": wheel["url"], "sha256": wheel["digests"]["sha256"]}


# ---------------------------------------------------------------------------
# Hugging Face dataset resolution
# ---------------------------------------------------------------------------


def _hf_dataset_sha256(repo_id: str, path: str, revision: str) -> str:
    """Fetch the dataset file's sha256 by streaming the resolve URL.

    Uses the ``HUGGING_FACE_TOKEN`` env var for private repos. Streams
    the file in 8 MiB chunks so memory usage stays flat.
    """
    url = https_dataset_uri(
        repo_id=repo_id,
        path_in_repo=path,
        revision=revision,
    )
    headers = {"User-Agent": "policyengine.py"}
    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    hasher = hashlib.sha256()
    with urlopen(Request(url, headers=headers)) as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


@dataclass(frozen=True)
class _DataReleaseManifestFetch:
    payload: dict
    repo_commit: Optional[str]


def _fetch_data_release_manifest(
    repo_id: str,
    release_manifest_path: str,
    revision: str,
    *,
    repo_type: str = "model",
    allow_main_fallback: bool = True,
) -> Optional[_DataReleaseManifestFetch]:
    """Fetch a data release manifest from HF if one is available.

    Older data releases may not have a machine-readable release manifest at the
    inferred path. In that case the bundle refresh falls back to hashing the
    dataset artifact directly.

    Data releases are stored under versioned paths, but the HF repository does
    not necessarily create a matching git tag for each data version. For
    inferred data-version revisions, try the version revision first for
    repositories that do publish tags, then fall back to ``main`` and persist
    the immutable ``x-repo-commit`` header. Explicit revisions do not get that
    fallback because a typo or stale CRFB run ref should fail closed.
    """
    headers = {"User-Agent": "policyengine.py"}
    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    revisions = [revision]
    if allow_main_fallback and revision != "main":
        revisions.append("main")

    for candidate in revisions:
        prefix = "datasets/" if repo_type == "dataset" else ""
        url = (
            f"https://huggingface.co/{prefix}{repo_id}/resolve/"
            f"{candidate}/{release_manifest_path}"
        )
        try:
            with urlopen(Request(url, headers=headers)) as f:
                payload = json.load(f)
                repo_commit = getattr(f, "headers", {}).get("x-repo-commit")
                return _DataReleaseManifestFetch(
                    payload=payload,
                    repo_commit=repo_commit,
                )
        except (OSError, ValueError):
            continue
    return None


def _fetch_json_release_artifact(
    artifact: dict,
    *,
    release_manifest_path: str | None,
    data_repo_id: str,
    data_repo_type: str,
    default_revision: str,
) -> dict:
    path = _release_scoped_artifact_path(
        artifact,
        release_manifest_path=release_manifest_path,
        data_repo_id=data_repo_id,
    )
    repo_id = artifact.get("repo_id") or data_repo_id
    revision = artifact.get("revision") or default_revision
    repo_type = artifact.get("repo_type")
    if repo_type is None:
        repo_type = data_repo_type if repo_id == data_repo_id else "model"
    url = https_dataset_uri(
        repo_id=repo_id,
        path_in_repo=path,
        revision=revision,
        repo_type=repo_type,
    )
    headers = {"User-Agent": "policyengine.py"}
    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with urlopen(Request(url, headers=headers)) as f:
        content = f.read()

    expected_sha256 = artifact.get("sha256")
    if expected_sha256:
        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(
                "Data release artifact hash mismatch for "
                f"{path!r}: expected {expected_sha256}, got {actual_sha256}."
            )

    try:
        return json.loads(content)
    except ValueError as exc:
        raise ValueError(f"Data release artifact {path!r} is not valid JSON.") from exc


def _calibration_relative_error(target: dict) -> float | None:
    relative_error = target.get("relative_error")
    if relative_error is not None:
        return float(relative_error)

    target_value = target.get("target")
    final_estimate = target.get("final_estimate", target.get("final"))
    if target_value in (None, 0) or final_estimate is None:
        return None
    return (float(final_estimate) - float(target_value)) / float(target_value)


def _validate_populace_critical_calibration_targets(
    *,
    country: str,
    release_manifest_json: dict,
    release_manifest_path: str | None,
    data_package_name: str,
    data_repo_id: str,
    data_repo_type: str,
    default_revision: str,
) -> None:
    if country != "us" or data_package_name != "populace-data":
        return

    diagnostics_artifact = release_manifest_json.get("artifacts", {}).get(
        "calibration_diagnostics"
    )
    if diagnostics_artifact is None:
        raise ValueError(
            "Populace release manifest is missing calibration_diagnostics; "
            "refusing to certify without critical calibration target gates."
        )

    diagnostics = _fetch_json_release_artifact(
        diagnostics_artifact,
        release_manifest_path=release_manifest_path,
        data_repo_id=data_repo_id,
        data_repo_type=data_repo_type,
        default_revision=default_revision,
    )
    targets = diagnostics.get("targets")
    if not isinstance(targets, list):
        raise ValueError(
            "Populace calibration_diagnostics is missing the target list; "
            "refusing to certify without critical calibration target gates."
        )
    targets_by_name = {
        target.get("name"): target
        for target in targets
        if isinstance(target, dict) and target.get("name")
    }

    failures = []
    for critical_target in _US_POPULACE_CRITICAL_CALIBRATION_TARGETS:
        target = targets_by_name.get(critical_target.name)
        if target is None:
            failures.append(f"{critical_target.name}: missing")
            continue

        relative_error = _calibration_relative_error(target)
        if relative_error is None:
            failures.append(f"{critical_target.name}: missing relative error")
            continue

        if abs(relative_error) > critical_target.max_abs_relative_error:
            failures.append(
                f"{critical_target.name}: relative_error={relative_error:.6g} "
                f"exceeds {critical_target.max_abs_relative_error:.6g}"
            )

    if failures:
        raise ValueError(
            "Populace critical calibration target gate failed: " + "; ".join(failures)
        )


def _updated_release_manifest_path(
    current_path: str,
    old_data: str,
    new_data: str,
) -> str:
    """Preserve country-specific release-manifest layout while bumping versions."""
    if old_data in current_path:
        return current_path.replace(old_data, new_data)
    return current_path


def _release_artifact_by_path(
    release_manifest_json: dict,
    path: str,
) -> Optional[dict]:
    artifacts = release_manifest_json.get("artifacts", {})
    for artifact in artifacts.values():
        if artifact.get("path") == path:
            return artifact
    return None


def _metadata_sidecar_path(path: str) -> str:
    return f"{path}.metadata.json"


def _release_scoped_artifact_path(
    artifact: dict,
    *,
    release_manifest_path: str | None,
    data_repo_id: str,
) -> str:
    """Return the dereferenceable country-manifest path for a release artifact.

    Populace release manifests describe diagnostics relative to the release
    directory, while the HF files are published under ``releases/{id}/``.
    Runtime manifests must store the dereferenceable path.
    """
    path = artifact.get("path", "")
    if not path:
        return path
    if not release_manifest_path:
        return path
    release_dir = posixpath.dirname(release_manifest_path)
    if (
        release_dir
        and release_dir != "."
        and artifact.get("kind") == "diagnostics"
        and artifact.get("repo_id") == data_repo_id
        and not path.startswith(f"{release_dir}/")
    ):
        return f"{release_dir}/{path}"
    return path


def _specifier_matches(*, version: str, specifier: str) -> bool:
    try:
        return Version(version) in SpecifierSet(specifier)
    except (InvalidSpecifier, InvalidVersion):
        return False


def _release_manifest_has_compatible_model_package(
    release_manifest_json: dict,
    *,
    package_name: str,
    model_version: str,
) -> bool:
    for compatible_model_package in release_manifest_json.get(
        "compatible_model_packages",
        [],
    ):
        if compatible_model_package.get("name") != package_name:
            continue
        if _specifier_matches(
            version=model_version,
            specifier=compatible_model_package.get("specifier", ""),
        ):
            return True
    return False


def _release_manifest_compatibility_basis(
    *,
    release_manifest_json: dict,
    current_manifest: CountryReleaseManifest,
    package_name: str,
    model_version: str,
    built_with_model_version: str | None,
    data_build_fingerprint: str | None,
) -> str:
    if built_with_model_version == model_version:
        return "exact_build_model_version"

    current_certification = current_manifest.certification
    if (
        current_certification is not None
        and current_certification.certified_for_model_version == model_version
        and current_certification.data_build_fingerprint is not None
        and current_certification.data_build_fingerprint == data_build_fingerprint
    ):
        return "matching_data_build_fingerprint"

    if _release_manifest_has_compatible_model_package(
        release_manifest_json,
        package_name=package_name,
        model_version=model_version,
    ):
        return "legacy_compatible_model_package"

    raise ValueError(
        "Data release manifest is not certified for "
        f"{package_name}=={model_version}. Publish a data release manifest with "
        "a matching build model, matching data-build fingerprint, or compatible "
        "model-package specifier before refreshing the bundle."
    )


def _refresh_dataset_path_references_from_data_release(
    manifest_json: dict,
    release_manifest_json: dict,
    *,
    release_manifest_path: str | None = None,
    data_repo_id: str,
) -> None:
    """Refresh bundled dataset hash pins from a data release manifest.

    The certified default dataset is handled separately because it also carries
    a URI and build ID. This helper covers every logical dataset entry under
    ``datasets``; notably the US long-term bundle stores one entry per year with
    both H5 and metadata-sidecar hashes.
    """
    datasets = manifest_json.setdefault("datasets", {})
    release_artifacts = release_manifest_json.get("artifacts", {})

    def update_reference_from_artifact(path_reference: dict, artifact: dict) -> None:
        raw_path = artifact.get("path")
        if raw_path:
            path_reference["path"] = _release_scoped_artifact_path(
                artifact,
                release_manifest_path=release_manifest_path,
                data_repo_id=data_repo_id,
            )
        if artifact.get("revision"):
            path_reference["revision"] = artifact["revision"]
        if artifact.get("repo_id"):
            path_reference["repo_id"] = artifact["repo_id"]
        if artifact.get("repo_type"):
            path_reference["repo_type"] = artifact["repo_type"]

        dataset_sha256 = artifact.get("sha256")
        if dataset_sha256:
            path_reference["sha256"] = dataset_sha256
        elif "sha256" in path_reference:
            raise ValueError(
                "Data release manifest dataset artifact lacks sha256 "
                f"for existing pinned path {raw_path!r}; refusing to leave "
                "stale dataset hash pin in place."
            )

        if not raw_path:
            return
        metadata_artifact = _release_artifact_by_path(
            release_manifest_json,
            _metadata_sidecar_path(raw_path),
        )
        had_metadata_pin = "metadata_sha256" in path_reference
        if metadata_artifact is None:
            if had_metadata_pin:
                raise ValueError(
                    "Data release manifest is missing metadata sidecar artifact "
                    f"for {raw_path!r}; refusing to drop existing metadata hash pin."
                )
            path_reference.pop("metadata_sha256", None)
            return
        metadata_sha256 = metadata_artifact.get("sha256")
        if not metadata_sha256:
            if had_metadata_pin:
                raise ValueError(
                    "Data release manifest metadata sidecar artifact lacks sha256 "
                    f"for {raw_path!r}; refusing to drop existing metadata hash pin."
                )
            path_reference.pop("metadata_sha256", None)
            return
        path_reference["metadata_sha256"] = metadata_sha256

    for name, path_reference in datasets.items():
        named_artifact = release_artifacts.get(name)
        if named_artifact is not None:
            update_reference_from_artifact(path_reference, named_artifact)
            continue

        path = path_reference.get("path")
        if not path:
            continue
        if path_reference.get("revision"):
            continue
        artifact = _release_artifact_by_path(release_manifest_json, path)
        if artifact is None:
            if "sha256" in path_reference or "metadata_sha256" in path_reference:
                raise ValueError(
                    "Data release manifest is missing dataset artifact "
                    f"for existing pinned path {path!r}; refusing to leave "
                    "stale dataset hash pins in place."
                )
            continue
        update_reference_from_artifact(path_reference, artifact)

    for name, artifact in release_artifacts.items():
        if name in datasets:
            continue
        path_reference: dict = {}
        update_reference_from_artifact(path_reference, artifact)
        datasets[name] = path_reference


# ---------------------------------------------------------------------------
# Refresh result
# ---------------------------------------------------------------------------


@dataclass
class RefreshResult:
    """What the refresh changed, for logs and PR bodies."""

    country: str
    old_model: str
    new_model: str
    old_data: str
    new_data: str
    old_wheel_sha256: str
    new_wheel_sha256: str
    old_dataset_sha256: str
    new_dataset_sha256: str
    manifest_path: Path
    pyproject_updated: bool

    def summary(self) -> str:
        lines = [
            f"Refreshed {self.country} release bundle:",
            f"  model:   {self.old_model} -> {self.new_model}",
            f"  data:    {self.old_data} -> {self.new_data}",
            f"  wheel sha256:   {self.old_wheel_sha256[:12]}... -> "
            f"{self.new_wheel_sha256[:12]}...",
            f"  dataset sha256: {self.old_dataset_sha256[:12]}... -> "
            f"{self.new_dataset_sha256[:12]}...",
            f"  manifest:       {self.manifest_path}",
        ]
        if self.pyproject_updated:
            lines.append("  pyproject.toml: pin updated")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core refresh function
# ---------------------------------------------------------------------------


def refresh_release_bundle(
    country: str,
    *,
    model_version: Optional[str] = None,
    data_version: Optional[str] = None,
    release_manifest_path: Optional[str] = None,
    release_manifest_revision: Optional[str] = None,
    update_pyproject: bool = True,
    manifest_dir: Path = MANIFEST_DIR,
    pyproject_path: Path = PYPROJECT,
) -> RefreshResult:
    """Refresh a country's release manifest in place.

    Args:
        country: ``"us"`` or ``"uk"``.
        model_version: New country-package version, e.g. ``"1.653.3"``.
            If ``None``, keeps the existing pin.
        data_version: New data-package version, e.g. ``"1.83.4"``. If
            ``None``, keeps the existing pin.
        release_manifest_path: Optional explicit data release manifest path.
            Needed for custom bundles whose path does not include the data
            package version, such as CRFB long-run candidate releases.
        release_manifest_revision: Optional HF revision to fetch the data
            release manifest from before pinning the immutable repo commit.
        update_pyproject: When True, also bumps the country extra in
            ``pyproject.toml`` to ``model_version``.
        manifest_dir: Overridable for tests.
        pyproject_path: Overridable for tests.

    Returns a :class:`RefreshResult` with the before/after of every
    content-addressed pin.
    """
    manifest_path = manifest_dir / f"{country}.json"
    manifest_json = json.loads(manifest_path.read_text())
    current = CountryReleaseManifest.model_validate(manifest_json)

    old_model = current.model_package.version
    old_data = current.data_package.version
    old_wheel_sha256 = current.model_package.sha256 or ""
    old_dataset_sha256 = current.certified_data_artifact.sha256 or ""

    new_model = model_version or old_model
    new_data = data_version or old_data

    package_name = current.model_package.name  # "policyengine-us" / "policyengine-uk"

    # Only hit PyPI if the model actually changed. Keeps no-op
    # refreshes and data-only refreshes offline for the wheel pin.
    if new_model != old_model:
        wheel = _pypi_wheel_metadata(package_name, new_model)
        new_wheel_sha256 = wheel["sha256"]
        new_wheel_url = wheel["url"]
    else:
        new_wheel_sha256 = old_wheel_sha256
        new_wheel_url = current.model_package.wheel_url or ""

    # Dataset HF resolve URL inferred from the existing URI: we only
    # change the ``@{revision}`` tail.
    current_uri = current.certified_data_artifact.uri
    repo_id_match = re.match(r"hf://([^/]+/[^/]+)/(.+?)@(.+)", current_uri)
    if not repo_id_match:
        raise ValueError(
            f"Cannot parse current dataset URI {current_uri!r}; expected "
            f"'hf://{{owner}}/{{repo}}/{{path}}@{{revision}}'"
        )
    repo_id, dataset_path, _old_revision = repo_id_match.groups()

    data_package_json = manifest_json["data_package"]
    release_manifest_json = None
    new_release_manifest_revision = None
    current_release_manifest_revision = data_package_json.get(
        "release_manifest_revision"
    )
    release_manifest_override = (
        release_manifest_path is not None or release_manifest_revision is not None
    )
    new_release_manifest_path = release_manifest_path or data_package_json.get(
        "release_manifest_path"
    )
    should_fetch_release_manifest = new_release_manifest_path is not None and (
        new_data != old_data or new_model != old_model or release_manifest_override
    )
    if should_fetch_release_manifest:
        if release_manifest_path is None:
            new_release_manifest_path = _updated_release_manifest_path(
                current_path=new_release_manifest_path,
                old_data=old_data,
                new_data=new_data,
            )
        fetch_revision = release_manifest_revision or (
            current_release_manifest_revision
            if release_manifest_path is None and new_data == old_data
            else new_data
        )
        release_manifest_fetch = _fetch_data_release_manifest(
            repo_id=repo_id,
            release_manifest_path=new_release_manifest_path,
            revision=fetch_revision,
            repo_type=data_package_json.get("repo_type", "model"),
            allow_main_fallback=release_manifest_revision is None,
        )
        if release_manifest_fetch is None:
            raise ValueError(
                "Could not fetch data release manifest "
                f"{new_release_manifest_path!r} from {repo_id}@{new_data}. "
                "Refusing to refresh a release-manifest-backed bundle with "
                "partial certification metadata."
            )
        if release_manifest_fetch.repo_commit is None:
            raise ValueError(
                "Could not resolve an immutable HF commit for data release "
                f"manifest {new_release_manifest_path!r} from {repo_id}@{new_data}."
            )
        release_manifest_json = release_manifest_fetch.payload
        release_manifest_data_version = release_manifest_json.get(
            "data_package", {}
        ).get("version")
        if release_manifest_data_version != new_data:
            raise ValueError(
                "Data release manifest "
                f"{new_release_manifest_path!r} from {repo_id} declares "
                f"version {release_manifest_data_version!r}, expected {new_data!r}."
            )
        new_release_manifest_revision = release_manifest_fetch.repo_commit
        _validate_populace_critical_calibration_targets(
            country=country,
            release_manifest_json=release_manifest_json,
            release_manifest_path=new_release_manifest_path,
            data_package_name=data_package_json.get("name", ""),
            data_repo_id=repo_id,
            data_repo_type=data_package_json.get("repo_type", "model"),
            default_revision=new_release_manifest_revision,
        )

    certified_dataset = (
        current.certified_data_artifact.dataset
        if current.certified_data_artifact is not None
        else current.default_dataset
    )
    data_artifact_json = {}
    if release_manifest_json is not None:
        data_artifact_json = release_manifest_json.get("artifacts", {}).get(
            certified_dataset,
            {},
        )
        if not data_artifact_json:
            raise ValueError(
                "Data release manifest "
                f"{new_release_manifest_path!r} from {repo_id}@{new_data} "
                f"does not include certified dataset {certified_dataset!r}."
            )
    dataset_repo_id = data_artifact_json.get("repo_id", repo_id)
    dataset_path = data_artifact_json.get("path", dataset_path)
    dataset_revision_default = (
        _old_revision
        if new_data == old_data and not release_manifest_override
        else new_data
    )
    dataset_revision = data_artifact_json.get("revision", dataset_revision_default)
    if (
        release_manifest_json is not None
        and new_release_manifest_revision is not None
        and dataset_repo_id == repo_id
        and dataset_revision in {new_data, release_manifest_revision}
    ):
        dataset_revision = new_release_manifest_revision

    # Only hit HF if the data version or release manifest target changed.
    if new_data != old_data or release_manifest_override:
        new_dataset_sha256 = data_artifact_json.get("sha256") or _hf_dataset_sha256(
            dataset_repo_id,
            dataset_path,
            dataset_revision,
        )
    else:
        new_dataset_sha256 = old_dataset_sha256
    new_uri = f"hf://{dataset_repo_id}/{dataset_path}@{dataset_revision}"
    policyengine_version = _pyproject_version(pyproject_path)

    # Mutate the manifest JSON in place (keep unknown fields untouched).
    manifest_json["model_package"]["version"] = new_model
    manifest_json["model_package"]["sha256"] = new_wheel_sha256
    manifest_json["model_package"]["wheel_url"] = new_wheel_url
    data_package_json["version"] = new_data
    if new_data != old_data or release_manifest_override:
        if new_release_manifest_path is not None:
            data_package_json["release_manifest_path"] = new_release_manifest_path
        if new_release_manifest_revision is not None:
            data_package_json["release_manifest_revision"] = (
                new_release_manifest_revision
            )
    manifest_json["certified_data_artifact"]["data_package"]["version"] = new_data
    manifest_json["certified_data_artifact"]["build_id"] = (
        f"{current.data_package.name}-{new_data}"
    )
    manifest_json["certified_data_artifact"]["uri"] = new_uri
    manifest_json["certified_data_artifact"]["sha256"] = new_dataset_sha256
    manifest_json["certification"]["data_build_id"] = (
        f"{current.data_package.name}-{new_data}"
    )
    manifest_json["certification"]["certified_for_model_version"] = new_model
    if release_manifest_json is not None:
        build = release_manifest_json.get("build") or {}
        built_with_model = build.get("built_with_model_package") or {}
        data_build_id = (
            build.get("build_id") or f"{current.data_package.name}-{new_data}"
        )
        manifest_json["certified_data_artifact"]["build_id"] = data_build_id
        certification_json = manifest_json["certification"]
        certification_json["data_build_id"] = data_build_id
        certification_json["certified_for_model_version"] = new_model
        certification_json["certified_by"] = (
            f"{current.data_package.name} release manifest"
        )
        built_with_model_version = built_with_model.get("version")
        if built_with_model_version is not None:
            certification_json["built_with_model_version"] = built_with_model_version
        if built_with_model.get("git_sha") is not None:
            certification_json["built_with_model_git_sha"] = built_with_model["git_sha"]
        else:
            certification_json.pop("built_with_model_git_sha", None)
        data_build_fingerprint = built_with_model.get("data_build_fingerprint")
        if data_build_fingerprint is not None:
            certification_json["data_build_fingerprint"] = data_build_fingerprint
        else:
            certification_json.pop("data_build_fingerprint", None)
        certification_json["compatibility_basis"] = (
            _release_manifest_compatibility_basis(
                release_manifest_json=release_manifest_json,
                current_manifest=current,
                package_name=package_name,
                model_version=new_model,
                built_with_model_version=built_with_model_version,
                data_build_fingerprint=data_build_fingerprint,
            )
        )
        _refresh_dataset_path_references_from_data_release(
            manifest_json,
            release_manifest_json,
            release_manifest_path=new_release_manifest_path,
            data_repo_id=repo_id,
        )

    manifest_path.write_text(
        json.dumps(manifest_json, indent=2, sort_keys=False) + "\n"
    )
    get_release_manifest.cache_clear()
    sync_release_manifest_policyengine_version(
        policyengine_version=policyengine_version,
        manifest_dir=manifest_dir,
    )

    pyproject_updated = False
    if update_pyproject and model_version is not None:
        pyproject_updated = _bump_pyproject_pin(pyproject_path, package_name, new_model)

    return RefreshResult(
        country=country,
        old_model=old_model,
        new_model=new_model,
        old_data=old_data,
        new_data=new_data,
        old_wheel_sha256=old_wheel_sha256,
        new_wheel_sha256=new_wheel_sha256,
        old_dataset_sha256=old_dataset_sha256,
        new_dataset_sha256=new_dataset_sha256,
        manifest_path=manifest_path,
        pyproject_updated=pyproject_updated,
    )


# ---------------------------------------------------------------------------
# pyproject.toml pin update (regex-based; avoids adding a TOML writer dep)
# ---------------------------------------------------------------------------


def _bump_pyproject_pin(
    pyproject_path: Path, package_name: str, new_version: str
) -> bool:
    """Update the ``{package_name}=={version}`` line under country
    extras. Returns True if a change was written.

    Only matches the exact ``"{package_name}==X.Y.Z"`` pin form that the
    release manifests produce; any looser pin (``>=``, ``~=``, extras
    markers) is left alone and signalled via the return value.
    """
    text = pyproject_path.read_text()
    pattern = rf'("{re.escape(package_name)}==)[^"]+(")'
    new_text, n = re.subn(pattern, rf"\g<1>{new_version}\g<2>", text)
    if n == 0:
        return False
    if new_text != text:
        pyproject_path.write_text(new_text)
        return True
    return False


# ---------------------------------------------------------------------------
# Trace TRO regeneration
# ---------------------------------------------------------------------------


def regenerate_trace_tro(country: str, manifest_dir: Path = MANIFEST_DIR) -> Path:
    """Regenerate ``{country}.trace.tro.jsonld`` from the country's
    release manifest plus the live data-release manifest on HF when
    that manifest is available.

    Thin wrapper around the same code path ``scripts/generate_trace_tros.py``
    uses; exposed here so the refresh function can chain
    ``refresh_release_bundle(...)`` with TRO regeneration in one call.
    """
    from policyengine.provenance.manifest import (
        DataReleaseManifestUnavailableError,
        get_data_release_manifest,
        get_release_manifest,
    )
    from policyengine.provenance.trace import (
        build_trace_tro_from_release_bundle,
        serialize_trace_tro,
    )

    get_release_manifest.cache_clear()
    get_data_release_manifest.cache_clear()
    release = get_release_manifest(country)
    try:
        data_release = get_data_release_manifest(country)
    except DataReleaseManifestUnavailableError:
        data_release = None
    tro = build_trace_tro_from_release_bundle(release, data_release)
    out_path = manifest_dir / f"{country}.trace.tro.jsonld"
    out_path.write_bytes(serialize_trace_tro(tro))
    return out_path
