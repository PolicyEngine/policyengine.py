"""Regression tests for small follow-up fixes from the audit.

Grouped together because each is small:

- ``Simulation.save()`` raises a helpful ``ValueError`` when
  ``output_dataset`` is still ``None`` (i.e. nothing has been
  computed yet), instead of the raw
  ``AttributeError: 'NoneType' object has no attribute 'save'``.

- ``scripts/check_data_staleness.py`` detects when the bundled
  release manifest's pinned country-model version drifts away
  from the installed one.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test__save_with_no_output_dataset_raises_helpfully() -> None:
    """Before the fix: raw ``AttributeError`` from ``None.save()``.
    After: ``ValueError`` that explicitly names the missing step.
    """
    pytest.importorskip("policyengine_us")

    import policyengine as pe
    from policyengine.core import Simulation
    from tests.fixtures.filtering_fixtures import create_us_test_dataset

    sim = Simulation(
        dataset=create_us_test_dataset(),
        tax_benefit_model_version=pe.us.model,
    )
    # ``output_dataset`` starts as ``None`` until ``run()`` / ``ensure()``.
    assert sim.output_dataset is None

    with pytest.raises(ValueError, match="no output_dataset"):
        sim.save()


def test__check_data_staleness_script_runs_and_reports_status() -> None:
    """Script exits 0 when pins match the installed country packages
    and prints one verdict line per country.

    In local dev against the pinned country packages, this should
    always pass. In CI we want a non-zero exit to gate the release
    pipeline, which we verify separately by inspecting the script
    logic itself (not re-running with a mismatch here, which would
    require reinstalling a country package).
    """
    pytest.importorskip("policyengine_us")

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_data_staleness.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    # Stdout has one line per configured country.
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert any(line.startswith("us:") for line in lines), result.stdout
    assert any(line.startswith("uk:") for line in lines), result.stdout
    # Exit code mirrors "any country stale". Since we pin to specific
    # country versions in pyproject.toml extras, matching is expected
    # in a clean install. If this fails, either (a) the pin drifted
    # or (b) an engineer has a newer country package installed
    # locally — both legitimate reasons to run the refresh helper.
    if result.returncode != 0:
        # Still check output shape is correct even if staleness is real.
        assert "STALE" in result.stdout, (
            f"Non-zero exit but no STALE report: {result.stdout!r} / {result.stderr!r}"
        )


def test__check_data_staleness_script_detects_drift() -> None:
    """Direct test of the country-check function so we don't have to
    actually break the installed environment to exercise the drift
    path.
    """
    pytest.importorskip("policyengine_us")

    # Import the script as a module so we can call its helper.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_data_staleness",
        REPO_ROOT / "scripts" / "check_data_staleness.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Monkey-patch the manifest path to a tmp file with a drifted pin.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_manifest_dir = Path(tmp)
        real_manifest = json.loads((module.MANIFEST_DIR / "us.json").read_text())
        real_manifest["model_package"]["version"] = "0.0.0-drift"
        (tmp_manifest_dir / "us.json").write_text(json.dumps(real_manifest, indent=2))
        module.MANIFEST_DIR = tmp_manifest_dir
        verdict, stale = module.check_country("us")
        assert stale is True
        assert "STALE" in verdict
        assert "0.0.0-drift" in verdict
