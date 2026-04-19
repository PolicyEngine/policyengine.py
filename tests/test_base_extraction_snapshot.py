"""Byte-level snapshot regression test for MicrosimulationModelVersion extraction.

These tests freeze the exact numeric outputs of both the US and UK household
calculators across a representative set of cases. The intent is to make the
base-class extraction (PR F) fail loudly if any country-specific behaviour
drifts during the refactor.

Snapshots live in ``tests/fixtures/base_extraction_snapshots/``. To refresh
them, run with ``PE_UPDATE_SNAPSHOTS=1`` set. Do **not** refresh them as part
of a refactor meant to be behaviour-preserving.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

SNAPSHOT_DIR = Path(__file__).parent / "fixtures" / "base_extraction_snapshots"
UPDATE = os.environ.get("PE_UPDATE_SNAPSHOTS") == "1"


def _flatten(prefix: str, value, out: dict[str, float]) -> None:
    """Flatten a nested ``HouseholdResult`` into ``"path.name" -> scalar``."""
    if isinstance(value, list):
        for idx, item in enumerate(value):
            _flatten(f"{prefix}[{idx}]", item, out)
        return
    if isinstance(value, dict):
        for key, sub in value.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            _flatten(new_prefix, sub, out)
        return
    if isinstance(value, bool):
        out[prefix] = float(value)
    elif isinstance(value, (int, float)):
        out[prefix] = float(value)
    else:
        out[prefix] = str(value)


def _round(value, places: int = 2):
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return round(value, places)
    return value


def _check_snapshot(name: str, data: dict) -> None:
    path = SNAPSHOT_DIR / f"{name}.json"
    rounded = {k: _round(v) for k, v in sorted(data.items())}

    if UPDATE or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rounded, indent=2, sort_keys=True) + "\n")
        if not UPDATE:
            pytest.skip(f"Created missing snapshot {path.name}; re-run to verify")
        return

    expected = json.loads(path.read_text())
    diffs = []
    all_keys = set(expected) | set(rounded)
    for key in sorted(all_keys):
        if key not in expected:
            diffs.append(f"  new key: {key}={rounded[key]!r}")
        elif key not in rounded:
            diffs.append(f"  removed key: {key}={expected[key]!r}")
        elif expected[key] != rounded[key]:
            diffs.append(
                f"  {key}: expected {expected[key]!r}, got {rounded[key]!r}"
            )
    assert not diffs, f"Snapshot {name} drift:\n" + "\n".join(diffs[:40])


# US cases -------------------------------------------------------------------


US_CASES = {
    "us_single_adult_no_income": dict(
        people=[{"age": 35}],
        tax_unit={"filing_status": "SINGLE"},
        year=2026,
    ),
    "us_single_adult_employment_income": dict(
        people=[{"age": 35, "employment_income": 60_000}],
        tax_unit={"filing_status": "SINGLE"},
        year=2026,
    ),
    "us_single_parent_one_child": dict(
        people=[
            {"age": 32, "employment_income": 40_000},
            {"age": 5},
        ],
        tax_unit={"filing_status": "HEAD_OF_HOUSEHOLD"},
        year=2026,
    ),
    "us_married_two_kids_high_income": dict(
        people=[
            {"age": 42, "employment_income": 150_000},
            {"age": 40, "employment_income": 90_000},
            {"age": 8},
            {"age": 3},
        ],
        tax_unit={"filing_status": "JOINT"},
        year=2026,
    ),
}


@pytest.mark.parametrize("case_name", sorted(US_CASES))
def test_us_household_snapshot(case_name: str) -> None:
    pytest.importorskip("policyengine_us")
    import policyengine as pe

    kwargs = US_CASES[case_name]
    result = pe.us.calculate_household(**kwargs)
    out: dict[str, float] = {}
    _flatten("", result.to_dict(), out)
    _check_snapshot(case_name, out)


# UK cases -------------------------------------------------------------------


UK_CASES = {
    "uk_single_adult_no_income": dict(
        people=[{"age": 35}],
        year=2026,
    ),
    "uk_single_adult_employment_income": dict(
        people=[{"age": 35, "employment_income": 30_000}],
        year=2026,
    ),
    "uk_single_parent_one_child": dict(
        people=[
            {"age": 32, "employment_income": 25_000},
            {"age": 5},
        ],
        year=2026,
    ),
    "uk_couple_two_kids": dict(
        people=[
            {"age": 42, "employment_income": 55_000},
            {"age": 40, "employment_income": 35_000},
            {"age": 8},
            {"age": 3},
        ],
        year=2026,
    ),
}


@pytest.mark.parametrize("case_name", sorted(UK_CASES))
def test_uk_household_snapshot(case_name: str) -> None:
    pytest.importorskip("policyengine_uk")
    import policyengine as pe

    kwargs = UK_CASES[case_name]
    result = pe.uk.calculate_household(**kwargs)
    out: dict[str, float] = {}
    _flatten("", result.to_dict(), out)
    _check_snapshot(case_name, out)


# Model-version metadata snapshots -------------------------------------------


def test_us_model_version_surface() -> None:
    """Freeze the exposed surface of ``us_latest`` (variables, parameters).

    If the base-class extraction accidentally changes how variables or
    parameters are loaded from ``policyengine_us.system``, these counts will
    drift. The snapshot intentionally rounds to stable aggregates rather than
    dumping the full variable list so that unrelated upstream releases don't
    churn the snapshot file.
    """
    pytest.importorskip("policyengine_us")
    from policyengine.tax_benefit_models.us import us_latest

    surface = {
        "country_id": us_latest.release_manifest.country_id,
        "model_package_name": us_latest.model_package.name,
        "data_package_name": us_latest.data_package.name,
        "has_region_registry": us_latest.region_registry is not None,
        "region_registry_country": us_latest.region_registry.country_id,
        "num_variables_bucketed_100s": len(us_latest.variables) // 100,
        "num_parameters_bucketed_100s": len(us_latest.parameters) // 100,
        "has_employment_income": any(
            v.name == "employment_income" for v in us_latest.variables
        ),
        "has_income_tax": any(v.name == "income_tax" for v in us_latest.variables),
    }
    _check_snapshot("us_model_surface", surface)


def test_uk_model_version_surface() -> None:
    pytest.importorskip("policyengine_uk")
    from policyengine.tax_benefit_models.uk import uk_latest

    surface = {
        "country_id": uk_latest.release_manifest.country_id,
        "model_package_name": uk_latest.model_package.name,
        "data_package_name": uk_latest.data_package.name,
        "has_region_registry": uk_latest.region_registry is not None,
        "region_registry_country": uk_latest.region_registry.country_id,
        "num_variables_bucketed_100s": len(uk_latest.variables) // 100,
        "num_parameters_bucketed_100s": len(uk_latest.parameters) // 100,
        "has_employment_income": any(
            v.name == "employment_income" for v in uk_latest.variables
        ),
        "has_income_tax": any(v.name == "income_tax" for v in uk_latest.variables),
    }
    _check_snapshot("uk_model_surface", surface)
