"""Tests for shared weighted decile grouping."""

import numpy as np
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


def test_ten_equally_weighted_households_fill_all_ten_groups():
    household = _household_frame(
        list(range(10, 110, 10)),
        [1] * 10,
        [1] * 10,
    )

    groups = calculate_decile_groups(
        household,
        household["household_net_income"],
        decile_variable=None,
        entity="household",
        quantiles=10,
    )

    assert groups.tolist() == list(range(1, 11))


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


def test_large_survey_observation_is_not_split_across_groups():
    household = _household_frame(
        [10, 20],
        [15, 85],
        [1, 1],
    )

    groups = calculate_decile_groups(
        household,
        household["household_net_income"],
        decile_variable=None,
        entity="household",
        quantiles=10,
    )

    assert groups.tolist() == [2, 10]


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


def test_non_household_groups_use_entity_survey_weight():
    person = MicroDataFrame(
        pd.DataFrame(
            {
                "person_income": [10, 20],
                "person_weight": [9, 1],
            }
        ),
        weights="person_weight",
    )

    groups = calculate_decile_groups(
        person,
        person["person_income"],
        decile_variable=None,
        entity="person",
        quantiles=10,
    )

    assert groups.tolist() == [9, 10]


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


def test_non_finite_ranking_values_do_not_affect_group_boundaries():
    household = _household_frame(
        [10, 20, np.nan, np.inf, -np.inf],
        [1, 1, 100, 100, 100],
        [1, 1, 1, 1, 1],
    )

    groups = calculate_decile_groups(
        household,
        household["household_net_income"],
        decile_variable=None,
        entity="household",
        quantiles=10,
    )

    assert groups.iloc[:2].tolist() == [5, 10]
    assert all(pd.isna(group) or group < 1 or group > 10 for group in groups.iloc[2:])


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


@pytest.mark.parametrize("invalid_weight", [-1, np.nan, np.inf, -np.inf])
def test_computed_groups_reject_invalid_survey_weights(invalid_weight):
    household = _household_frame(
        [10, 20],
        [2, invalid_weight],
        [1, 1],
    )

    with pytest.raises(ValueError):
        calculate_decile_groups(
            household,
            household["household_net_income"],
            decile_variable=None,
            entity="household",
            quantiles=10,
        )


@pytest.mark.parametrize("invalid_people_count", [-1, np.nan, np.inf, -np.inf])
def test_computed_groups_reject_invalid_people_counts(invalid_people_count):
    household = _household_frame(
        [10, 20],
        [1, 1],
        [2, invalid_people_count],
    )

    with pytest.raises(ValueError):
        calculate_decile_groups(
            household,
            household["household_net_income"],
            decile_variable=None,
            entity="household",
            quantiles=10,
        )


def test_computed_groups_reject_zero_total_effective_weight():
    household = _household_frame(
        [10, 20],
        [0, 0],
        [1, 1],
    )

    with pytest.raises((ValueError, ZeroDivisionError)):
        calculate_decile_groups(
            household,
            household["household_net_income"],
            decile_variable=None,
            entity="household",
            quantiles=10,
        )


@pytest.mark.parametrize("quantiles", [0, -1])
def test_computed_groups_require_at_least_one_group(quantiles):
    household = _household_frame(
        [10, 20],
        [1, 1],
        [1, 1],
    )

    with pytest.raises(ValueError, match="quantiles"):
        calculate_decile_groups(
            household,
            household["household_net_income"],
            decile_variable=None,
            entity="household",
            quantiles=quantiles,
        )
