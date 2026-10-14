"""Unit tests for ConstituencyImpact output class."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.data.uk_geography_assets import packaged_uk_area_list_path
from policyengine.outputs.constituency_impact import (
    ConstituencyImpact,
    compute_uk_constituency_impacts,
)
from policyengine.outputs.uk_geography_assets import CONSTITUENCY_ASSET_SPEC

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
    csv_path = tmp_path / "constituencies.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return str(csv_path)


def test_basic_constituency_longwise_grouping(tmp_path):
    """Two constituencies with household geography codes produce metrics."""
    baseline = _make_sim(
        {
            "constituency_code_oa": ["C001", "C001", b"C002", ""],
            "household_net_income": [50000.0, 60000.0, 40000.0, 30000.0],
            "household_weight": [2.0, 1.0, 3.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "constituency_code_oa": ["C001", "C001", b"C002", ""],
            "household_net_income": [52000.0, 62000.0, 43000.0, 33000.0],
            "household_weight": [2.0, 1.0, 3.0, 1.0],
        }
    )
    csv_path = _write_lookup_csv(
        tmp_path,
        [
            {"code": "C001", "name": "Constituency A", "x": 10, "y": 20},
            {"code": "C002", "name": "Constituency B", "x": 30, "y": 40},
        ],
    )

    impact = compute_uk_constituency_impacts(
        baseline,
        reform,
        constituency_csv_path=csv_path,
        download_missing_assets=False,
    )

    assert impact.constituency_results is not None
    assert len(impact.constituency_results) == 2

    by_code = {r["constituency_code"]: r for r in impact.constituency_results}

    c1 = by_code["C001"]
    assert abs(c1["average_household_income_change"] - 2000.0) < 1e-6
    assert c1["constituency_name"] == "Constituency A"
    assert c1["x"] == 10
    assert c1["y"] == 20
    assert c1["population"] == 3.0

    c2 = by_code["C002"]
    assert abs(c2["average_household_income_change"] - 3000.0) < 1e-6
    assert c2["constituency_name"] == "Constituency B"
    assert c2["population"] == 3.0


def test_zero_weight_constituency_skipped(tmp_path):
    """A constituency with all-zero household weights produces no result."""
    baseline = _make_sim(
        {
            "constituency_code_oa": ["C001", "C002"],
            "household_net_income": [50000.0, 60000.0],
            "household_weight": [1.0, 0.0],
        }
    )
    reform = _make_sim(
        {
            "constituency_code_oa": ["C001", "C002"],
            "household_net_income": [55000.0, 65000.0],
            "household_weight": [1.0, 0.0],
        }
    )
    csv_path = _write_lookup_csv(
        tmp_path,
        [
            {"code": "C001", "name": "A", "x": 0, "y": 0},
            {"code": "C002", "name": "B", "x": 0, "y": 0},
        ],
    )

    impact = compute_uk_constituency_impacts(
        baseline,
        reform,
        constituency_csv_path=csv_path,
        download_missing_assets=False,
    )

    assert len(impact.constituency_results) == 1
    assert impact.constituency_results[0]["constituency_code"] == "C001"


def test_relative_change(tmp_path):
    """Relative household income change is computed correctly."""
    baseline = _make_sim(
        {
            "constituency_code_oa": ["C001"],
            "household_net_income": [100000.0],
            "household_weight": [1.0],
        }
    )
    reform = _make_sim(
        {
            "constituency_code_oa": ["C001"],
            "household_net_income": [110000.0],
            "household_weight": [1.0],
        }
    )
    csv_path = _write_lookup_csv(
        tmp_path,
        [{"code": "C001", "name": "A", "x": 0, "y": 0}],
    )

    impact = compute_uk_constituency_impacts(
        baseline,
        reform,
        constituency_csv_path=csv_path,
        download_missing_assets=False,
    )

    assert (
        abs(impact.constituency_results[0]["relative_household_income_change"] - 0.1)
        < 1e-6
    )


def test_compute_labels_with_packaged_area_list_by_default(
    tmp_path,
):
    """Labels come from the packaged list, not local or downloaded files."""
    baseline = _make_sim(
        {
            "constituency_code_oa": ["E14001063", "UNLISTED"],
            "household_net_income": [100.0, 200.0],
            "household_weight": [1.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "constituency_code_oa": ["E14001063", "UNLISTED"],
            "household_net_income": [110.0, 220.0],
            "household_weight": [1.0, 1.0],
        }
    )
    # A stale lookup in a local search dir (the old GCS download cache) is
    # ignored.
    pd.DataFrame([{"code": "E14001063", "name": "Stale", "x": 0, "y": 0}]).to_csv(
        tmp_path / CONSTITUENCY_ASSET_SPEC.lookup_csv_filename, index=False
    )

    with patch(
        "policyengine.outputs.uk_geography_impact.default_local_search_dirs",
        return_value=[tmp_path],
    ):
        impact = compute_uk_constituency_impacts(
            baseline,
            reform,
            download_missing_assets=True,
        )

    assert impact.constituency_csv_path == packaged_uk_area_list_path("constituency")
    assert impact.constituency_csv_path.endswith("constituencies_2024.csv")
    by_code = {row["constituency_code"]: row for row in impact.constituency_results}
    assert by_code["E14001063"]["constituency_name"] == "Aldershot"
    assert (by_code["E14001063"]["x"], by_code["E14001063"]["y"]) == (56, -40)
    assert by_code["UNLISTED"]["constituency_name"] == "UNLISTED"
    assert by_code["UNLISTED"]["x"] is None


def test_compute_constituency_impacts_does_not_require_lookup_csv_or_matrix(
    tmp_path,
):
    baseline = _make_sim(
        {
            "constituency_code_oa": ["C001"],
            "household_net_income": [100.0],
            "household_weight": [1.0],
        }
    )
    reform = _make_sim(
        {
            "constituency_code_oa": ["C001"],
            "household_net_income": [110.0],
            "household_weight": [1.0],
        }
    )

    legacy_matrix_path = str(tmp_path / "legacy-unused.h5")
    with patch(
        "policyengine.outputs.uk_geography_impact.default_local_search_dirs",
        return_value=[tmp_path / "missing"],
    ):
        impact = compute_uk_constituency_impacts(
            baseline,
            reform,
            weight_matrix_path=legacy_matrix_path,
            download_missing_assets=False,
        )

    assert impact.weight_matrix_path == legacy_matrix_path
    assert len(impact.constituency_results) == 1
    result = impact.constituency_results[0]
    assert result["constituency_code"] == "C001"
    assert result["constituency_name"] == "C001"
    assert result["x"] is None
    assert result["y"] is None


def test_compute_constituency_impacts_requires_longwise_geography_column():
    baseline = _make_sim(
        {
            "household_net_income": [100.0],
            "household_weight": [1.0],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [110.0],
            "household_weight": [1.0],
        }
    )

    with pytest.raises(ValueError, match="constituency_code_oa"):
        compute_uk_constituency_impacts(
            baseline,
            reform,
            download_missing_assets=False,
        )


def test_constituency_impacts_warn_that_they_are_not_disclosure_controlled(caplog):
    household = {
        "household_net_income": [100.0],
        "household_weight": [1.0],
        "constituency_code_oa": ["A001"],
    }
    baseline, reform = _make_sim(household), _make_sim(household)
    message = "not disclosure-controlled.*compute_uk_geography_disclosure"

    with pytest.warns(DeprecationWarning, match=message):
        compute_uk_constituency_impacts(baseline, reform, download_missing_assets=False)
    impact = ConstituencyImpact.model_construct(
        baseline_simulation=baseline, reform_simulation=reform
    )
    with pytest.warns(DeprecationWarning, match=message):
        impact.run()
    # policyengine-core silences Python warnings once a country model loads,
    # so the message must also reach the log.
    logged = [record.getMessage() for record in caplog.records]
    assert sum("not disclosure-controlled" in line for line in logged) == 2
