"""Regression tests for small follow-up fixes from the audit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test__save_with_no_output_dataset_raises_helpfully() -> None:
    """Before: raw ``AttributeError`` from ``None.save()``."""
    pytest.importorskip("policyengine_us")

    import policyengine as pe
    from policyengine.core import Simulation
    from tests.fixtures.filtering_fixtures import create_us_test_dataset

    sim = Simulation(
        dataset=create_us_test_dataset(),
        tax_benefit_model_version=pe.us.model,
    )
    assert sim.output_dataset is None

    with pytest.raises(ValueError, match="no output_dataset"):
        sim.save()


def test__check_data_staleness_script_runs_and_reports_status() -> None:
    """The script prints one verdict line per configured country."""
    pytest.importorskip("policyengine_us")

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_data_staleness.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert any(line.startswith("us:") for line in lines), result.stdout
    assert any(line.startswith("uk:") for line in lines), result.stdout
    if result.returncode != 0:
        assert "STALE" in result.stdout, (
            f"Non-zero exit but no STALE report: {result.stdout!r} / {result.stderr!r}"
        )


def test__check_data_staleness_script_detects_drift() -> None:
    """Directly exercise the drift path without reinstalling packages."""
    pytest.importorskip("policyengine_us")

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_data_staleness",
        REPO_ROOT / "scripts" / "check_data_staleness.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    real_manifest = module.load_release_manifest("us").model_copy(deep=True)
    real_manifest.model_package.version = "0.0.0-drift"

    def drifted_manifest(country: str):
        return real_manifest

    module.load_release_manifest = drifted_manifest

    verdict, stale = module.check_country("us")
    assert stale is True
    assert "STALE" in verdict
    assert "0.0.0-drift" in verdict
