from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path
from typing import Any

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
VENDORED_BUNDLE_ROOT = REPO_ROOT / "src" / "policyengine" / "data"
BUNDLE_PATH = VENDORED_BUNDLE_ROOT / "bundle.json"
COUNTRY_BUNDLE_ROOT = VENDORED_BUNDLE_ROOT
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
    parser.add_argument(
        "--release-asset-dir",
        type=Path,
        help=(
            "Optional directory containing all policyengine-bundles GitHub "
            "release assets for this version."
        ),
    )
    parser.add_argument(
        "--require-certified",
        action="store_true",
        help=(
            "Require release-grade bundle evidence: digest, full validation, "
            "and no skipped or failed validation checks."
        ),
    )
    args = parser.parse_args()

    errors = check_bundle_consistency(
        args.release_bundle,
        args.release_asset_dir,
        require_certified=args.require_certified,
    )
    if errors:
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print("bundle consistency ok")
    return 0


def check_bundle_consistency(
    release_bundle: Path | None = None,
    release_asset_dir: Path | None = None,
    *,
    require_certified: bool = False,
) -> list[str]:
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
    errors.extend(_check_vendored_bundle_files(bundle))
    errors.extend(_check_country_manifests(bundle))
    if require_certified:
        errors.extend(_check_certified_bundle(bundle))
    if release_bundle is not None:
        errors.extend(_check_release_bundle(bundle, _load_json(release_bundle)))
    if release_asset_dir is not None:
        errors.extend(
            _check_release_asset_dir(
                bundle,
                release_asset_dir,
            )
        )
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
        country_bundle_file = COUNTRY_BUNDLE_ROOT / country_bundle_path
        country_manifest_file = COUNTRY_MANIFEST_ROOT / f"{country_id}.json"
        if not country_bundle_file.is_file():
            errors.append(f"{country_bundle_path} is missing.")
            continue
        if not country_manifest_file.is_file():
            errors.append(f"release_manifests/{country_id}.json is missing.")
            continue
        country_bundle = _load_json(country_bundle_file)
        country_manifest = _load_json(country_manifest_file)
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


def _check_vendored_bundle_files(bundle: dict[str, Any]) -> list[str]:
    errors = []
    for relative_path in sorted(_bundle_referenced_paths(bundle)):
        path = VENDORED_BUNDLE_ROOT / relative_path
        if not path.is_file():
            errors.append(
                f"Vendored bundle references {relative_path}, but the file is missing."
            )
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
    for field_name in ("bundle_version",):
        if vendored_bundle.get(field_name) != release_bundle.get(field_name):
            errors.append(
                f"Vendored {field_name} does not match bundle release asset: "
                f"{vendored_bundle.get(field_name)} != {release_bundle.get(field_name)}."
            )
    if vendored_bundle.get("bundle_digest") != release_bundle.get("bundle_digest"):
        if vendored_bundle.get("bundle_digest") or release_bundle.get("bundle_digest"):
            errors.append(
                "Vendored bundle_digest does not match bundle release asset: "
                f"{vendored_bundle.get('bundle_digest')} != "
                f"{release_bundle.get('bundle_digest')}."
            )
    return errors


def _check_release_asset_dir(
    vendored_bundle: dict[str, Any],
    release_asset_dir: Path,
) -> list[str]:
    version = str(vendored_bundle.get("bundle_version"))
    archive_path = release_asset_dir / f"policyengine-bundle-{version}.tar.gz"
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    summary_path = release_asset_dir / f"policyengine-bundle-{version}.json"
    bundle_path = release_asset_dir / f"bundle-{version}.json"
    report_path = release_asset_dir / f"validation-report-{version}.json"

    errors = []
    expected_assets = [
        archive_path,
        checksum_path,
        summary_path,
        bundle_path,
        report_path,
    ]
    for path in expected_assets:
        if not path.is_file():
            errors.append(f"Bundle release asset is missing: {path.name}.")
    if errors:
        return errors

    release_bundle = _load_json(bundle_path)
    errors.extend(_check_release_bundle(vendored_bundle, release_bundle))
    errors.extend(
        _check_release_summary(
            vendored_bundle=vendored_bundle,
            summary=_load_json(summary_path),
            archive_path=archive_path,
            checksum_path=checksum_path,
        )
    )
    errors.extend(_check_release_validation_report(vendored_bundle, report_path))
    errors.extend(_check_release_archive(vendored_bundle, archive_path))
    return errors


def _check_release_summary(
    *,
    vendored_bundle: dict[str, Any],
    summary: dict[str, Any],
    archive_path: Path,
    checksum_path: Path,
) -> list[str]:
    errors = []
    for field_name in ("bundle_version",):
        if vendored_bundle.get(field_name) != summary.get(field_name):
            errors.append(
                f"Vendored {field_name} does not match bundle release summary: "
                f"{vendored_bundle.get(field_name)} != {summary.get(field_name)}."
            )
    if vendored_bundle.get("bundle_digest") != summary.get("bundle_digest"):
        if vendored_bundle.get("bundle_digest") or summary.get("bundle_digest"):
            errors.append(
                "Vendored bundle_digest does not match bundle release summary: "
                f"{vendored_bundle.get('bundle_digest')} != "
                f"{summary.get('bundle_digest')}."
            )
    if summary.get("archive") != archive_path.name:
        errors.append(
            "Bundle release summary archive does not match expected asset name: "
            f"{summary.get('archive')} != {archive_path.name}."
        )

    archive_sha256 = _sha256_file(archive_path)
    if summary.get("archive_sha256") != archive_sha256:
        errors.append(
            "Bundle release summary archive_sha256 does not match archive bytes: "
            f"{summary.get('archive_sha256')} != {archive_sha256}."
        )
    checksum = _read_checksum(checksum_path)
    if checksum != archive_sha256:
        errors.append(
            "Bundle release archive checksum file does not match archive bytes: "
            f"{checksum} != {archive_sha256}."
        )
    return errors


