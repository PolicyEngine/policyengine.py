"""Tests for the paired Microcosm dataset/package update ceremony."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from policyengine.provenance.certification import CertificationError

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "prepare_dataset_bundle_update.py"
BUNDLE_MANIFEST = REPO_ROOT / "src/policyengine/data/bundle/manifest.json"
PYPROJECT = REPO_ROOT / "pyproject.toml"
RELEASE_MANIFEST = (
    REPO_ROOT / "tests/fixtures/release_manifests/microcosm_uk_june_shape.json"
)
RELEASE_ID = "populace-uk-2023-next-test-20260819T000000Z"
HF_REPO_ID = "policyengine/populace-uk-private"


def _load_script():
    module_name = "_test_prepare_dataset_bundle_update"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _copy_generated_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    bundle_path = tmp_path / "manifest.json"
    pyproject_path = tmp_path / "pyproject.toml"
    changelog_dir = tmp_path / "changelog.d"
    bundle_path.write_bytes(BUNDLE_MANIFEST.read_bytes())
    pyproject_path.write_bytes(PYPROJECT.read_bytes())
    return bundle_path, pyproject_path, changelog_dir


def test_local_manifest_prepares_paired_update_without_network(monkeypatch, tmp_path):
    module = _load_script()
    bundle_path, pyproject_path, changelog_dir = _copy_generated_inputs(tmp_path)
    fetch = Mock(side_effect=AssertionError("local manifest must not be fetched"))
    monkeypatch.setattr(module.requests, "get", fetch)

    result = module.prepare_dataset_bundle_update(
        country="uk",
        release_id=RELEASE_ID,
        hf_repo_id=HF_REPO_ID,
        model_version="2.91.0",
        core_version="3.30.4",
        release_manifest_source=RELEASE_MANIFEST,
        bundle_path=bundle_path,
        pyproject_path=pyproject_path,
        changelog_dir=changelog_dir,
    )

    fetch.assert_not_called()
    bundle = json.loads(bundle_path.read_text())
    release = bundle["data_releases"]["uk"]
    certification = release["certification"]
    assert release["version"] == RELEASE_ID
    assert release["build_id"] == RELEASE_ID
    assert release["default_dataset_uri"] == (
        f"hf://{HF_REPO_ID}/populace_uk_2023.h5@{RELEASE_ID}"
    )
    assert release["source_manifest_uri"] == (
        f"hf://dataset/{HF_REPO_ID}@{RELEASE_ID}/"
        f"releases/{RELEASE_ID}/release_manifest.json"
    )
    assert release["release_manifest_uri"] == (
        f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/{RELEASE_ID}/"
        f"releases/{RELEASE_ID}/release_manifest.json"
    )
    assert release["datasets"]["calibration_diagnostics"]["path"] == (
        f"releases/{RELEASE_ID}/calibration_diagnostics.json"
    )
    assert certification == {
        "built_with_core_version": "3.30.0",
        "built_with_model_git_sha": "4aa4b14",
        "built_with_model_version": "2.89.2",
        "certified_by": "policyengine.py bundle certification",
        "certified_for_core_version": "3.30.4",
        "certified_for_model_version": "2.91.0",
        "compatibility_basis": "compatible_model_packages",
        "core_compatibility_basis": "compatible_core_packages",
        "data_build_id": RELEASE_ID,
    }
    assert bundle["packages"]["policyengine-uk"]["version"] == "2.91.0"
    assert bundle["packages"]["policyengine-core"]["version"] == "3.30.4"
    assert (
        bundle["packages"]["policyengine-uk"]["install_requirement"]
        == "policyengine-uk==2.91.0"
    )
    assert (
        bundle["packages"]["policyengine-core"]["install_requirement"]
        == "policyengine-core==3.30.4"
    )

    pyproject_text = pyproject_path.read_text()
    assert pyproject_text.count("policyengine-uk==2.91.0") == 3
    assert pyproject_text.count("policyengine-core==3.30.4") == 4
    assert (
        module.generate(
            check=True,
            bundle_manifest=bundle_path,
            pyproject=pyproject_path,
        )
        == 0
    )
    assert result.changelog_path.read_text() == (
        f"Pair the UK Microcosm data release `{RELEASE_ID}` with "
        "`policyengine-uk==2.91.0` and `policyengine-core==3.30.4` "
        "in the certified bundle.\n"
    )
    assert len(result.warnings) == 2


@pytest.mark.parametrize(
    ("model_version", "core_version", "message"),
    [
        ("3.0.0", "3.30.4", "policyengine-uk 3.0.0 matches neither"),
        ("2.91.0", "3.31.0", "policyengine-core 3.31.0 matches neither"),
    ],
)
def test_incompatible_package_pair_fails_before_writing(
    tmp_path,
    model_version,
    core_version,
    message,
):
    module = _load_script()
    bundle_path, pyproject_path, changelog_dir = _copy_generated_inputs(tmp_path)
    original_bundle = bundle_path.read_bytes()
    original_pyproject = pyproject_path.read_bytes()

    with pytest.raises(CertificationError, match=message):
        module.prepare_dataset_bundle_update(
            country="uk",
            release_id=RELEASE_ID,
            hf_repo_id=HF_REPO_ID,
            model_version=model_version,
            core_version=core_version,
            release_manifest_source=RELEASE_MANIFEST,
            bundle_path=bundle_path,
            pyproject_path=pyproject_path,
            changelog_dir=changelog_dir,
        )

    assert bundle_path.read_bytes() == original_bundle
    assert pyproject_path.read_bytes() == original_pyproject
    assert not changelog_dir.exists()


def test_release_id_must_match_manifest_build_before_writing(tmp_path):
    module = _load_script()
    bundle_path, pyproject_path, changelog_dir = _copy_generated_inputs(tmp_path)
    original_bundle = bundle_path.read_bytes()

    with pytest.raises(CertificationError, match="does not match requested"):
        module.prepare_dataset_bundle_update(
            country="uk",
            release_id="different-release",
            hf_repo_id=HF_REPO_ID,
            model_version="2.91.0",
            core_version="3.30.4",
            release_manifest_source=RELEASE_MANIFEST,
            bundle_path=bundle_path,
            pyproject_path=pyproject_path,
            changelog_dir=changelog_dir,
        )

    assert bundle_path.read_bytes() == original_bundle


def test_http_manifest_source_is_fetched(monkeypatch):
    module = _load_script()
    response = Mock(status_code=200, content=RELEASE_MANIFEST.read_bytes())
    fetch = Mock(return_value=response)
    monkeypatch.setattr(module.requests, "get", fetch)

    manifest, digest = module.load_release_manifest_source(
        "https://example.test/release_manifest.json"
    )

    assert manifest.build.build_id == RELEASE_ID
    assert len(digest) == 64
    fetch.assert_called_once_with(
        "https://example.test/release_manifest.json",
        timeout=30,
    )


def test_cli_accepts_required_pairing_arguments(monkeypatch, capsys):
    module = _load_script()
    prepare = Mock(
        return_value=SimpleNamespace(summary=lambda: "prepared test release")
    )
    monkeypatch.setattr(module, "prepare_dataset_bundle_update", prepare)

    assert (
        module.main(
            [
                "--country",
                "uk",
                "--microcosm-release-id",
                RELEASE_ID,
                "--hf-repo-id",
                HF_REPO_ID,
                "--model-version",
                "2.91.0",
                "--core-version",
                "3.30.4",
                "--release-manifest",
                str(RELEASE_MANIFEST),
            ]
        )
        == 0
    )

    prepare.assert_called_once_with(
        country="uk",
        release_id=RELEASE_ID,
        hf_repo_id=HF_REPO_ID,
        model_version="2.91.0",
        core_version="3.30.4",
        release_manifest_source=str(RELEASE_MANIFEST),
        fragment_name=None,
    )
    assert capsys.readouterr().out == "prepared test release\n"
