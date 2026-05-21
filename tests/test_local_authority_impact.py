"""Unit tests for LocalAuthorityImpact output class."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import h5py
import numpy as np
import pandas as pd
from microdf import MicroDataFrame

from policyengine.outputs.local_authority_impact import (
    compute_uk_local_authority_impacts,
)
from policyengine.outputs.uk_geography_assets import (
    LOCAL_AUTHORITY_ASSET_SPEC,
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


def _make_weight_matrix_and_csv(tmpdir, weights, csv_rows):
    """Create a temp H5 weight matrix and CSV metadata file."""
    h5_path = os.path.join(tmpdir, "la_weights.h5")
    with h5py.File(h5_path, "w") as f:
        f.create_dataset("2025", data=np.array(weights, dtype=np.float64))

    csv_path = os.path.join(tmpdir, "local_authorities.csv")
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)

    return h5_path, csv_path


def test_basic_local_authority_reweighting():
    """Two LAs with known weight matrices produce correct metrics."""
    baseline = _make_sim(
        {
            "household_net_income": [50000.0, 60000.0, 40000.0],
            "household_weight": [1.0, 1.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [53000.0, 63000.0, 43000.0],
            "household_weight": [1.0, 1.0, 1.0],
        }
    )

    weight_matrix = [[1.0, 1.0, 0.0], [0.0, 1.0, 2.0]]
    csv_rows = [
        {"code": "LA001", "name": "Authority A", "x": 5, "y": 15},
        {"code": "LA002", "name": "Authority B", "x": 25, "y": 35},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        h5_path, csv_path = _make_weight_matrix_and_csv(tmpdir, weight_matrix, csv_rows)
        impact = compute_uk_local_authority_impacts(baseline, reform, h5_path, csv_path)

    assert impact.local_authority_results is not None
    assert len(impact.local_authority_results) == 2

    by_code = {r["local_authority_code"]: r for r in impact.local_authority_results}

    la1 = by_code["LA001"]
    # Weighted change: (1*3000 + 1*3000) / 2 = 3000
    assert abs(la1["average_household_income_change"] - 3000.0) < 1e-6
    assert la1["local_authority_name"] == "Authority A"
    assert la1["population"] == 2.0

    la2 = by_code["LA002"]
    # Weighted change: (0 + 1*3000 + 2*3000) / 3 = 3000
    assert abs(la2["average_household_income_change"] - 3000.0) < 1e-6


def test_zero_weight_la_skipped():
    """A local authority with all-zero weights produces no result."""
    baseline = _make_sim(
        {
            "household_net_income": [50000.0],
            "household_weight": [1.0],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [55000.0],
            "household_weight": [1.0],
        }
    )

    weight_matrix = [[1.0], [0.0]]
    csv_rows = [
        {"code": "LA001", "name": "A", "x": 0, "y": 0},
        {"code": "LA002", "name": "B", "x": 0, "y": 0},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        h5_path, csv_path = _make_weight_matrix_and_csv(tmpdir, weight_matrix, csv_rows)
        impact = compute_uk_local_authority_impacts(baseline, reform, h5_path, csv_path)

    assert len(impact.local_authority_results) == 1
    assert impact.local_authority_results[0]["local_authority_code"] == "LA001"


def test_compute_resolves_standard_local_authority_assets_from_default_local_dir(
    monkeypatch,
):
    """The helper can run without explicit asset paths when standard files exist."""
    baseline = _make_sim(
        {
            "household_net_income": [100.0, 200.0],
            "household_weight": [1.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [115.0, 230.0],
            "household_weight": [1.0, 1.0],
        }
    )

    weight_matrix = [[1.0, 0.0], [0.0, 1.0]]
    csv_rows = [
        {"code": "LA001", "name": "A", "x": 0, "y": 0},
        {"code": "LA002", "name": "B", "x": 1, "y": 1},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        h5_path = os.path.join(
            tmpdir,
            LOCAL_AUTHORITY_ASSET_SPEC.weight_matrix_filename,
        )
        with h5py.File(h5_path, "w") as f:
            f.create_dataset("2025", data=np.array(weight_matrix, dtype=np.float64))

        csv_path = os.path.join(tmpdir, LOCAL_AUTHORITY_ASSET_SPEC.lookup_csv_filename)
        pd.DataFrame(csv_rows).to_csv(csv_path, index=False)

        monkeypatch.setenv("POLICYENGINE_UK_GEOGRAPHY_DATA_DIR", tmpdir)
        with patch(
            "policyengine_core.tools.google_cloud.download_gcs_file"
        ) as download:
            impact = compute_uk_local_authority_impacts(
                baseline,
                reform,
            )

        download.assert_not_called()

    assert impact.weight_matrix_path == h5_path
    assert impact.local_authority_csv_path == csv_path
    assert len(impact.local_authority_results) == 2
