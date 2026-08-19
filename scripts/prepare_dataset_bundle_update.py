"""Prepare an offline-friendly paired dataset and package bundle update.

The release manifest may be a local file or an HTTP(S) URL. The canonical
Hugging Face release references are built from the explicit repo and release
id, so rehearsals against a downloaded manifest do not need network access.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlsplit

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_bundle_artifacts import (  # noqa: E402
    BUNDLE_MANIFEST,
    PYPROJECT,
    generate,
    load_bundle_manifest,
    write_bundle_manifest,
)

from policyengine.provenance.certification import (  # noqa: E402
    COUNTRY_MODEL_PACKAGES,
    CertificationError,
    build_bundle_data_release_payload,
    build_country_manifest_payload,
    parse_manifest_uri,
    validate_release_package_pair,
)
from policyengine.provenance.manifest import (  # noqa: E402
    HF_REQUEST_TIMEOUT_SECONDS,
    DataReleaseManifest,
)

CORE_PACKAGE = "policyengine-core"
DEFAULT_CHANGELOG_DIR = REPO_ROOT / "changelog.d"


@dataclass(frozen=True)
class DatasetBundleUpdateResult:
    country: str
    release_id: str
    model_package: str
    model_version: str
    core_version: str
    manifest_sha256: str
    bundle_path: Path
    pyproject_path: Path
    changelog_path: Path
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"prepared {self.country} dataset release {self.release_id}",
            f"  model: {self.model_package}=={self.model_version}",
            f"  core: {CORE_PACKAGE}=={self.core_version}",
            f"  release manifest sha256: {self.manifest_sha256}",
            f"  bundle: {self.bundle_path}",
            f"  pyproject: {self.pyproject_path}",
            f"  changelog: {self.changelog_path}",
        ]
        lines.extend(f"  WARNING: {warning}" for warning in self.warnings)
        return "\n".join(lines)


def load_release_manifest_source(
    source: Union[str, Path],
) -> tuple[DataReleaseManifest, str]:
    """Load a release manifest locally, fetching only explicit HTTP(S) URLs."""

    source_text = str(source)
    if urlsplit(source_text).scheme in {"http", "https"}:
        response = requests.get(source_text, timeout=HF_REQUEST_TIMEOUT_SECONDS)
        if response.status_code != 200:
            raise CertificationError(
                "Could not fetch data release manifest "
                f"({response.status_code}) from {source_text}."
            )
        source_bytes = response.content
    else:
        path = Path(source).expanduser()
        try:
            source_bytes = path.read_bytes()
        except OSError as error:
            raise CertificationError(
                f"Could not read data release manifest from {path}: {error}"
            ) from error

    try:
        payload = json.loads(source_bytes)
        manifest = DataReleaseManifest.model_validate(payload)
    except (json.JSONDecodeError, ValueError) as error:
        raise CertificationError(
            f"Invalid data release manifest from {source_text}: {error}"
        ) from error
    return manifest, hashlib.sha256(source_bytes).hexdigest()


def canonical_release_manifest_uri(hf_repo_id: str, release_id: str) -> str:
    repo_parts = hf_repo_id.split("/")
    if (
        len(repo_parts) != 2
        or not all(repo_parts)
        or "@" in hf_repo_id
        or any(character.isspace() for character in hf_repo_id)
    ):
        raise CertificationError(
            f"Hugging Face repo id must look like 'owner/repo', got {hf_repo_id!r}."
        )
    if not release_id or re.search(r"[/@\s]", release_id):
        raise CertificationError(
            "Microcosm release id must be a non-empty Hugging Face revision "
            f"without '/', '@', or whitespace, got {release_id!r}."
        )
    return (
        f"hf://dataset/{hf_repo_id}@{release_id}/"
        f"releases/{release_id}/release_manifest.json"
    )


def validate_release_identity(
    manifest: DataReleaseManifest,
    *,
    release_id: str,
    hf_repo_id: str,
) -> None:
    build_id = manifest.build.build_id if manifest.build is not None else None
    if build_id != release_id:
        raise CertificationError(
            f"Release manifest build id {build_id!r} does not match requested "
            f"release id {release_id!r}."
        )
    default_name = manifest.default_datasets.get("national")
    if default_name is None or default_name not in manifest.artifacts:
        return
    default_artifact = manifest.artifacts[default_name]
    if default_artifact.repo_id != hf_repo_id:
        raise CertificationError(
            f"Default dataset repo {default_artifact.repo_id!r} does not match "
            f"requested Hugging Face repo {hf_repo_id!r}."
        )
    if default_artifact.revision != release_id:
        raise CertificationError(
            f"Default dataset revision {default_artifact.revision!r} does not "
            f"match requested release id {release_id!r}."
        )


def _changelog_fragment_name(country: str, release_id: str) -> str:
    safe_release_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", release_id)
    return f"dataset-{country}-{safe_release_id}.changed.md"


def write_changelog(
    *,
    changelog_dir: Path,
    country: str,
    release_id: str,
    model_package: str,
    model_version: str,
    core_version: str,
    fragment_name: Optional[str] = None,
) -> Path:
    fragment_name = fragment_name or _changelog_fragment_name(country, release_id)
    if Path(fragment_name).name != fragment_name:
        raise CertificationError("Changelog fragment name must be a filename.")
    changelog_dir.mkdir(parents=True, exist_ok=True)
    path = changelog_dir / fragment_name
    path.write_text(
        f"Pair the {country.upper()} Microcosm data release `{release_id}` with "
        f"`{model_package}=={model_version}` and "
        f"`{CORE_PACKAGE}=={core_version}` in the certified bundle.\n"
    )
    return path


def prepare_dataset_bundle_update(
    *,
    country: str,
    release_id: str,
    hf_repo_id: str,
    model_version: str,
    core_version: str,
    release_manifest_source: Union[str, Path],
    bundle_path: Path = BUNDLE_MANIFEST,
    pyproject_path: Path = PYPROJECT,
    changelog_dir: Path = DEFAULT_CHANGELOG_DIR,
    fragment_name: Optional[str] = None,
) -> DatasetBundleUpdateResult:
    if country not in COUNTRY_MODEL_PACKAGES:
        raise CertificationError(f"Unknown country {country!r}.")
    model_package = COUNTRY_MODEL_PACKAGES[country]
    manifest_uri = canonical_release_manifest_uri(hf_repo_id, release_id)
    manifest, manifest_sha256 = load_release_manifest_source(release_manifest_source)
    validate_release_identity(
        manifest,
        release_id=release_id,
        hf_repo_id=hf_repo_id,
    )
    model_basis, core_basis, warnings = validate_release_package_pair(
        manifest,
        model_package=model_package,
        model_version=model_version,
        core_package=CORE_PACKAGE,
        core_version=core_version,
    )

    bundle = load_bundle_manifest(bundle_path)
    packages = bundle.get("packages", {})
    for package_name in (model_package, CORE_PACKAGE):
        if package_name not in packages:
            raise CertificationError(
                f"Bundle manifest has no package entry for {package_name!r}."
            )
    existing_release = bundle.get("data_releases", {}).get(country, {})
    data_producer = str(existing_release.get("data_producer") or "populace")
    uri_parts = parse_manifest_uri(manifest_uri)
    country_payload = build_country_manifest_payload(
        country=country,
        manifest=manifest,
        uri_parts=uri_parts,
        policyengine_version=str(bundle["policyengine_version"]),
        model_package=model_package,
        model_version=model_version,
        model_wheel={},
        compatibility_basis=model_basis,
        core_version=core_version,
        core_compatibility_basis=core_basis,
    )
    data_release = build_bundle_data_release_payload(
        country_payload=country_payload,
        data_producer=data_producer,
        manifest_uri=manifest_uri,
        uri_parts=uri_parts,
    )

    updated = copy.deepcopy(bundle)
    updated.setdefault("data_releases", {})[country] = data_release
    updated.setdefault("countries", {}).setdefault(country, {})["model_package"] = (
        model_package
    )
    updated["packages"][model_package]["version"] = model_version
    updated["packages"][CORE_PACKAGE]["version"] = core_version
    write_bundle_manifest(updated, bundle_path)
    generate(
        check=False,
        bundle_manifest=bundle_path,
        pyproject=pyproject_path,
    )
    changelog_path = write_changelog(
        changelog_dir=changelog_dir,
        country=country,
        release_id=release_id,
        model_package=model_package,
        model_version=model_version,
        core_version=core_version,
        fragment_name=fragment_name,
    )
    return DatasetBundleUpdateResult(
        country=country,
        release_id=release_id,
        model_package=model_package,
        model_version=model_version,
        core_version=core_version,
        manifest_sha256=manifest_sha256,
        bundle_path=bundle_path,
        pyproject_path=pyproject_path,
        changelog_path=changelog_path,
        warnings=warnings,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a paired Microcosm dataset/model/core bundle update."
    )
    parser.add_argument(
        "--country", required=True, choices=sorted(COUNTRY_MODEL_PACKAGES)
    )
    parser.add_argument(
        "--release-id",
        "--microcosm-release-id",
        dest="release_id",
        required=True,
        help="Immutable Microcosm release id / Hugging Face revision.",
    )
    parser.add_argument(
        "--hf-repo-id",
        required=True,
        help="Hugging Face dataset repo id, for example owner/repo.",
    )
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--core-version", required=True)
    parser.add_argument(
        "--release-manifest",
        dest="release_manifest_source",
        required=True,
        help="Local path or HTTP(S) URL to release_manifest.json.",
    )
    parser.add_argument(
        "--fragment-name",
        default=None,
        help="Optional Towncrier fragment filename under changelog.d/.",
    )
    args = parser.parse_args(argv)

    result = prepare_dataset_bundle_update(
        country=args.country,
        release_id=args.release_id,
        hf_repo_id=args.hf_repo_id,
        model_version=args.model_version,
        core_version=args.core_version,
        release_manifest_source=args.release_manifest_source,
        fragment_name=args.fragment_name,
    )
    print(result.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
