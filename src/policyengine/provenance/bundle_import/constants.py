from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BUNDLE_DIR = REPO_ROOT / "src" / "policyengine" / "data" / "bundle"
DEFAULT_RELEASE_MANIFEST_DIR = (
    REPO_ROOT / "src" / "policyengine" / "data" / "release_manifests"
)
DEFAULT_PYPROJECT = REPO_ROOT / "pyproject.toml"
DEFAULT_CHANGELOG_DIR = REPO_ROOT / "changelog.d"
