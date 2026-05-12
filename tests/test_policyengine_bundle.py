from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
VENDORED_BUNDLE_ROOT = REPO_ROOT / "src" / "policyengine" / "data"
BUNDLE_MODULE_PATH = REPO_ROOT / "src" / "policyengine" / "bundle.py"
CHECK_BUNDLE_PATH = REPO_ROOT / ".github" / "check_bundle_consistency.py"

bundle_spec = importlib.util.spec_from_file_location(
    "policyengine_bundle_for_test",
    BUNDLE_MODULE_PATH,
)
bundle = importlib.util.module_from_spec(bundle_spec)
assert bundle_spec.loader is not None
bundle_spec.loader.exec_module(bundle)

spec = importlib.util.spec_from_file_location(
    "check_bundle_consistency",
    CHECK_BUNDLE_PATH,
)
check_bundle_consistency = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(check_bundle_consistency)


class LocalPackageFiles:
    def __init__(self, path: Path):
        self.path = path

    def joinpath(self, *parts: str) -> LocalPackageFiles:
        return LocalPackageFiles(self.path.joinpath(*parts))

    def is_file(self) -> bool:
        return self.path.is_file()

    def read_text(self) -> str:
        return self.path.read_text()


bundle.files = lambda _package_name: LocalPackageFiles(
    REPO_ROOT / "src" / "policyengine"
)


def pyproject_version() -> str:
    return re.search(
        r'^version\s*=\s*"([^"]+)"',
        PYPROJECT.read_text(),
        re.MULTILINE,
    ).group(1)


def test_vendored_bundle_matches_policyengine_version() -> None:
    manifest = bundle.get_bundle_manifest()

    assert manifest["bundle_version"] == pyproject_version()
    assert manifest["policyengine"]["version"] == pyproject_version()
    assert bundle.get_bundle_digest().startswith("sha256:")


def test_country_bundle_is_vendored() -> None:
    us_bundle = bundle.get_country_bundle("us")

    assert us_bundle["country_id"] == "us"
    assert us_bundle["bundle_version"] == bundle.get_bundle_version()
    assert us_bundle["model_package"]["version"] == "1.687.0"


def test_require_bundle_strict_checks_installed_versions(monkeypatch) -> None:
    expected_versions = {
        package_name: package["version"]
        for package_name, package in bundle.current_profile_summary("us")[
            "packages"
        ].items()
    }
    monkeypatch.setattr(
        bundle,
        "_installed_version",
        lambda package_name: expected_versions[package_name],
    )

    summary = bundle.require_bundle(bundle.get_bundle_version(), profile="us")

    assert summary["profile"] == "us"
    assert summary["installed_packages"]["policyengine-us"]["matches"] is True


def test_require_bundle_strict_rejects_version_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(bundle, "_installed_version", lambda _package_name: "0.0.0")

    with pytest.raises(bundle.BundleMismatchError, match="do not match"):
        bundle.require_bundle(bundle.get_bundle_version(), profile="us")


def test_constraints_url_uses_bundle_install_target() -> None:
    assert bundle.constraints_url("us", "3.13") == (
        "https://raw.githubusercontent.com/PolicyEngine/policyengine-bundles/"
        "v4.4.2/bundles/4.4.2/install/us/py313/constraints.txt"
    )


def test_constraints_url_supports_python_314() -> None:
    assert bundle.constraints_url("us", "3.14") == (
        "https://raw.githubusercontent.com/PolicyEngine/policyengine-bundles/"
        "v4.4.2/bundles/4.4.2/install/us/py314/constraints.txt"
    )


def test_install_target_files_are_vendored() -> None:
    target = bundle.get_install_target("us", "3.13")
    target_314 = bundle.get_install_target("us", "3.14")

    assert (VENDORED_BUNDLE_ROOT / target["constraints"]).is_file()
    assert (VENDORED_BUNDLE_ROOT / target["lockfile"]).is_file()
    assert (VENDORED_BUNDLE_ROOT / target_314["constraints"]).is_file()
    assert (VENDORED_BUNDLE_ROOT / target_314["lockfile"]).is_file()
    assert (
        VENDORED_BUNDLE_ROOT / bundle.get_bundle_manifest()["validation_report"]
    ).is_file()


def test_install_command_uses_target_python_and_constraints() -> None:
    assert bundle.install_command(
        "all",
        "3.13",
        target_python="/tmp/project/.venv/bin/python",
    ) == [
        "/tmp/project/.venv/bin/python",
        "-m",
        "pip",
        "install",
        "policyengine[uk,us]==4.4.2",
        "-c",
        (
            "https://raw.githubusercontent.com/PolicyEngine/policyengine-bundles/"
            "v4.4.2/bundles/4.4.2/install/all/py313/constraints.txt"
        ),
    ]


def test_install_profile_supports_dry_run() -> None:
    command = bundle.install_profile(
        "uk",
        "3.13",
        target_python="/tmp/project/.venv/bin/python",
        dry_run=True,
    )

    assert command[0:5] == [
        "/tmp/project/.venv/bin/python",
        "-m",
        "pip",
        "install",
        "policyengine[uk]==4.4.2",
    ]


def test_install_target_rejects_unsupported_python_version() -> None:
    with pytest.raises(bundle.BundleMismatchError, match="No install target"):
        bundle.get_install_target("us", "3.12")


def test_repository_bundle_consistency_check_passes() -> None:
    assert check_bundle_consistency.check_bundle_consistency() == []


def test_release_asset_dir_consistency_check_passes(tmp_path: Path) -> None:
    asset_dir = _write_release_assets(tmp_path)

    assert (
        check_bundle_consistency.check_bundle_consistency(
            release_asset_dir=asset_dir,
        )
        == []
    )


def test_release_asset_dir_consistency_requires_archive(tmp_path: Path) -> None:
    asset_dir = _write_release_assets(tmp_path)
    version = bundle.get_bundle_version()
    (asset_dir / f"policyengine-bundle-{version}.tar.gz").unlink()

    errors = check_bundle_consistency.check_bundle_consistency(
        release_asset_dir=asset_dir,
    )

    assert (
        f"Bundle release asset is missing: policyengine-bundle-{version}.tar.gz."
        in errors
    )


def _write_release_assets(tmp_path: Path) -> Path:
    manifest = bundle.get_bundle_manifest()
    version = manifest["bundle_version"]
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()

    _write_json(asset_dir / f"bundle-{version}.json", manifest)
    validation_report = json.loads(
        (VENDORED_BUNDLE_ROOT / manifest["validation_report"]).read_text()
    )
    _write_json(asset_dir / f"validation-report-{version}.json", validation_report)

    archive_path = asset_dir / f"policyengine-bundle-{version}.tar.gz"
    archive_root = f"policyengine-bundle-{version}"
    archive_members = {
        "bundle.json",
        *check_bundle_consistency._bundle_referenced_paths(manifest),
    }
    with tarfile.open(archive_path, "w:gz") as archive:
        for relative_path in sorted(archive_members):
            archive.add(
                VENDORED_BUNDLE_ROOT / relative_path,
                arcname=str(Path(archive_root) / relative_path),
            )

    archive_sha256 = _sha256_file(archive_path)
    (asset_dir / f"policyengine-bundle-{version}.tar.gz.sha256").write_text(
        f"{archive_sha256}  {archive_path.name}\n"
    )
    _write_json(
        asset_dir / f"policyengine-bundle-{version}.json",
        {
            "bundle_version": version,
            "bundle_digest": manifest["bundle_digest"],
            "archive": archive_path.name,
            "archive_sha256": archive_sha256,
        },
    )
    return asset_dir


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
