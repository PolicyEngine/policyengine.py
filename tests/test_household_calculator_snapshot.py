"""Byte-level snapshot regression test for MicrosimulationModelVersion extraction.

These tests freeze the exact numeric outputs of both the US and UK household
calculators across a representative set of cases. The intent is to make the
base-class extraction (PR F) fail loudly if any country-specific behaviour
drifts during the refactor.

Snapshots live in ``tests/fixtures/household_calculator_snapshots/``. To refresh
them, run with ``PE_UPDATE_SNAPSHOTS=1`` set. Do **not** refresh them as part
of a refactor meant to be behaviour-preserving.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

SNAPSHOT_DIR = Path(__file__).parent / "fixtures" / "household_calculator_snapshots"
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


def _check_snapshot(
    name: str, data: dict, exclude: dict[str, str] | None = None
) -> None:
    path = SNAPSHOT_DIR / f"{name}.json"
    rounded = {k: _round(v) for k, v in sorted(data.items())}
    excluded = dict(exclude or {})

    if UPDATE or not path.exists():
        if excluded and path.exists():
            # A refresh must never launder a known country defect into the
            # expected output. Keep the pre-defect value for excluded fields so
            # PE_UPDATE_SNAPSHOTS=1 cannot quietly freeze the wrong number.
            previous = json.loads(path.read_text())
            for key in excluded:
                if key in previous:
                    rounded[key] = previous[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rounded, indent=2, sort_keys=True) + "\n")
        if not UPDATE:
            pytest.skip(f"Created missing snapshot {path.name}; re-run to verify")
        return

    expected = json.loads(path.read_text())
    diffs = []
    all_keys = (set(expected) | set(rounded)) - set(excluded)
    for key in sorted(all_keys):
        if key not in expected:
            diffs.append(f"  new key: {key}={rounded[key]!r}")
        elif key not in rounded:
            diffs.append(f"  removed key: {key}={expected[key]!r}")
        elif expected[key] != rounded[key]:
            diffs.append(f"  {key}: expected {expected[key]!r}, got {rounded[key]!r}")
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


SNAP_ANNUALIZATION_ISSUE = "https://github.com/PolicyEngine/policyengine-us/issues/9447"

# Fields whose expected value is contaminated by a country defect. They are
# excluded from the comparison rather than rebaselined, so the rest of the case
# keeps protecting against drift while the wrong number is never frozen in.
#
# For 2026 policyengine-us reports one month's SNAP allotment where the annual
# value belongs (spm_unit.snap 3596.04 -> 298.00); the three resource fields
# below are downstream sums of it. The behaviour is identical on
# policyengine-us 1.825.2 and 2.0.x, so it predates the canonical SPM release
# and is not drift this pin introduced.
#
# It is also not the wrapper's: on a bare policyengine_us.Simulation, annual
# `snap` sums its monthly values and only some months resolve — 2024 picks up
# November and December alone (584 = 2 x 292), 2025 picks up all twelve
# (3522 = 9 x 292 + 3 x 298), 2026 picks up January alone (298), and 2027 picks
# up none (0). The stored 3596.04 was the correct twelve-month sum under the
# older uprating index (9 x 298 + 3 x 304.68); on this pin the correct annual
# figure would be 3607.56 (9 x 298 + 3 x 308.52), so rebaselining to 298.00
# would freeze about a twelfth of the real benefit into the expected output.
# Instead test_snap_annualization_defect_still_present fails loudly the moment
# the country annualizes SNAP again.
COUNTRY_DEFECT_EXCLUSIONS: dict[str, dict[str, str]] = {
    "us_single_adult_no_income": {
        "spm_unit.snap": SNAP_ANNUALIZATION_ISSUE,
        "household.household_benefits": SNAP_ANNUALIZATION_ISSUE,
        "household.household_net_income": SNAP_ANNUALIZATION_ISSUE,
        "spm_unit.spm_unit_net_income": SNAP_ANNUALIZATION_ISSUE,
    },
}


@pytest.mark.parametrize("case_name", sorted(US_CASES))
def test_us_household_snapshot(case_name: str) -> None:
    pytest.importorskip("policyengine_us")
    import policyengine as pe

    kwargs = US_CASES[case_name]
    result = pe.us.calculate_household(**kwargs, spm={"geography_kind": "national"})
    out: dict[str, float] = {}
    # Provenance is an additive receipt tested in test_spm_household.py; keep
    # this historical snapshot focused on its existing numeric output contract.
    values = result.to_dict()
    values.pop("provenance", None)
    _flatten("", values, out)
    _check_snapshot(case_name, out, exclude=COUNTRY_DEFECT_EXCLUSIONS.get(case_name))


def test_snap_annualization_defect_still_present() -> None:
    """Fail loudly when policyengine-us#9447 is fixed.

    While the defect stands, the fields in ``COUNTRY_DEFECT_EXCLUSIONS`` are
    excluded from ``test_us_household_snapshot[us_single_adult_no_income]``.
    A correctly annualized 2026 benefit for a one-person unit with no income is
    3607.56 on this pin (nine months at the 298.00 allotment plus three at the
    uprated 308.52); the country currently returns January alone. When that
    changes this assertion fails: drop the exclusion entry, regenerate
    ``us_single_adult_no_income.json``, and delete this test.
    """
    pytest.importorskip("policyengine_us")
    import policyengine as pe

    result = pe.us.calculate_household(
        **US_CASES["us_single_adult_no_income"], spm={"geography_kind": "national"}
    )
    snap = result.spm_unit.snap
    assert snap < 1_000, (
        f"policyengine-us returned annual SNAP {snap:.2f}, which is no longer a "
        f"single month's allotment. {SNAP_ANNUALIZATION_ISSUE} appears fixed: "
        "remove the COUNTRY_DEFECT_EXCLUSIONS entry for "
        "us_single_adult_no_income, regenerate that snapshot, and delete this "
        "test."
    )


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
