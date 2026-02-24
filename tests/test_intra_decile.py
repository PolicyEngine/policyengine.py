"""Regression tests for intra_decile_impact and intra_wealth_decile_impact.

These tests verify the fix for the double-counting bug where
capped_reform_income was computed as max(reform, 1) + absolute_change,
effectively doubling the percentage income change.
"""

import pytest
import numpy as np

from policyengine.outputs.macro.comparison.calculate_economy_comparison import (
    _compute_income_change,
    intra_decile_impact,
    intra_wealth_decile_impact,
)
from tests.fixtures.test_intra_decile import (
    make_single_economy,
    make_uniform_pair,
)


class TestComputeIncomeChange:
    """Direct unit tests for the income change formula."""

    def test__given_4pct_gain__returns_0_04(self):
        result = _compute_income_change(
            np.array([1000.0]), np.array([1040.0])
        )
        assert result[0] == pytest.approx(0.04)


class TestIntraDecileImpact:
    """Tests for intra_decile_impact — verifying correct percentage
    change calculation and bucket assignment."""

    def test__given_5pct_gain__classifies_as_below_5pct(self):
        """A uniform 5% income gain must NOT land in 'Gain more than 5%'.

        This is the key regression test for the double-counting bug where
        income_change was 2x the true value, pushing 5% gains into the
        >5% bucket.
        """
        baseline, reform = make_uniform_pair(1000.0, 1050.0)
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 0.0, f"5% gain incorrectly classified as >5% (got {pct})"
        for pct in result.deciles["Gain less than 5%"]:
            assert pct == 1.0, f"5% gain not classified as <5% (got {pct})"

    def test__given_10pct_gain__classifies_as_above_5pct(self):
        baseline, reform = make_uniform_pair(1000.0, 1100.0)
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 1.0

    def test__given_3pct_loss__classifies_as_below_5pct_loss(self):
        baseline, reform = make_uniform_pair(1000.0, 970.0)
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Lose less than 5%"]:
            assert pct == 1.0
        for pct in result.deciles["Lose more than 5%"]:
            assert pct == 0.0

    def test__given_no_change__classifies_as_no_change(self):
        baseline, reform = make_uniform_pair(1000.0, 1000.0)
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["No change"]:
            assert pct == 1.0

    def test__given_zero_baseline__proportions_sum_to_one(self):
        baseline, reform = make_uniform_pair(0.0, 100.0)
        result = intra_decile_impact(baseline, reform)

        total = sum(result.all[label] for label in result.all)
        assert abs(total - 1.0) < 1e-9, f"Proportions should sum to 1, got {total}"

    def test__given_zero_baseline__classifies_gain_as_above_5pct(self):
        """When baseline income is 0, the max(B, 1) floor means the
        effective denominator is 1. A $0 -> $100 change gives
        income_change = 100/1 = 10000%, landing in >5%."""
        baseline, reform = make_uniform_pair(0.0, 100.0)
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 1.0, f"Zero baseline with $100 gain should be >5% (got {pct})"
        for label in result.all:
            assert not np.isnan(result.all[label])
            assert not np.isinf(result.all[label])

    def test__given_negative_baseline__produces_no_nan_or_inf(self):
        baseline, reform = make_uniform_pair(-500.0, 500.0)
        result = intra_decile_impact(baseline, reform)

        for label in result.all:
            assert not np.isnan(result.all[label])
            assert not np.isinf(result.all[label])

    def test__given_4pct_gain__does_not_double_into_above_5pct(self):
        """A 4% gain must stay in <5%. With the doubling bug, 4% * 2 = 8%
        would incorrectly land in >5%."""
        baseline, reform = make_uniform_pair(10000.0, 10400.0)
        result = intra_decile_impact(baseline, reform)

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 0.0, "4% gain incorrectly classified as >5% (doubling bug)"
        for pct in result.deciles["Gain less than 5%"]:
            assert pct == 1.0, "4% gain not classified as <5%"

    def test__given_uniform_gain__all_field_averages_deciles(self):
        baseline, reform = make_uniform_pair(1000.0, 1050.0)
        result = intra_decile_impact(baseline, reform)

        for label in result.all:
            expected = sum(result.deciles[label]) / 10
            assert abs(result.all[label] - expected) < 1e-9


class TestIntraWealthDecileImpact:
    """Tests for intra_wealth_decile_impact — same formula, keyed by
    wealth decile instead of income decile."""

    def test__given_5pct_gain__classifies_as_below_5pct(self):
        baseline, reform = make_uniform_pair(
            1000.0, 1050.0, decile_attr="household_wealth_decile"
        )
        result = intra_wealth_decile_impact(baseline, reform, "uk")

        for pct in result.deciles["Gain more than 5%"]:
            assert (
                pct == 0.0
            ), f"5% gain incorrectly classified as >5% in wealth decile (got {pct})"

    def test__given_4pct_gain__does_not_double_into_above_5pct(self):
        baseline, reform = make_uniform_pair(
            10000.0, 10400.0, decile_attr="household_wealth_decile"
        )
        result = intra_wealth_decile_impact(baseline, reform, "uk")

        for pct in result.deciles["Gain more than 5%"]:
            assert pct == 0.0, "4% gain incorrectly classified as >5%"
        for pct in result.deciles["Gain less than 5%"]:
            assert pct == 1.0, "4% gain not classified as <5%"
