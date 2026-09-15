"""Exercise the bundle commands as CI runs them before runtime installation."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def bootstrap_checkout(tmp_path):
    paths = (
        "scripts/bundle.py",
        "scripts/generate_bundle_artifacts.py",
        "src/policyengine/provenance/bundle_validation.py",
        "src/policyengine/data/bundle/manifest.json",
        "pyproject.toml",
    )
    for path in paths:
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / path, destination)
    return tmp_path


def _bootstrap(checkout, *arguments):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return subprocess.run(
        [sys.executable, "-S", *arguments],
        cwd=checkout,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ("scripts/bundle.py", "check"),
        ("scripts/bundle.py", "generate"),
        ("scripts/generate_bundle_artifacts.py", "--check"),
        ("scripts/generate_bundle_artifacts.py",),
    ],
)
def test_bundle_commands_work_without_site_packages(bootstrap_checkout, arguments):
    manifest = bootstrap_checkout / "src/policyengine/data/bundle/manifest.json"
    pyproject = bootstrap_checkout / "pyproject.toml"
    before = (manifest.read_bytes(), pyproject.read_bytes())
    result = _bootstrap(bootstrap_checkout, *arguments)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (manifest.read_bytes(), pyproject.read_bytes()) == before


def test_dependency_free_check_keeps_published_spm_gate(bootstrap_checkout):
    manifest = bootstrap_checkout / "src/policyengine/data/bundle/manifest.json"
    staged = json.loads(manifest.read_text())
    staged["packages"].pop("spm-calculator", None)
    manifest.write_text(json.dumps(staged))
    result = _bootstrap(
        bootstrap_checkout, "scripts/bundle.py", "check", "--published-spm"
    )
    assert result.returncode == 2
    assert "no published spm-calculator pin" in result.stderr
    assert "ModuleNotFoundError" not in result.stderr


@pytest.mark.parametrize(
    "change",
    [
        {"forecast_content_sha256": "unverified"},
        {"scenario": ""},
        {"geography_kind": "metro", "geography_id": None},
        {"as_of": "2026-02-30"},
        {"provider": "/tmp/unsupported.json"},
    ],
)
def test_dependency_free_generation_validates_before_writing(
    bootstrap_checkout, change
):
    manifest = bootstrap_checkout / "src/policyengine/data/bundle/manifest.json"
    invalid = json.loads(manifest.read_text())
    invalid["measurements"]["spm"].update(change)
    manifest.write_text(json.dumps(invalid))
    before = manifest.read_bytes()
    result = _bootstrap(bootstrap_checkout, "scripts/bundle.py", "generate")
    assert result.returncode == 2
    assert "ModuleNotFoundError" not in result.stderr
    assert manifest.read_bytes() == before


def test_release_checks_published_spm_before_publication_and_after_pypi_visibility():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/push.yaml").read_text())
    publish_steps = workflow["jobs"]["Publish"]["steps"]
    # Publish installs the package first, so its gate is the full bundle check
    # rather than the dependency-light one NotifyConsumers has to use.
    prepublication_gate = next(
        index
        for index, step in enumerate(publish_steps)
        if "bundle.py check --published-spm" in step.get("run", "")
    )
    publication = next(
        index
        for index, step in enumerate(publish_steps)
        if step.get("uses", "").startswith("pypa/gh-action-pypi-publish@")
    )
    assert prepublication_gate < publication
    notify = workflow["jobs"]["NotifyConsumers"]
    assert "Publish" in notify["needs"]
    steps = notify["steps"]
    runs = [step.get("run", "") for step in steps]
    wait = runs.index("bash .github/wait-for-pypi.sh")
    strict_gate = runs.index("python -S scripts/bundle.py check --published-spm")
    dispatch = runs.index("bash .github/dispatch-policyengine-release.sh")
    assert wait < strict_gate < dispatch
