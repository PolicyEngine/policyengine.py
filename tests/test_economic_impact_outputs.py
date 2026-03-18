"""Tests for the new economic impact output modules."""

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.outputs.change_aggregate import ChangeAggregate, ChangeAggregateType
from policyengine.outputs.country_config import UK_CONFIG, US_CONFIG
from policyengine.outputs.decile_impact import DecileImpact, compute_decile_impacts

# ---------------------------------------------------------------------------
# Helpers (same pattern as test_intra_decile_impact.py)
# ---------------------------------------------------------------------------


def _make_variable_mock(name: str, entity: str) -> MagicMock:
    """Create a mock Variable with name and entity attributes."""
    var = MagicMock()
    var.name = name
    var.entity = entity
    return var


def _make_sim(household_data: dict, variables: list | None = None) -> MagicMock:
    """Create a mock Simulation with household-level data."""
    hh_df = MicroDataFrame(
        pd.DataFrame(household_data),
        weights="household_weight",
    )
    sim = MagicMock()
    sim.output_dataset.data.household = hh_df
    sim.id = "test-sim"
    if variables is not None:
        sim.tax_benefit_model_version.variables = variables
    return sim


# ---------------------------------------------------------------------------
# CountryConfig tests
# ---------------------------------------------------------------------------


def test_us_config_is_frozen():
    """US_CONFIG should be immutable."""
    with pytest.raises(FrozenInstanceError):
        US_CONFIG.country_id = "uk"


def test_uk_config_is_frozen():
    """UK_CONFIG should be immutable."""
    with pytest.raises(FrozenInstanceError):
        UK_CONFIG.country_id = "us"


def test_us_config_has_correct_country_id():
    assert US_CONFIG.country_id == "us"


def test_uk_config_has_correct_country_id():
    assert UK_CONFIG.country_id == "uk"


def test_us_config_programs():
    """US_CONFIG should contain expected program keys."""
    expected = {
        "income_tax",
        "employee_payroll_tax",
        "snap",
        "tanf",
        "ssi",
        "social_security",
    }
    assert set(US_CONFIG.programs.keys()) == expected


def test_uk_config_programs():
    """UK_CONFIG should contain expected programme keys."""
    expected = {
        "income_tax",
        "national_insurance",
        "vat",
        "council_tax",
        "universal_credit",
        "child_benefit",
        "pension_credit",
        "income_support",
        "working_tax_credit",
        "child_tax_credit",
    }
    assert set(UK_CONFIG.programs.keys()) == expected


def test_country_config_program_structure():
    """Each program entry should have 'entity' and 'is_tax' keys."""
    for name, info in US_CONFIG.programs.items():
        assert "entity" in info, f"US program {name} missing 'entity'"
        assert "is_tax" in info, f"US program {name} missing 'is_tax'"
    for name, info in UK_CONFIG.programs.items():
        assert "entity" in info, f"UK programme {name} missing 'entity'"
        assert "is_tax" in info, f"UK programme {name} missing 'is_tax'"


# ---------------------------------------------------------------------------
# DecileImpact tests
# ---------------------------------------------------------------------------


def test_decile_impact_variable_not_found():
    """DecileImpact.run() should raise ValueError for a nonexistent variable."""
    variables = [_make_variable_mock("household_net_income", "household")]
    sim = _make_sim(
        {"household_net_income": [50000.0], "household_weight": [1.0]},
        variables=variables,
    )

    di = DecileImpact.model_construct(
        baseline_simulation=sim,
        reform_simulation=sim,
        income_variable="nonexistent_variable",
        entity="household",
        decile=1,
    )
    with pytest.raises(ValueError, match="not found in model"):
        di.run()


def test_compute_decile_impacts_returns_10():
    """compute_decile_impacts should return 10 DecileImpact objects by default."""
    n = 100
    incomes = np.linspace(10000, 100000, n)
    reform_incomes = incomes + 500
    variables = [_make_variable_mock("household_net_income", "household")]

    baseline = _make_sim(
        {"household_net_income": incomes, "household_weight": np.ones(n)},
        variables=variables,
    )
    reform = _make_sim(
        {"household_net_income": reform_incomes, "household_weight": np.ones(n)},
        variables=variables,
    )

    result = compute_decile_impacts(
        baseline, reform, income_variable="household_net_income", entity="household"
    )

    assert len(result.outputs) == 10
    assert len(result.dataframe) == 10

    # Each decile should have absolute_change ~500
    for di in result.outputs:
        assert abs(di.absolute_change - 500.0) < 1e-6


def test_compute_decile_impacts_custom_quantiles():
    """compute_decile_impacts with quantiles=5 should return 5 outputs."""
    n = 100
    incomes = np.linspace(10000, 100000, n)
    variables = [_make_variable_mock("household_net_income", "household")]

    sim = _make_sim(
        {"household_net_income": incomes, "household_weight": np.ones(n)},
        variables=variables,
    )

    result = compute_decile_impacts(
        sim,
        sim,
        income_variable="household_net_income",
        entity="household",
        quantiles=5,
    )

    assert len(result.outputs) == 5


# ---------------------------------------------------------------------------
# ChangeAggregate error test
# ---------------------------------------------------------------------------


def test_change_aggregate_variable_not_found():
    """ChangeAggregate should raise ValueError for a nonexistent variable."""
    variables = [_make_variable_mock("employment_income", "person")]
    sim = _make_sim(
        {"household_net_income": [50000.0], "household_weight": [1.0]},
        variables=variables,
    )

    ca = ChangeAggregate.model_construct(
        baseline_simulation=sim,
        reform_simulation=sim,
        variable="nonexistent_variable",
        aggregate_type=ChangeAggregateType.COUNT,
    )
    with pytest.raises(ValueError, match="not found in model"):
        ca.run()
