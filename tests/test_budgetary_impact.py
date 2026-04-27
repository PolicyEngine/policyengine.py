"""Unit tests for federal/state budgetary impact partitioning."""

from unittest.mock import patch

from policyengine.tax_benefit_models.us.analysis import (
    BudgetaryImpact,
    calculate_budgetary_impact,
)


def _fake_sum_change_factory(variable_to_delta: dict[str, float]):
    """Return a fake _sum_change that looks up deltas by variable name."""

    def fake_sum_change(baseline_sim, reform_sim, variable):
        return variable_to_delta.get(variable, 0.0)

    return fake_sum_change


def test_federal_tax_cut_only():
    """A pure federal tax cut shows up as negative federal impact, zero state."""
    deltas = {
        "income_tax": -100e9,
        "payroll_tax": 0,
        "state_income_tax": 0,
        "federal_benefit_cost": 0,
        "state_benefit_cost": 0,
    }
    with patch(
        "policyengine.tax_benefit_models.us.analysis._sum_change",
        side_effect=_fake_sum_change_factory(deltas),
    ):
        result = calculate_budgetary_impact(None, None)

    assert isinstance(result, BudgetaryImpact)
    assert result.federal == -100e9
    assert result.state == 0
    assert result.total == -100e9


def test_medicaid_expansion_rollback_shifts_cost_to_states():
    """Repealing ACA expansion reduces federal benefit spending 10x more
    than state (90% vs 10% FMAP), which shows as a federal *gain* and
    a small state gain — sign: reduced spending = positive fiscal impact."""
    deltas = {
        "income_tax": 0,
        "payroll_tax": 0,
        "state_income_tax": 0,
        # Federal benefit spending drops by $90B, state by $10B
        "federal_benefit_cost": -90e9,
        "state_benefit_cost": -10e9,
    }
    with patch(
        "policyengine.tax_benefit_models.us.analysis._sum_change",
        side_effect=_fake_sum_change_factory(deltas),
    ):
        result = calculate_budgetary_impact(None, None)

    # Federal "impact" = -(-90B) = +90B (government saves money)
    assert result.federal == 90e9
    assert result.state == 10e9
    assert result.total == 100e9


def test_mixed_federal_and_state_tax_changes():
    """Federal income tax cut + state income tax cut partition correctly."""
    deltas = {
        "income_tax": -50e9,
        "payroll_tax": -10e9,
        "state_income_tax": -20e9,
        "federal_benefit_cost": 5e9,
        "state_benefit_cost": 2e9,
    }
    with patch(
        "policyengine.tax_benefit_models.us.analysis._sum_change",
        side_effect=_fake_sum_change_factory(deltas),
    ):
        result = calculate_budgetary_impact(None, None)

    # Federal = (-50B + -10B) - 5B = -65B
    assert result.federal == -65e9
    # State = -20B - 2B = -22B
    assert result.state == -22e9
    assert result.total == -87e9


def test_zero_reform_gives_zero_impact():
    deltas = {}  # all zero
    with patch(
        "policyengine.tax_benefit_models.us.analysis._sum_change",
        side_effect=_fake_sum_change_factory(deltas),
    ):
        result = calculate_budgetary_impact(None, None)

    assert result.federal == 0
    assert result.state == 0
    assert result.total == 0
