"""Unit tests for CongressionalDistrictImpact output class."""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
from microdf import MicroDataFrame

from policyengine.outputs.congressional_district_impact import (
    CongressionalDistrictImpact,
    compute_us_congressional_district_impacts,
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


def test_basic_district_grouping():
    """Two districts with known incomes produce correct per-district metrics."""
    baseline = _make_sim(
        {
            "congressional_district_geoid": [101, 101, 202],
            "household_net_income": [50000.0, 60000.0, 40000.0],
            "household_weight": [1.0, 1.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "congressional_district_geoid": [101, 101, 202],
            "household_net_income": [52000.0, 62000.0, 42000.0],
            "household_weight": [1.0, 1.0, 1.0],
        }
    )

    impact = compute_us_congressional_district_impacts(baseline, reform)

    assert impact.district_results is not None
    assert len(impact.district_results) == 2

    by_geoid = {r["district_geoid"]: r for r in impact.district_results}

    # District 101: baseline avg = 55000, reform avg = 57000, change = 2000
    d101 = by_geoid[101]
    assert d101["state_fips"] == 1
    assert d101["district_number"] == 1
    assert abs(d101["average_household_income_change"] - 2000.0) < 1e-6
    assert d101["population"] == 2.0

    # District 202: baseline = 40000, reform = 42000, change = 2000
    d202 = by_geoid[202]
    assert d202["state_fips"] == 2
    assert d202["district_number"] == 2
    assert abs(d202["average_household_income_change"] - 2000.0) < 1e-6


def test_negative_geoid_excluded():
    """Households with geoid <= 0 are excluded from results."""
    baseline = _make_sim(
        {
            "congressional_district_geoid": [-1, 0, 101],
            "household_net_income": [50000.0, 50000.0, 50000.0],
            "household_weight": [1.0, 1.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "congressional_district_geoid": [-1, 0, 101],
            "household_net_income": [55000.0, 55000.0, 55000.0],
            "household_weight": [1.0, 1.0, 1.0],
        }
    )

    impact = compute_us_congressional_district_impacts(baseline, reform)

    assert len(impact.district_results) == 1
    assert impact.district_results[0]["district_geoid"] == 101


def test_zero_weight_district_skipped():
    """Districts where all households have zero weight produce no result."""
    baseline = _make_sim(
        {
            "congressional_district_geoid": [101, 202],
            "household_net_income": [50000.0, 50000.0],
            "household_weight": [1.0, 0.0],
        }
    )
    reform = _make_sim(
        {
            "congressional_district_geoid": [101, 202],
            "household_net_income": [55000.0, 55000.0],
            "household_weight": [1.0, 0.0],
        }
    )

    impact = compute_us_congressional_district_impacts(baseline, reform)

    assert len(impact.district_results) == 1
    assert impact.district_results[0]["district_geoid"] == 101


def test_weighted_average_change():
    """Weighted average income change is computed correctly."""
    baseline = _make_sim(
        {
            "congressional_district_geoid": [101, 101],
            "household_net_income": [40000.0, 80000.0],
            "household_weight": [3.0, 1.0],
        }
    )
    reform = _make_sim(
        {
            "congressional_district_geoid": [101, 101],
            "household_net_income": [42000.0, 82000.0],
            "household_weight": [3.0, 1.0],
        }
    )

    impact = compute_us_congressional_district_impacts(baseline, reform)

    d = impact.district_results[0]
    # Weighted avg change: (3*2000 + 1*2000) / 4 = 2000
    assert abs(d["average_household_income_change"] - 2000.0) < 1e-6
    assert d["population"] == 4.0
