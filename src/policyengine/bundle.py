from __future__ import annotations

import json
import os
from functools import lru_cache
from importlib import metadata
from importlib.resources import files
from typing import Any, Optional

STRICT_BUNDLE_ENV_VAR = "POLICYENGINE_BUNDLE_STRICT"
TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}


class BundleMismatchError(RuntimeError):
    """Raised when the installed runtime does not match the vendored bundle."""


@lru_cache
def get_bundle_manifest() -> dict[str, Any]:
    bundle_path = files("policyengine").joinpath("data", "bundle.json")
    if not bundle_path.is_file():
        raise BundleMismatchError("No vendored PolicyEngine bundle manifest found.")
    return json.loads(bundle_path.read_text())


def get_bundle_version() -> str:
    return str(get_bundle_manifest()["bundle_version"])


def get_bundle_digest() -> Optional[str]:
    digest = get_bundle_manifest().get("bundle_digest")
    return str(digest) if digest is not None else None


def get_profile(profile: str) -> dict[str, Any]:
    profiles = get_bundle_manifest().get("profiles", {})
    try:
        return profiles[profile]
    except KeyError as exc:
        raise BundleMismatchError(f"Unknown PolicyEngine bundle profile: {profile}") from exc


def get_country_bundle(country_id: str) -> dict[str, Any]:
    manifest = get_bundle_manifest()
    country_path = manifest.get("countries", {}).get(country_id)
    if not country_path:
        raise BundleMismatchError(
            f"No country bundle for {country_id!r} in PolicyEngine bundle "
            f"{manifest.get('bundle_version')}."
        )
    data_root = files("policyengine").joinpath("data")
    country_bundle_path = data_root.joinpath(country_path)
    if not country_bundle_path.is_file():
        raise BundleMismatchError(
            f"Country bundle {country_path!r} is referenced by bundle.json but "
            "is not vendored in this policyengine wheel."
        )
    return json.loads(country_bundle_path.read_text())


def current_profile_summary(profile: Optional[str] = None) -> dict[str, Any]:
    manifest = get_bundle_manifest()
    resolved_profile = profile or "all"
    package_names = _profile_package_names(resolved_profile)
    packages = {
        package_name: manifest["packages"][package_name]
        for package_name in package_names
    }
    return {
        "bundle_version": manifest["bundle_version"],
        "bundle_digest": manifest.get("bundle_digest"),
        "profile": resolved_profile,
        "packages": packages,
        "validation_report": manifest.get("validation_report"),
    }


def require_bundle(
    version: Optional[str] = None,
    *,
    profile: Optional[str] = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Validate that the installed runtime matches the vendored bundle."""

    manifest = get_bundle_manifest()
    expected_version = version or manifest["bundle_version"]
    if manifest["bundle_version"] != expected_version:
        raise BundleMismatchError(
            "Vendored PolicyEngine bundle version mismatch: "
            f"expected {expected_version}, got {manifest['bundle_version']}."
        )

    summary = current_profile_summary(profile)
    if not strict:
        return summary

    mismatches = []
    installed: dict[str, dict[str, Any]] = {}
    for package_name, package in summary["packages"].items():
        expected_package_version = package.get("version")
        if expected_package_version is None:
            continue
        actual_version = _installed_version(package_name)
        installed[package_name] = {
            "expected": expected_package_version,
            "actual": actual_version,
            "matches": actual_version == expected_package_version,
        }
        if actual_version != expected_package_version:
            mismatches.append(
                f"{package_name}: expected {expected_package_version}, "
                f"got {actual_version or 'not installed'}"
            )

    summary["installed_packages"] = installed
    if mismatches:
        raise BundleMismatchError(
            "Installed PolicyEngine packages do not match the vendored bundle "
            f"{manifest['bundle_version']} ({summary['profile']}): "
            + "; ".join(mismatches)
        )
    return summary


def strict_bundle_enabled() -> bool:
    return os.environ.get(STRICT_BUNDLE_ENV_VAR, "").lower() in TRUTHY_ENV_VALUES


def _profile_package_names(profile: str) -> list[str]:
    profile_manifest = get_profile(profile)
    return list(profile_manifest.get("packages", []))


def _installed_version(package_name: str) -> Optional[str]:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


class CurrentBundle:
    def as_dict(self) -> dict[str, Any]:
        return get_bundle_manifest()

    def __getitem__(self, key: str) -> Any:
        return get_bundle_manifest()[key]


current = CurrentBundle()
