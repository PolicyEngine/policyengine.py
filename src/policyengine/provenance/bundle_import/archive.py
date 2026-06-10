from __future__ import annotations

import sys
import tarfile
from pathlib import Path

from .io import load_json, required_dict, required_string
from .types import BundleImportError


def extract_bundle_archive(*, archive_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(archive_path) as archive:
            root_name = validate_archive_members(archive)
            if sys.version_info >= (3, 12):
                archive.extractall(output_dir, filter="data")
            else:
                archive.extractall(output_dir)
    except (tarfile.TarError, OSError) as exc:
        raise BundleImportError(f"Could not extract {archive_path}: {exc}") from exc

    bundle_dir = output_dir / root_name
    if not bundle_dir.is_dir():
        raise BundleImportError(f"Archive did not contain {root_name}/.")
    return bundle_dir


def validate_archive_members(archive: tarfile.TarFile) -> str:
    members = archive.getmembers()
    if not members:
        raise BundleImportError("Bundle archive is empty.")

    roots: set[str] = set()
    for member in members:
        member_path = Path(member.name)
        if not member_path.parts:
            raise BundleImportError("Archive contains an empty member path.")
        if member_path.is_absolute() or ".." in member_path.parts:
            raise BundleImportError(f"Unsafe archive member path: {member.name}")
        if member.issym() or member.islnk():
            raise BundleImportError(
                f"Archive link members are not allowed: {member.name}"
            )
        if not member.isfile() and not member.isdir():
            raise BundleImportError(
                f"Archive special members are not allowed: {member.name}"
            )
        roots.add(member_path.parts[0])

    if len(roots) != 1:
        raise BundleImportError(
            "Bundle archive must contain exactly one root directory."
        )
    root_name = next(iter(roots))
    if not root_name.startswith("policyengine-bundle-"):
        raise BundleImportError(
            "Bundle archive root must be named policyengine-bundle-<version>."
        )
    if root_name == "policyengine-bundle-":
        raise BundleImportError("Bundle archive root is missing a version.")
    return root_name


def validate_bundle_manifest(bundle: dict, bundle_dir: Path) -> None:
    schema_version = bundle.get("schema_version")
    if schema_version != 2:
        raise BundleImportError(
            "Only schema v2 policyengine-bundles archives can be imported; "
            f"got schema_version={schema_version!r}."
        )
    bundle_version = required_string(bundle, "bundle_version")
    expected_root = f"policyengine-bundle-{bundle_version}"
    if bundle_dir.name != expected_root:
        raise BundleImportError(
            "Bundle archive root does not match bundle_version: "
            f"expected {expected_root}, got {bundle_dir.name}."
        )
    required_dict(bundle, "countries")
    required_dict(bundle, "packages")
    validation_report = required_string(bundle, "validation_report")
    report = load_json(bundle_dir / validation_report)
    if report.get("schema_version") != 2:
        raise BundleImportError("Bundle validation report must use schema v2.")


def load_country_bundles(*, bundle_dir: Path, bundle: dict) -> dict[str, dict]:
    country_paths = required_dict(bundle, "countries")
    country_bundles: dict[str, dict] = {}
    for country_id, relative_path in sorted(country_paths.items()):
        if not isinstance(country_id, str) or not isinstance(relative_path, str):
            raise BundleImportError("Bundle countries must map ids to paths.")
        country_bundle = load_json(bundle_dir / relative_path)
        if country_bundle.get("schema_version") != 2:
            raise BundleImportError(
                f"Country bundle {country_id} must use schema_version=2."
            )
        if country_bundle.get("country_id") != country_id:
            raise BundleImportError(
                f"Country bundle path for {country_id} contains country_id "
                f"{country_bundle.get('country_id')!r}."
            )
        if country_bundle.get("bundle_version") != bundle.get("bundle_version"):
            raise BundleImportError(
                f"Country bundle {country_id} bundle_version does not match "
                "bundle.json."
            )
        country_bundles[country_id] = country_bundle
    return country_bundles
