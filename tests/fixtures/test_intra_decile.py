"""Fixtures for intra_decile_impact and intra_wealth_decile_impact tests."""

import numpy as np
from unittest.mock import MagicMock


# Standard decile assignment: one household per decile (1-10)
DECILES_1_TO_10 = list(range(1, 11))
NUM_DECILES = 10


def make_single_economy(
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


def make_uniform_pair(
    baseline_income,
    reform_income,
    decile_attr="household_income_decile",
):
    """Build a baseline/reform pair where every household has the same
    income, one per decile."""
    baseline = make_single_economy(
        incomes=[baseline_income] * NUM_DECILES,
        deciles=DECILES_1_TO_10,
        decile_attr=decile_attr,
    )
    reform = make_single_economy(
        incomes=[reform_income] * NUM_DECILES,
        deciles=DECILES_1_TO_10,
        decile_attr=decile_attr,
    )
    return baseline, reform
