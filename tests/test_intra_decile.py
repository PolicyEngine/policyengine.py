"""Regression tests for intra_decile_impact and intra_wealth_decile_impact.

These tests verify the fix for the double-counting bug where
capped_reform_income was computed as max(reform, 1) + absolute_change,
effectively doubling the percentage income change.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

from policyengine.outputs.macro.comparison.calculate_economy_comparison import (
    compute_income_change,
    intra_decile_impact,
    intra_wealth_decile_impact,
)


def _make_single_economy(
    incomes,
    deciles,
    weights=None,
    people=None,
    decile_attr="household_income_decile",
):
    """Build a mock SingleEconomy with the fields needed by
    intra_decile_impact / intra_wealth_decile_impact."""
    n = len(incomes)
    economy = MagicMock()
    economy.household_net_income = np.array(incomes, dtype=float)
    economy.household_weight = np.array(
        weights if weights else [1.0] * n, dtype=float
    )
    economy.household_count_people = np.array(
        people if people else [1.0] * n, dtype=float
    )
    setattr(economy, decile_attr, np.array(deciles, dtype=float))
    return economy


class TestComputeIncomeChange:
    """Direct unit tests for the income change formula."""

    def test__income_change_formula_exact(self):
        result = compute_income_change(np.array([1000.0]), np.array([1040.0]))
        assert result[0] == pytest.approx(0.04)


class TestIntraDecileImpact:
    """Tests for intra_decile_impact — verifying correct percentage
    change calculation and bucket assignment."""

    def test__5pct_gain_classified_below_5pct(self):
        """A uniform 5% income gain must NOT land in 'Gain more than 5%'.

        This is the key regression test for the double-counting bug where
        income_change was 2x the true value, pushing 5% gains into the
        >5% bucket.
        """
        baseline = _make_single_economy(
            incomes=[1000.0] * 10,
            deciles=list(range(1, 11)),
        )
        reform = _make_single_economy(
            incomes=[1050.0] * 10,
            deciles=list(range(1, 11)),
        )
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 0.0, f"5% gain incorrectly classified as >5% (got {pct})"
        for pct in result.deciles["Gain less than 5%"]:
            assert pct == 1.0, f"5% gain not classified as <5% (got {pct})"

    def test__10pct_gain_classified_above_5pct(self):
        """A 10% gain should be in 'Gain more than 5%'."""
        baseline = _make_single_economy(
            incomes=[1000.0] * 10,
            deciles=list(range(1, 11)),
        )
        reform = _make_single_economy(
            incomes=[1100.0] * 10,
            deciles=list(range(1, 11)),
        )
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 1.0

    def test__3pct_loss_classified_below_5pct(self):
        """A 3% loss should be in 'Lose less than 5%'."""
        baseline = _make_single_economy(
            incomes=[1000.0] * 10,
            deciles=list(range(1, 11)),
        )
        reform = _make_single_economy(
            incomes=[970.0] * 10,
            deciles=list(range(1, 11)),
        )
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Lose less than 5%"]:
            assert pct == 1.0
        for pct in result.deciles["Lose more than 5%"]:
            assert pct == 0.0

    def test__no_change_classified_correctly(self):
        """Zero change should land in 'No change'."""
        baseline = _make_single_economy(
            incomes=[1000.0] * 10,
            deciles=list(range(1, 11)),
        )
        reform = _make_single_economy(
            incomes=[1000.0] * 10,
            deciles=list(range(1, 11)),
        )
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["No change"]:
            assert pct == 1.0

    def test__near_zero_baseline_no_division_error(self):
        """Households with near-zero baseline income should not cause
        division errors — the floor of 1 handles this."""
        baseline = _make_single_economy(
            incomes=[0.0] * 10,
            deciles=list(range(1, 11)),
        )
        reform = _make_single_economy(
            incomes=[100.0] * 10,
            deciles=list(range(1, 11)),
        )
        result = intra_decile_impact(baseline, reform)

        total = sum(result.all[label] for label in result.all)
        assert abs(total - 1.0) < 1e-9, f"Proportions should sum to 1, got {total}"

    def test__zero_baseline_uses_floor_of_one(self):
        """When baseline income is 0, the max(B, 1) floor means the
        effective denominator is 1. A $0 -> $100 change should give
        income_change = 100/1 = 100 (10000%), landing in >5%."""
        baseline = _make_single_economy(
            incomes=[0.0] * 10,
            deciles=list(range(1, 11)),
        )
        reform = _make_single_economy(
            incomes=[100.0] * 10,
            deciles=list(range(1, 11)),
        )
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 1.0, f"Zero baseline with $100 gain should be >5% (got {pct})"
        for label in result.all:
            assert not np.isnan(result.all[label])
            assert not np.isinf(result.all[label])

    def test__negative_baseline_handled(self):
        """Households with negative baseline income should be handled
        by the max(B, 1) floor without producing NaN or Inf."""
        baseline = _make_single_economy(
            incomes=[-500.0] * 10,
            deciles=list(range(1, 11)),
        )
        reform = _make_single_economy(
            incomes=[500.0] * 10,
            deciles=list(range(1, 11)),
        )
        result = intra_decile_impact(baseline, reform)

        for label in result.all:
            assert not np.isnan(result.all[label])
            assert not np.isinf(result.all[label])

    def test__4pct_gain_not_doubled_into_above_5pct(self):
        """A 4% gain must stay in <5%. With the doubling bug, 4% * 2 = 8%
        would incorrectly land in >5%. This is the tightest regression
        test for the doubling bug on the gain side."""
        baseline = _make_single_economy(
            incomes=[10000.0] * 10,
            deciles=list(range(1, 11)),
        )
        reform = _make_single_economy(
            incomes=[10400.0] * 10,
            deciles=list(range(1, 11)),
        )
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 0.0, "4% gain incorrectly classified as >5% (doubling bug)"
        for pct in result.deciles["Gain less than 5%"]:
            assert pct == 1.0, "4% gain not classified as <5%"

    def test__all_field_averages_deciles(self):
        """The 'all' field should be the mean of the 10 decile values."""
        baseline = _make_single_economy(
            incomes=[1000.0] * 10,
            deciles=list(range(1, 11)),
        )
        reform = _make_single_economy(
            incomes=[1050.0] * 10,
            deciles=list(range(1, 11)),
        )
        result = intra_decile_impact(baseline, reform)

        for label in result.all:
            expected = sum(result.deciles[label]) / 10
            assert abs(result.all[label] - expected) < 1e-9


class TestIntraWealthDecileImpact:
    """Tests for intra_wealth_decile_impact — same formula, keyed by
    wealth decile instead of income decile."""

    def test__5pct_gain_classified_below_5pct(self):
        """Regression test: 5% gain must not be doubled into >5% bucket."""
        baseline = _make_single_economy(
            incomes=[1000.0] * 10,
            deciles=list(range(1, 11)),
            decile_attr="household_wealth_decile",
        )
        reform = _make_single_economy(
            incomes=[1050.0] * 10,
            deciles=list(range(1, 11)),
            decile_attr="household_wealth_decile",
        )

        result = intra_wealth_decile_impact(baseline, reform, "uk")

        for pct in result.deciles["Gain more than 5%"]:
            assert (
                pct == 0.0
            ), f"5% gain incorrectly classified as >5% in wealth decile (got {pct})"

    def test__4pct_gain_not_doubled(self):
        """A 4% gain must stay in the <5% bucket for wealth deciles too."""
        baseline = _make_single_economy(
            incomes=[10000.0] * 10,
            deciles=list(range(1, 11)),
            decile_attr="household_wealth_decile",
        )
        reform = _make_single_economy(
            incomes=[10400.0] * 10,
            deciles=list(range(1, 11)),
            decile_attr="household_wealth_decile",
        )

        result = intra_wealth_decile_impact(baseline, reform, "uk")

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 0.0, "4% gain incorrectly classified as >5%"
        for pct in result.deciles["Gain less than 5%"]:
            assert pct == 1.0, "4% gain not classified as <5%"
