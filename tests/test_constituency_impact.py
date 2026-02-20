"""Unit tests for ConstituencyImpact output class."""

import os
import tempfile
from unittest.mock import MagicMock

import h5py
import numpy as np
import pandas as pd
from microdf import MicroDataFrame

from policyengine.outputs.constituency_impact import (
    ConstituencyImpact,
    compute_uk_constituency_impacts,
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


def _make_weight_matrix_and_csv(tmpdir, n_constituencies, n_households, weights, csv_rows):
    """Create a temp H5 weight matrix and CSV metadata file."""
    h5_path = os.path.join(tmpdir, "weights.h5")
    with h5py.File(h5_path, "w") as f:
        f.create_dataset("2025", data=np.array(weights, dtype=np.float64))

    csv_path = os.path.join(tmpdir, "constituencies.csv")
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)

    return h5_path, csv_path


def test_basic_constituency_reweighting():
    """Two constituencies with known weight matrices produce correct metrics."""
    n_hh = 3
    baseline = _make_sim(
        {
            "household_net_income": [50000.0, 60000.0, 40000.0],
            "household_weight": [1.0, 1.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [52000.0, 62000.0, 42000.0],
            "household_weight": [1.0, 1.0, 1.0],
        }
    )

    # Constituency 0 weights: [2, 0, 1] → weighted baseline = 2*50k + 0 + 1*40k = 140k
    # Constituency 1 weights: [0, 3, 0] → weighted baseline = 0 + 3*60k + 0 = 180k
    weight_matrix = [[2.0, 0.0, 1.0], [0.0, 3.0, 0.0]]
    csv_rows = [
        {"code": "C001", "name": "Constituency A", "x": 10, "y": 20},
        {"code": "C002", "name": "Constituency B", "x": 30, "y": 40},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        h5_path, csv_path = _make_weight_matrix_and_csv(
            tmpdir, 2, n_hh, weight_matrix, csv_rows
        )
        impact = compute_uk_constituency_impacts(
            baseline, reform, h5_path, csv_path
        )

    assert impact.constituency_results is not None
    assert len(impact.constituency_results) == 2

    by_code = {r["constituency_code"]: r for r in impact.constituency_results}

    c1 = by_code["C001"]
    # Weighted change: (2*2000 + 0 + 1*2000) / 3 = 2000
    assert abs(c1["average_household_income_change"] - 2000.0) < 1e-6
    assert c1["constituency_name"] == "Constituency A"
    assert c1["x"] == 10
    assert c1["y"] == 20
    assert c1["population"] == 3.0

    c2 = by_code["C002"]
    # Weighted change: (0 + 3*2000 + 0) / 3 = 2000
    assert abs(c2["average_household_income_change"] - 2000.0) < 1e-6


def test_zero_weight_constituency_skipped():
    """A constituency with all-zero weights produces no result."""
    baseline = _make_sim(
        {
            "household_net_income": [50000.0, 60000.0],
            "household_weight": [1.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [55000.0, 65000.0],
            "household_weight": [1.0, 1.0],
        }
    )

    weight_matrix = [[1.0, 1.0], [0.0, 0.0]]
    csv_rows = [
        {"code": "C001", "name": "A", "x": 0, "y": 0},
        {"code": "C002", "name": "B", "x": 0, "y": 0},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        h5_path, csv_path = _make_weight_matrix_and_csv(
            tmpdir, 2, 2, weight_matrix, csv_rows
        )
        impact = compute_uk_constituency_impacts(
            baseline, reform, h5_path, csv_path
        )

    assert len(impact.constituency_results) == 1
    assert impact.constituency_results[0]["constituency_code"] == "C001"


def test_relative_change():
    """Relative household income change is computed correctly."""
    baseline = _make_sim(
        {
            "household_net_income": [100000.0],
            "household_weight": [1.0],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [110000.0],
            "household_weight": [1.0],
        }
    )

    weight_matrix = [[1.0]]
    csv_rows = [{"code": "C001", "name": "A", "x": 0, "y": 0}]

    with tempfile.TemporaryDirectory() as tmpdir:
        h5_path, csv_path = _make_weight_matrix_and_csv(
            tmpdir, 1, 1, weight_matrix, csv_rows
        )
        impact = compute_uk_constituency_impacts(
            baseline, reform, h5_path, csv_path
        )

    # 10% increase
    assert abs(impact.constituency_results[0]["relative_household_income_change"] - 0.1) < 1e-6
