from __future__ import annotations

import json
import os
import subprocess
import sys
from functools import lru_cache
from importlib import metadata
from importlib.resources import files
from pathlib import Path
from typing import Any, Optional

STRICT_BUNDLE_ENV_VAR = "POLICYENGINE_BUNDLE_STRICT"
TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}
BUNDLE_REPOSITORY = "PolicyEngine/policyengine-bundles"
BUNDLE_RAW_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/"
    + BUNDLE_REPOSITORY
    + "/{ref}/bundles/{version}/{path}"
)
PROFILE_EXTRAS = {
    "us": "us",
    "uk": "uk",
    "all": "uk,us",
}


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
        raise BundleMismatchError(
            f"Unknown PolicyEngine bundle profile: {profile}"
        ) from exc


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


def get_install_target(
    profile: str,
    python_version: Optional[str] = None,
) -> dict[str, Any]:
    resolved_python_version = python_version or current_python_version()
    target_key = python_version_key(resolved_python_version)
    install_targets = get_profile(profile).get("install_targets", {})
    try:
        return install_targets[target_key]
    except KeyError as exc:
        raise BundleMismatchError(
            f"No install target for profile {profile!r} and Python "
            f"{resolved_python_version!r} in PolicyEngine bundle "
            f"{get_bundle_version()}."
        ) from exc


def constraints_url(
    profile: str,
    python_version: Optional[str] = None,
    *,
    bundle_ref: Optional[str] = None,
) -> str:
    """Return the immutable constraints URL for a profile install target."""

    version = get_bundle_version()
    target = get_install_target(profile, python_version)
    constraints_path = str(target["constraints"])
    ref = bundle_ref or f"v{version}"
    return BUNDLE_RAW_URL_TEMPLATE.format(
        ref=ref,
        version=version,
        path=constraints_path,
    )


def install_profile(
    profile: str,
    python_version: Optional[str] = None,
    *,
    installer: str = "pip",
    target_python: Optional[str] = None,
    dry_run: bool = False,
    runner: Optional[Any] = None,
) -> list[str]:
    """Install a certified profile using the vendored bundle's constraints."""

    command = install_command(
        profile,
        python_version,
        installer=installer,
        target_python=target_python,
    )
    if dry_run:
        return command
    resolved_runner = runner or _run_command
    resolved_runner(command)
    return command


def install_command(
    profile: str,
    python_version: Optional[str] = None,
    *,
    installer: str = "pip",
    target_python: Optional[str] = None,
) -> list[str]:
    resolved_target_python = target_python or default_target_python()
    package_spec = policyengine_package_spec(profile)
    constraints = constraints_url(profile, python_version)
    if installer == "pip":
        return [
            resolved_target_python,
            "-m",
            "pip",
            "install",
            package_spec,
            "-c",
            constraints,
        ]
    if installer == "uv":
        return [
            "uv",
            "pip",
            "install",
            "--python",
            resolved_target_python,
            package_spec,
            "-c",
            constraints,
        ]
    raise BundleMismatchError(
        f"Unsupported installer {installer!r}. Expected 'pip' or 'uv'."
    )


def policyengine_package_spec(profile: str) -> str:
    try:
        extra = PROFILE_EXTRAS[profile]
    except KeyError as exc:
        raise BundleMismatchError(
            f"Unknown PolicyEngine bundle profile: {profile}"
        ) from exc
    return f"policyengine[{extra}]=={get_bundle_version()}"


def python_version_key(python_version: str) -> str:
    parts = python_version.split(".")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise BundleMismatchError(
            "Python version must use major.minor form, e.g. '3.13'."
        )
    return f"py{parts[0]}{parts[1]}"


def current_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def default_target_python() -> str:
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        candidate = _virtualenv_python(Path(virtual_env))
        if candidate.is_file():
            return str(candidate)
    return sys.executable


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


def _run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _virtualenv_python(virtual_env: Path) -> Path:
    if os.name == "nt":
        return virtual_env / "Scripts" / "python.exe"
    return virtual_env / "bin" / "python"


class CurrentBundle:
    def as_dict(self) -> dict[str, Any]:
        return get_bundle_manifest()

    def __getitem__(self, key: str) -> Any:
        return get_bundle_manifest()[key]


current = CurrentBundle()


def main(argv: Optional[list[str]] = None) -> int:
    from policyengine.bundle_cli import main as bundle_cli_main

    return bundle_cli_main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
