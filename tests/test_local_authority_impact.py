"""Unit tests for LocalAuthorityImpact output class."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.outputs.local_authority_impact import (
    compute_uk_local_authority_impacts,
)
from policyengine.outputs.uk_geography_assets import LOCAL_AUTHORITY_ASSET_SPEC


def _make_sim(household_data: dict) -> MagicMock:
    """Create a mock Simulation with household-level data."""
    hh_df = MicroDataFrame(
        pd.DataFrame(household_data),
        weights="household_weight",
    )
    sim = MagicMock()
    sim.output_dataset.data.household = hh_df
    sim.id = "test-sim"
    return sim


def _write_lookup_csv(tmp_path, rows) -> str:
    csv_path = tmp_path / "local_authorities.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return str(csv_path)


def test_basic_local_authority_longwise_grouping(tmp_path):
    """Two local authorities with household geography codes produce metrics."""
    baseline = _make_sim(
        {
            "la_code_oa": ["LA001", "LA001", b"LA002", ""],
            "household_net_income": [50000.0, 60000.0, 40000.0, 30000.0],
            "household_weight": [2.0, 1.0, 3.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "la_code_oa": ["LA001", "LA001", b"LA002", ""],
            "household_net_income": [53000.0, 63000.0, 43000.0, 33000.0],
            "household_weight": [2.0, 1.0, 3.0, 1.0],
        }
    )
    csv_path = _write_lookup_csv(
        tmp_path,
        [
            {"code": "LA001", "name": "Authority A", "x": 5, "y": 15},
            {"code": "LA002", "name": "Authority B", "x": 25, "y": 35},
        ],
    )

    impact = compute_uk_local_authority_impacts(
        baseline,
        reform,
        local_authority_csv_path=csv_path,
        download_missing_assets=False,
    )

    assert impact.local_authority_results is not None
    assert len(impact.local_authority_results) == 2

    by_code = {r["local_authority_code"]: r for r in impact.local_authority_results}

    la1 = by_code["LA001"]
    assert abs(la1["average_household_income_change"] - 3000.0) < 1e-6
    assert la1["local_authority_name"] == "Authority A"
    assert la1["x"] == 5
    assert la1["y"] == 15
    assert la1["population"] == 3.0

    la2 = by_code["LA002"]
    assert abs(la2["average_household_income_change"] - 3000.0) < 1e-6
    assert la2["local_authority_name"] == "Authority B"
    assert la2["population"] == 3.0


def test_zero_weight_la_skipped(tmp_path):
    """A local authority with all-zero household weights produces no result."""
    baseline = _make_sim(
        {
            "la_code_oa": ["LA001", "LA002"],
            "household_net_income": [50000.0, 60000.0],
            "household_weight": [1.0, 0.0],
        }
    )
    reform = _make_sim(
        {
            "la_code_oa": ["LA001", "LA002"],
            "household_net_income": [55000.0, 65000.0],
            "household_weight": [1.0, 0.0],
        }
    )
    csv_path = _write_lookup_csv(
        tmp_path,
        [
            {"code": "LA001", "name": "A", "x": 0, "y": 0},
            {"code": "LA002", "name": "B", "x": 0, "y": 0},
        ],
    )

    impact = compute_uk_local_authority_impacts(
        baseline,
        reform,
        local_authority_csv_path=csv_path,
        download_missing_assets=False,
    )

    assert len(impact.local_authority_results) == 1
    assert impact.local_authority_results[0]["local_authority_code"] == "LA001"


def test_relative_change(tmp_path):
    """Relative household income change is computed correctly."""
    baseline = _make_sim(
        {
            "la_code_oa": ["LA001"],
            "household_net_income": [100000.0],
            "household_weight": [1.0],
        }
    )
    reform = _make_sim(
        {
            "la_code_oa": ["LA001"],
            "household_net_income": [115000.0],
            "household_weight": [1.0],
        }
    )
    csv_path = _write_lookup_csv(
        tmp_path,
        [{"code": "LA001", "name": "A", "x": 0, "y": 0}],
    )

    impact = compute_uk_local_authority_impacts(
        baseline,
        reform,
        local_authority_csv_path=csv_path,
        download_missing_assets=False,
    )

    assert (
        abs(
            impact.local_authority_results[0]["relative_household_income_change"] - 0.15
        )
        < 1e-6
    )


def test_compute_uses_local_lookup_csv_without_matrix_or_gcs(
    tmp_path,
):
    """The helper can enrich labels from local CSV without matrix assets."""
    baseline = _make_sim(
        {
            "la_code_oa": ["LA001", "LA002"],
            "household_net_income": [100.0, 200.0],
            "household_weight": [1.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "la_code_oa": ["LA001", "LA002"],
            "household_net_income": [115.0, 230.0],
            "household_weight": [1.0, 1.0],
        }
    )
    csv_path = tmp_path / LOCAL_AUTHORITY_ASSET_SPEC.lookup_csv_filename
    pd.DataFrame(
        [
            {"code": "LA001", "name": "A", "x": 0, "y": 0},
            {"code": "LA002", "name": "B", "x": 1, "y": 1},
        ]
    ).to_csv(csv_path, index=False)

    with patch(
        "policyengine.outputs.uk_geography_impact.default_local_search_dirs",
        return_value=[tmp_path],
    ):
        impact = compute_uk_local_authority_impacts(
            baseline,
            reform,
            download_missing_assets=True,
        )

    assert impact.local_authority_csv_path == str(csv_path)
    assert len(impact.local_authority_results) == 2
    assert impact.local_authority_results[0]["local_authority_name"] == "A"


def test_compute_local_authority_impacts_does_not_require_lookup_csv_or_matrix(
    tmp_path,
):
    baseline = _make_sim(
        {
            "la_code_oa": ["LA001"],
            "household_net_income": [100.0],
            "household_weight": [1.0],
        }
    )
    reform = _make_sim(
        {
            "la_code_oa": ["LA001"],
            "household_net_income": [115.0],
            "household_weight": [1.0],
        }
    )

    legacy_matrix_path = str(tmp_path / "legacy-unused.h5")
    with patch(
        "policyengine.outputs.uk_geography_impact.default_local_search_dirs",
        return_value=[tmp_path / "missing"],
    ):
        impact = compute_uk_local_authority_impacts(
            baseline,
            reform,
            weight_matrix_path=legacy_matrix_path,
            download_missing_assets=False,
        )

    assert impact.weight_matrix_path == legacy_matrix_path
    assert len(impact.local_authority_results) == 1
    result = impact.local_authority_results[0]
    assert result["local_authority_code"] == "LA001"
    assert result["local_authority_name"] == "LA001"
    assert result["x"] is None
    assert result["y"] is None


def test_compute_local_authority_impacts_requires_longwise_geography_column():
    baseline = _make_sim(
        {
            "household_net_income": [100.0],
            "household_weight": [1.0],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [115.0],
            "household_weight": [1.0],
        }
    )

    with pytest.raises(ValueError, match="la_code_oa"):
        compute_uk_local_authority_impacts(
            baseline,
            reform,
            download_missing_assets=False,
        )
