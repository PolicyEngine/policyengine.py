from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / ".github" / "bump_version.py"

spec = importlib.util.spec_from_file_location("bump_version", MODULE_PATH)
bump_version = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bump_version)


def test_infer_bump_uses_flat_towncrier_fragment_types(tmp_path):
    changelog_dir = tmp_path / "changelog.d"
    changelog_dir.mkdir()
    (changelog_dir / "feature.added.md").write_text("Add a feature.\n")

    bump = bump_version.infer_bump(changelog_dir)

    assert bump == "minor"


def test_infer_bump_uses_breaking_fragment_precedence(tmp_path):
    changelog_dir = tmp_path / "changelog.d"
    changelog_dir.mkdir()
    (changelog_dir / "bugfix.fixed.md").write_text("Fix a bug.\n")
    (changelog_dir / "api.breaking.md").write_text("Break an API.\n")

    bump = bump_version.infer_bump(changelog_dir)

    assert bump == "major"


def test_infer_bump_rejects_fragments_towncrier_would_ignore(tmp_path):
    changelog_dir = tmp_path / "changelog.d"
    nested_dir = changelog_dir / "added"
    nested_dir.mkdir(parents=True)
    (nested_dir / "feature.md").write_text("Add a feature.\n")

    with pytest.raises(SystemExit):
        bump_version.infer_bump(changelog_dir)


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


def test_sync_release_manifest_versions_rewrites_bundle_identity(tmp_path):
    manifest_dir = tmp_path / "release_manifests"
    manifest_dir.mkdir()
    manifest_path = manifest_dir / "uk.json"
    manifest_path.write_text(
        "{\n"
        '  "schema_version": 1,\n'
        '  "bundle_id": "uk-4.0.0",\n'
        '  "country_id": "uk",\n'
        '  "policyengine_version": "4.0.0"\n'
        "}\n"
    )

    bump_version.sync_release_manifest_versions(manifest_dir, "4.3.2")

    text = manifest_path.read_text()
    assert '"bundle_id": "uk-4.3.2"' in text
    assert '"policyengine_version": "4.3.2"' in text


def test_sync_release_manifest_versions_fails_when_required_field_missing(tmp_path):
    manifest_dir = tmp_path / "release_manifests"
    manifest_dir.mkdir()
    manifest_path = manifest_dir / "uk.json"
    manifest_path.write_text(
        "{\n"
        '  "schema_version": 1,\n'
        '  "bundle_id": "uk-4.0.0",\n'
        '  "country_id": "uk"\n'
        "}\n"
    )
    original = manifest_path.read_text()

    with pytest.raises(SystemExit):
        bump_version.sync_release_manifest_versions(manifest_dir, "4.3.2")

    assert manifest_path.read_text() == original
