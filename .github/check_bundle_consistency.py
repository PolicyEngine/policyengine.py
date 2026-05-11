from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
BUNDLE_PATH = REPO_ROOT / "src" / "policyengine" / "data" / "bundle.json"
COUNTRY_BUNDLE_ROOT = REPO_ROOT / "src" / "policyengine" / "data"
COUNTRY_MANIFEST_ROOT = (
    REPO_ROOT / "src" / "policyengine" / "data" / "release_manifests"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that policyengine.py is synchronized with its bundle."
    )
    parser.add_argument(
        "--release-bundle",
        type=Path,
        help="Optional bundle.json downloaded from the matching bundle release.",
    )
    args = parser.parse_args()

    errors = check_bundle_consistency(args.release_bundle)
    if errors:
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print("bundle consistency ok")
    return 0


def check_bundle_consistency(release_bundle: Path | None = None) -> list[str]:
    errors: list[str] = []
    bundle = _load_json(BUNDLE_PATH)
    pyproject_version = _pyproject_version(PYPROJECT)
    if bundle.get("bundle_version") != pyproject_version:
        errors.append(
            "Vendored bundle_version must match pyproject version: "
            f"{bundle.get('bundle_version')} != {pyproject_version}."
        )
    if bundle.get("policyengine", {}).get("version") != pyproject_version:
        errors.append("Vendored policyengine package pin must match pyproject version.")

    extras = _optional_dependency_pins(PYPROJECT)
    for profile in ("us", "uk"):
        errors.extend(_check_profile_extra(bundle, extras, profile))
    errors.extend(_check_dev_extra(bundle, extras))
    errors.extend(_check_country_manifests(bundle))
    if release_bundle is not None:
        errors.extend(_check_release_bundle(bundle, _load_json(release_bundle)))
    return errors


def _check_profile_extra(
    bundle: dict[str, Any],
    extras: dict[str, dict[str, str]],
    profile: str,
) -> list[str]:
    expected = _expected_profile_pins(bundle, profile)
    actual = extras.get(profile, {})
    errors = []
    for package_name, expected_version in expected.items():
        actual_version = actual.get(_normalized_package_name(package_name))
        if actual_version != expected_version:
            errors.append(
                f"[{profile}] must pin {package_name}=={expected_version}; "
                f"got {actual_version or 'missing'}."
            )
    return errors


def _check_dev_extra(
    bundle: dict[str, Any],
    extras: dict[str, dict[str, str]],
) -> list[str]:
    expected: dict[str, str] = {}
    for profile in ("us", "uk"):
        expected.update(_expected_profile_pins(bundle, profile))
    actual = extras.get("dev", {})
    errors = []
    for package_name, expected_version in expected.items():
        actual_version = actual.get(_normalized_package_name(package_name))
        if actual_version != expected_version:
            errors.append(
                f"[dev] must pin {package_name}=={expected_version}; "
                f"got {actual_version or 'missing'}."
            )
    return errors


def _check_country_manifests(bundle: dict[str, Any]) -> list[str]:
    errors = []
    for country_id, country_bundle_path in bundle.get("countries", {}).items():
        country_bundle = _load_json(COUNTRY_BUNDLE_ROOT / country_bundle_path)
        country_manifest = _load_json(COUNTRY_MANIFEST_ROOT / f"{country_id}.json")
        if country_bundle.get("bundle_version") != bundle.get("bundle_version"):
            errors.append(
                f"{country_bundle_path} bundle_version does not match bundle."
            )
        if country_manifest.get("policyengine_version") != bundle.get("bundle_version"):
            errors.append(
                f"release_manifests/{country_id}.json policyengine_version "
                "does not match bundle."
            )
        _compare_country_field(
            errors,
            country_id,
            country_manifest,
            country_bundle,
            "model_package",
        )
        _compare_country_field(
            errors,
            country_id,
            country_manifest,
            country_bundle,
            "data_package",
        )
        if country_manifest.get("default_dataset") != country_bundle.get(
            "default_dataset"
        ):
            errors.append(f"{country_id} default_dataset does not match bundle.")
    return errors


def _compare_country_field(
    errors: list[str],
    country_id: str,
    country_manifest: dict[str, Any],
    country_bundle: dict[str, Any],
    field_name: str,
) -> None:
    manifest_package = country_manifest.get(field_name, {})
    bundle_package = country_bundle.get(field_name, {})
    for key in ("name", "version"):
        if manifest_package.get(key) != bundle_package.get(key):
            errors.append(
                f"{country_id} {field_name}.{key} does not match bundle: "
                f"{manifest_package.get(key)} != {bundle_package.get(key)}."
            )


def _check_release_bundle(
    vendored_bundle: dict[str, Any],
    release_bundle: dict[str, Any],
) -> list[str]:
    errors = []
    for field_name in ("bundle_version", "bundle_digest"):
        if vendored_bundle.get(field_name) != release_bundle.get(field_name):
            errors.append(
                f"Vendored {field_name} does not match bundle release asset: "
                f"{vendored_bundle.get(field_name)} != {release_bundle.get(field_name)}."
            )
    return errors


def _expected_profile_pins(bundle: dict[str, Any], profile: str) -> dict[str, str]:
    package_names = bundle["profiles"][profile]["packages"]
    expected = {}
    for package_name in package_names:
        if package_name == "policyengine":
            continue
        version = bundle["packages"][package_name].get("version")
        if version:
            expected[package_name] = version
    return expected


def _optional_dependency_pins(pyproject: Path) -> dict[str, dict[str, str]]:
    extras: dict[str, dict[str, str]] = {}
    current_extra = None
    in_optional_dependencies = False
    for raw_line in pyproject.read_text().splitlines():
        line = raw_line.strip()
        if line == "[project.optional-dependencies]":
            in_optional_dependencies = True
            continue
        if in_optional_dependencies and line.startswith("["):
            break
        if not in_optional_dependencies or not line or line.startswith("#"):
            continue
        extra_match = re.match(r"^([A-Za-z0-9_-]+)\s*=\s*\[$", line)
        if extra_match:
            current_extra = extra_match.group(1)
            extras[current_extra] = {}
            continue
        if current_extra is None:
            continue
        if line == "]":
            current_extra = None
            continue
        dependency_match = re.match(r'^"([^"]+)"\s*,?$', line)
        if dependency_match:
            dependency = dependency_match.group(1)
            pin_match = re.match(r"^([A-Za-z0-9_.-]+)==([^;]+)$", dependency)
            if pin_match:
                extras[current_extra][_normalized_package_name(pin_match.group(1))] = (
                    pin_match.group(2)
                )
    return extras


def _pyproject_version(pyproject: Path) -> str:
    match = re.search(
        r'^version\s*=\s*"([^"]+)"',
        pyproject.read_text(),
        re.MULTILINE,
    )
    if not match:
        raise ValueError("Could not find pyproject version.")
    return match.group(1)


def _normalized_package_name(package_name: str) -> str:
    return package_name.replace("_", "-").lower()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


if __name__ == "__main__":
    raise SystemExit(main())
