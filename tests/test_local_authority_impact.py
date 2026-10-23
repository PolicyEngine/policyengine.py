"""Unit tests for LocalAuthorityImpact output class."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.data.uk_geography_assets import packaged_uk_area_list_path
from policyengine.outputs.local_authority_impact import (
    LocalAuthorityImpact,
    compute_uk_local_authority_impacts,
)
from policyengine.outputs.uk_geography_assets import LOCAL_AUTHORITY_ASSET_SPEC

# These outputs are deprecated: they are not disclosure-controlled. The tests
# below still pin their behaviour until they are removed.
pytestmark = pytest.mark.filterwarnings(
    "ignore:.*not disclosure-controlled.*:DeprecationWarning"
)


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


def test_compute_labels_with_packaged_area_list_by_default(
    tmp_path,
):
    """Labels come from the packaged list, not local or downloaded files."""
    baseline = _make_sim(
        {
            "la_code_oa": ["N09000011", "UNLISTED"],
            "household_net_income": [100.0, 200.0],
            "household_weight": [1.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "la_code_oa": ["N09000011", "UNLISTED"],
            "household_net_income": [110.0, 220.0],
            "household_weight": [1.0, 1.0],
        }
    )
    # A stale lookup in a local search dir (the old GCS download cache) is
    # ignored.
    pd.DataFrame([{"code": "N09000011", "name": "Stale", "x": 0, "y": 0}]).to_csv(
        tmp_path / LOCAL_AUTHORITY_ASSET_SPEC.lookup_csv_filename, index=False
    )

    with patch(
        "policyengine.outputs.uk_geography_impact.default_local_search_dirs",
        return_value=[tmp_path],
    ):
        impact = compute_uk_local_authority_impacts(
            baseline,
            reform,
            download_missing_assets=True,
        )

    assert impact.local_authority_csv_path == packaged_uk_area_list_path(
        "local_authority"
    )
    assert impact.local_authority_csv_path.endswith("local_authorities_2023.csv")
    by_code = {
        row["local_authority_code"]: row for row in impact.local_authority_results
    }
    assert by_code["N09000011"]["local_authority_name"] == "Ards and North Down"
    assert (by_code["N09000011"]["x"], by_code["N09000011"]["y"]) == (-3, 16)
    assert by_code["UNLISTED"]["local_authority_name"] == "UNLISTED"
    assert by_code["UNLISTED"]["x"] is None


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


def test_local_authority_impacts_warn_that_they_are_not_disclosure_controlled(caplog):
    household = {
        "household_net_income": [100.0],
        "household_weight": [1.0],
        "la_code_oa": ["A001"],
    }
    baseline, reform = _make_sim(household), _make_sim(household)
    message = "not disclosure-controlled.*compute_uk_geography_disclosure"

    with pytest.warns(DeprecationWarning, match=message):
        compute_uk_local_authority_impacts(
            baseline, reform, download_missing_assets=False
        )
    impact = LocalAuthorityImpact.model_construct(
        baseline_simulation=baseline, reform_simulation=reform
    )
    with pytest.warns(DeprecationWarning, match=message):
        impact.run()
    # policyengine-core silences Python warnings once a country model loads,
    # so the message must also reach the log.
    logged = [record.getMessage() for record in caplog.records]
    assert sum("not disclosure-controlled" in line for line in logged) == 2