def _check_release_validation_report(
    vendored_bundle: dict[str, Any],
    report_path: Path,
) -> list[str]:
    report_reference = vendored_bundle.get("validation_report")
    if not isinstance(report_reference, str):
        return ["Vendored bundle does not define validation_report."]
    vendored_report_path = VENDORED_BUNDLE_ROOT / report_reference
    if not vendored_report_path.is_file():
        return [f"Vendored validation report is missing: {report_reference}."]
    release_report = _load_json(report_path)
    vendored_report = _load_json(vendored_report_path)
    if release_report != vendored_report:
        return ["Release validation report does not match vendored validation report."]
    return []


def _check_release_archive(
    vendored_bundle: dict[str, Any],
    archive_path: Path,
) -> list[str]:
    version = str(vendored_bundle.get("bundle_version"))
    archive_root = f"policyengine-bundle-{version}"
    expected_members = {
        str(Path(archive_root) / relative_path)
        for relative_path in _bundle_referenced_paths(vendored_bundle)
    }
    expected_members.add(str(Path(archive_root) / "bundle.json"))

    errors = []
    with tarfile.open(archive_path) as archive:
        names = set(archive.getnames())
        missing = sorted(expected_members - names)
        if missing:
            errors.append(
                "Bundle release archive is missing referenced files: "
                + ", ".join(missing)
                + "."
            )
        for member_path in sorted(expected_members.intersection(names)):
            member = archive.extractfile(member_path)
            if member is None:
                errors.append(f"Bundle release archive {member_path} is not a file.")
                continue
            member_bytes = member.read()
            relative_path = Path(member_path).relative_to(archive_root).as_posix()
            vendored_path = _vendored_bundle_member_path(relative_path)
            if not vendored_path.is_file():
                errors.append(
                    f"Vendored file is missing for archive member {member_path}."
                )
                continue
            vendored_bytes = vendored_path.read_bytes()
            if member_bytes != vendored_bytes:
                errors.append(
                    "Bundle release archive member does not match vendored file: "
                    f"{member_path}."
                )
            if relative_path == "bundle.json":
                archive_bundle = json.loads(member_bytes.decode())
                errors.extend(_check_release_bundle(vendored_bundle, archive_bundle))
    return errors


def _vendored_bundle_member_path(relative_path: str) -> Path:
    if relative_path == "bundle.json":
        return BUNDLE_PATH
    return VENDORED_BUNDLE_ROOT / relative_path


def _check_certified_bundle(bundle: dict[str, Any]) -> list[str]:
    errors = []
    digest = bundle.get("bundle_digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        errors.append(
            "Certified bundle must define bundle_digest starting with sha256:."
        )
    report_reference = bundle.get("validation_report")
    if not isinstance(report_reference, str):
        return errors + ["Certified bundle must define validation_report."]
    report_path = VENDORED_BUNDLE_ROOT / report_reference
    if not report_path.is_file():
        return errors + [
            f"Certified bundle validation report is missing: {report_reference}."
        ]
    report = _load_json(report_path)
    if report.get("status") != "passed":
        errors.append(
            "Certified bundle validation report status must be passed: "
            f"{report.get('status')}."
        )
    metadata = report.get("metadata", {})
    if metadata.get("validation_scope") != "full":
        errors.append(
            "Certified bundle validation report must have validation_scope='full': "
            f"{metadata.get('validation_scope')}."
        )
    for check in report.get("checks", []):
        if check.get("status") in {"failed", "skipped"}:
            errors.append(
                "Certified bundle validation report contains a "
                f"{check.get('status')} check: {check.get('name')}."
            )
    return errors


def _bundle_referenced_paths(bundle: dict[str, Any]) -> set[str]:
    paths = set()
    paths.update(str(path) for path in bundle.get("countries", {}).values())
    validation_report = bundle.get("validation_report")
    if isinstance(validation_report, str):
        paths.add(validation_report)
    for profile in bundle.get("profiles", {}).values():
        for target in profile.get("install_targets", {}).values():
            for field_name in ("constraints", "lockfile"):
                path = target.get(field_name)
                if isinstance(path, str):
                    paths.add(path)
    return paths


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
    pyproject_data = tomllib.loads(pyproject.read_text())
    optional_dependencies = pyproject_data.get("project", {}).get(
        "optional-dependencies", {}
    )
    extras: dict[str, dict[str, str]] = {}
    for extra_name, dependencies in optional_dependencies.items():
        extras[extra_name] = {}
        for dependency in dependencies:
            pin = _exact_dependency_pin(dependency)
            if pin is not None:
                package_name, version = pin
                extras[extra_name][_normalized_package_name(package_name)] = version
    return extras


def _exact_dependency_pin(dependency: str) -> tuple[str, str] | None:
    requirement = dependency.split(";", 1)[0].strip()
    match = re.match(r"^([A-Za-z0-9_.-]+)\s*==\s*([^,\s]+)$", requirement)
    if match is None:
        return None
    return match.group(1), match.group(2)


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
    return re.sub(r"[-_.]+", "-", package_name).lower()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _read_checksum(path: Path) -> str:
    return path.read_text().split()[0]


if __name__ == "__main__":
    raise SystemExit(main())
