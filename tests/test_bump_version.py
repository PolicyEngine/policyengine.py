from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / ".github" / "bump_version.py"

spec = importlib.util.spec_from_file_location("bump_version", MODULE_PATH)
bump_version = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bump_version)


def test_get_current_version_prefers_highest_seen_version(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "3.4.1"\n')
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "## [3.4.1] - 2026-04-13\n\n"
        "### Changed\n\n"
        "- Current change.\n\n"
        "## [3.4.2] - 2026-04-12\n\n"
        "### Changed\n\n"
        "- Prior release.\n"
    )

    current = bump_version.get_current_version(pyproject, changelog, tmp_path)

    assert current == "3.4.2"


def test_get_current_version_uses_git_tags_when_available(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "3.4.1"\n')
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [3.4.1] - 2026-04-13\n")

    monkeypatch.setattr(
        bump_version,
        "get_git_tag_versions",
        lambda _repo_root: ["3.4.3"],
    )

    current = bump_version.get_current_version(pyproject, changelog, tmp_path)

    assert current == "3.4.3"


def test_update_file_replaces_stale_version_field(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "3.4.1"\n')

    bump_version.update_file(pyproject, "3.4.3")

    assert 'version = "3.4.3"' in pyproject.read_text()
