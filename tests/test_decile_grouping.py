"""Tests for shared weighted decile grouping."""

import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.outputs.decile_grouping import calculate_decile_groups


def _household_frame(
    incomes,
    household_weights,
    people_counts=None,
    *,
    index=None,
) -> MicroDataFrame:
    data = {
        "household_net_income": incomes,
        "household_weight": household_weights,
    }
    if people_counts is not None:
        data["household_count_people"] = people_counts
    return MicroDataFrame(
        pd.DataFrame(data, index=index),
        weights="household_weight",
    )


def test_household_groups_multiply_survey_weights_by_household_size():
    household = _household_frame(
        [10, 20, 30, 40],
        [2, 1, 1, 1],
        [2, 1, 1, 1],
        index=[100, 200, 300, 400],
    )

    groups = calculate_decile_groups(
        household,
        household["household_net_income"],
        decile_variable=None,
        entity="household",
        quantiles=10,
    )

    assert groups.index.tolist() == [100, 200, 300, 400]
    assert groups.tolist() == [6, 8, 9, 10]


def test_household_groups_keep_tied_incomes_together():
    household = _household_frame(
        [10, 10, 20],
        [1, 1, 1],
        [1, 2, 1],
    )

    groups = calculate_decile_groups(
        household,
        household["household_net_income"],
        decile_variable=None,
        entity="household",
        quantiles=10,
    )

    assert groups.tolist() == [8, 8, 10]


def test_computed_groups_clamp_zero_weight_rows_to_first_group():
    household = _household_frame(
        [10, 20, 30],
        [0, 1, 1],
        [1, 1, 1],
    )

    groups = calculate_decile_groups(
        household,
        household["household_net_income"],
        decile_variable=None,
        entity="household",
        quantiles=10,
    )

    assert groups.tolist() == [1, 5, 10]


def test_computed_groups_exclude_negative_ranking_values():
    household = _household_frame(
        [-10, 20, 30],
        [1, 1, 1],
        [1, 1, 1],
    )

    groups = calculate_decile_groups(
        household,
        household["household_net_income"],
        decile_variable=None,
        entity="household",
        quantiles=10,
    )

    assert groups.tolist() == [-1, 7, 10]


def test_precomputed_groups_bypass_weighted_ranking_requirements():
    household = _household_frame(
        [10, 20],
        [1, 1],
    )
    household["household_wealth_decile"] = [2, 1]

    groups = calculate_decile_groups(
        household,
        household["household_net_income"],
        decile_variable="household_wealth_decile",
        entity="household",
        quantiles=10,
    )

    assert groups.tolist() == [2, 1]


def test_precomputed_groups_preserve_exclusion_sentinel():
    household = _household_frame(
        [10, 20],
        [1, 1],
    )
    household["household_income_decile"] = [-1, 2]

    groups = calculate_decile_groups(
        household,
        household["household_net_income"],
        decile_variable="household_income_decile",
        entity="household",
        quantiles=10,
    )

    assert groups.tolist() == [-1, 2]


def test_computed_household_groups_require_people_counts():
    household = _household_frame(
        [10, 20],
        [1, 1],
    )

    with pytest.raises(ValueError, match="household_count_people"):
        calculate_decile_groups(
            household,
            household["household_net_income"],
            decile_variable=None,
            entity="household",
            quantiles=10,
        )
