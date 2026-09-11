"""Candidate metadata must authenticate the code Python actually resolves."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _probe(tmp_path, payload, setup):
    manifest = tmp_path / "development.json"
    manifest.write_text(json.dumps(payload))
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    script = "\n".join(
        [
            "import importlib.util, json, sys, types",
            "from pathlib import Path",
            "from tests.fixtures.spm_development import _verify_local_wheel_installations",
            f"payload = json.loads(Path({str(manifest)!r}).read_text())",
            setup,
            "_verify_local_wheel_installations(payload)",
            "assert 'policyengine_us' not in sys.modules",
            "assert 'spm_calculator' not in sys.modules",
            "print('Candidate import sources authenticated before country imports')",
        ]
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def candidate_manifest():
    from tests.fixtures.spm_development import _DEVELOPMENT_MANIFEST

    if _DEVELOPMENT_MANIFEST is None:
        pytest.skip("Requires the explicit local-wheel development manifest")
    return _DEVELOPMENT_MANIFEST


def test_authenticates_real_candidate_before_import(tmp_path, candidate_manifest):
    result = _probe(tmp_path, candidate_manifest, "")
    assert result.returncode == 0, result.stderr
    assert "authenticated before country imports" in result.stdout


@pytest.mark.parametrize(
    "import_name", ["policyengine_us", "spm_calculator", "policyengine_core"]
)
def test_rejects_pythonpath_shadow_before_executing_it(
    tmp_path, candidate_manifest, import_name
):
    shadow = tmp_path / "shadow"
    package = shadow / import_name
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "raise AssertionError('Shadow package was executed')\n"
    )
    result = _probe(
        tmp_path, candidate_manifest, f"sys.path.insert(0, {str(shadow)!r})"
    )
    assert result.returncode != 0
    assert f"Unexpected import source for {import_name}" in result.stderr
    assert "Shadow package was executed" not in result.stderr


def test_rejects_preloaded_submodule_outside_authenticated_wheel(
    tmp_path, candidate_manifest
):
    source = tmp_path / "foreign_spm.py"
    source.write_text("# Foreign module, never executed\n")
    result = _probe(
        tmp_path,
        candidate_manifest,
        "\n".join(
            [
                "module = types.ModuleType('policyengine_us.spm')",
                f"module.__file__ = {str(source)!r}",
                "module.__spec__ = importlib.util.spec_from_file_location("
                "module.__name__, module.__file__)",
                "sys.modules[module.__name__] = module",
            ]
        ),
    )
    assert result.returncode != 0
    assert "Unexpected loaded import source for policyengine_us.spm" in result.stderr
