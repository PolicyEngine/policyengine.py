from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
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
        bundle.get_install_target("us", "3.14")


def test_repository_bundle_consistency_check_passes() -> None:
    assert check_bundle_consistency.check_bundle_consistency() == []
