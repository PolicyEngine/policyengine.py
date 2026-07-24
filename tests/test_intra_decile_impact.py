"""Unit tests for DecileImpact and IntraDecileImpact."""

from typing import Optional
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

from policyengine.core import Simulation, TaxBenefitModel, TaxBenefitModelVersion
from policyengine.core.variable import Variable
from policyengine.outputs.decile_impact import (
    DecileImpact,
    calculate_decile_impacts,
)
from policyengine.outputs.intra_decile_impact import (
    compute_intra_decile_impacts,
)


def _make_variable_mock(name: str, entity: str) -> MagicMock:
    """Create a mock Variable with name and entity attributes."""
    var = MagicMock()
    var.name = name
    var.entity = entity
    return var


def _make_version(variable_name: str, entity: str) -> TaxBenefitModelVersion:
    """Create a minimal TaxBenefitModelVersion with one variable."""
    model = TaxBenefitModel(id="test-model")
    version = TaxBenefitModelVersion(model=model, version="test-version")
    variable = Variable(
        id=f"test-model-{variable_name}",
        name=variable_name,
        tax_benefit_model_version=version,
        entity=entity,
    )
    version.variables = [variable]
    version.variables_by_name = {variable_name: variable}
    return version


def _make_sim(
    household_data: dict,
    variables: Optional[list] = None,
    *,
    index=None,
) -> MagicMock:
    """Create a mock Simulation with household-level data."""
    hh_df = MicroDataFrame(
        pd.DataFrame(household_data, index=index),
        weights="household_weight",
    )
    sim = MagicMock()
    sim.output_dataset.data.household = hh_df
    sim.id = "test-sim"
    if variables is not None:
        sim.tax_benefit_model_version.variables = variables
    return sim


# ---------------------------------------------------------------------------
# IntraDecileImpact tests
# ---------------------------------------------------------------------------


def test_intra_decile_no_change():
    """When baseline == reform, all households fall in no_change category."""
    n = 100
    incomes = np.linspace(10000, 100000, n)
    baseline = _make_sim(
        {
            "household_net_income": incomes,
            "household_weight": np.ones(n),
            "household_count_people": np.full(n, 2.0),
        }
    )
    reform = _make_sim(
        {
            "household_net_income": incomes,
            "household_weight": np.ones(n),
            "household_count_people": np.full(n, 2.0),
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        entity="household",
    )

    # 11 rows: deciles 1-10 + overall (decile=0)
    assert len(results.outputs) == 11

    for r in results.outputs:
        assert r.no_change == 1.0 or abs(r.no_change - 1.0) < 1e-9
        assert r.lose_more_than_5pct == 0.0 or abs(r.lose_more_than_5pct) < 1e-9
        assert r.gain_more_than_5pct == 0.0 or abs(r.gain_more_than_5pct) < 1e-9


def test_intra_decile_all_large_gain():
    """When everyone gains >5%, all fall in gain_more_than_5pct category."""
    n = 100
    incomes = np.linspace(10000, 100000, n)
    reform_incomes = incomes * 1.10  # 10% gain
    baseline = _make_sim(
        {
            "household_net_income": incomes,
            "household_weight": np.ones(n),
            "household_count_people": np.ones(n),
        }
    )
    reform = _make_sim(
        {
            "household_net_income": reform_incomes,
            "household_weight": np.ones(n),
            "household_count_people": np.ones(n),
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        entity="household",
    )

    for r in results.outputs:
        assert r.gain_more_than_5pct == 1.0 or abs(r.gain_more_than_5pct - 1.0) < 1e-9
        assert r.no_change == 0.0 or abs(r.no_change) < 1e-9


def test_intra_decile_overall_uses_included_population_weights():
    """Overall proportions are calculated directly, not averaged by decile."""
    baseline = _make_sim(
        {
            "household_net_income": [100.0, 100.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 9.0],
            "household_income_decile": [1, 2],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [110.0, 100.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 9.0],
            "household_income_decile": [1, 2],
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        quantiles=2,
    )

    overall = next(r for r in results.outputs if r.decile == 0)

    assert overall.gain_more_than_5pct == pytest.approx(0.1)
    assert overall.no_change == pytest.approx(0.9)
    assert overall.lose_more_than_5pct == pytest.approx(0.0)


def test_intra_decile_category_boundaries_are_inclusive_on_the_upper_bound():
    baseline = _make_sim(
        {
            "household_net_income": [1000.0] * 5,
            "household_weight": [1.0] * 5,
            "household_count_people": [1.0] * 5,
            "household_income_decile": [1] * 5,
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [950.0, 999.0, 1001.0, 1050.0, 1060.0],
            "household_weight": [1.0] * 5,
            "household_count_people": [1.0] * 5,
            "household_income_decile": [1] * 5,
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        quantiles=1,
    )

    group = next(result for result in results.outputs if result.decile == 1)
    assert group.lose_more_than_5pct == pytest.approx(0.2)
    assert group.lose_less_than_5pct == pytest.approx(0.2)
    assert group.no_change == pytest.approx(0.2)
    assert group.gain_less_than_5pct == pytest.approx(0.2)
    assert group.gain_more_than_5pct == pytest.approx(0.2)


def test_intra_decile_uses_person_weights_within_each_group():
    baseline = _make_sim(
        {
            "household_net_income": [100.0, 100.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 9.0],
            "household_income_decile": [1, 1],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [110.0, 100.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 9.0],
            "household_income_decile": [1, 1],
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        quantiles=1,
    )

    group = next(result for result in results.outputs if result.decile == 1)
    assert group.gain_more_than_5pct == pytest.approx(0.1)
    assert group.no_change == pytest.approx(0.9)
    assert sum(
        [
            group.lose_more_than_5pct,
            group.lose_less_than_5pct,
            group.no_change,
            group.gain_less_than_5pct,
            group.gain_more_than_5pct,
        ]
    ) == pytest.approx(1.0)


def test_intra_decile_percentage_change_floors_baseline_income_at_one():
    baseline = _make_sim(
        {
            "household_net_income": [0.0, -10.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_wealth_decile": [1, 1],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [0.04, -9.96],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_wealth_decile": [1, 1],
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_wealth_decile",
        entity="household",
        quantiles=1,
    )

    group = next(result for result in results.outputs if result.decile == 1)
    assert group.gain_less_than_5pct == pytest.approx(1.0)


def test_intra_decile_empty_groups_are_null():
    baseline = _make_sim(
        {
            "household_net_income": [100.0],
            "household_weight": [1.0],
            "household_count_people": [1.0],
            "household_income_decile": [1],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [100.0],
            "household_weight": [1.0],
            "household_count_people": [1.0],
            "household_income_decile": [1],
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        quantiles=2,
    )

    empty_group = next(result for result in results.outputs if result.decile == 2)
    assert empty_group.lose_more_than_5pct is None
    assert empty_group.lose_less_than_5pct is None
    assert empty_group.no_change is None
    assert empty_group.gain_less_than_5pct is None
    assert empty_group.gain_more_than_5pct is None


def test_intra_decile_overall_excludes_invalid_precomputed_groups():
    baseline = _make_sim(
        {
            "household_net_income": [100.0, 100.0, 100.0, 100.0],
            "household_weight": [1.0, 99.0, 99.0, 99.0],
            "household_count_people": [1.0, 1.0, 1.0, 1.0],
            "household_income_decile": [1, -1, 0, 2],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [110.0, 0.0, 0.0, 0.0],
            "household_weight": [1.0, 99.0, 99.0, 99.0],
            "household_count_people": [1.0, 1.0, 1.0, 1.0],
            "household_income_decile": [1, -1, 0, 2],
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        quantiles=1,
    )

    overall = next(result for result in results.outputs if result.decile == 0)
    assert overall.gain_more_than_5pct == pytest.approx(1.0)
    assert overall.lose_more_than_5pct == pytest.approx(0.0)


def test_intra_decile_overall_is_null_without_included_positive_weight():
    baseline = _make_sim(
        {
            "household_net_income": [100.0, 200.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [-1, 3],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [110.0, 220.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [-1, 3],
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        quantiles=2,
    )

    overall = next(result for result in results.outputs if result.decile == 0)
    assert overall.lose_more_than_5pct is None
    assert overall.lose_less_than_5pct is None
    assert overall.no_change is None
    assert overall.gain_less_than_5pct is None
    assert overall.gain_more_than_5pct is None


def test_intra_decile_rejects_missing_reform_income_for_included_household():
    baseline = _make_sim(
        {
            "household_net_income": [100.0, 200.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [110.0, np.nan],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        }
    )

    with pytest.raises(ValueError):
        compute_intra_decile_impacts(
            baseline_simulation=baseline,
            reform_simulation=reform,
            income_variable="household_net_income",
            decile_variable="household_income_decile",
            entity="household",
            quantiles=1,
        )


def test_intra_decile_allows_missing_reform_income_for_excluded_household():
    baseline = _make_sim(
        {
            "household_net_income": [100.0, 200.0],
            "household_weight": [1.0, 100.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, -1],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [110.0, np.nan],
            "household_weight": [1.0, 100.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, -1],
        }
    )

    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        quantiles=1,
    )

    overall = next(result for result in results.outputs if result.decile == 0)
    assert overall.gain_more_than_5pct == pytest.approx(1.0)


def test_intra_decile_rejects_misaligned_simulation_observations():
    baseline = _make_sim(
        {
            "household_net_income": [100.0, 200.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        },
        index=["a", "b"],
    )
    reform = _make_sim(
        {
            "household_net_income": [110.0, 220.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        },
        index=["a", "c"],
    )

    with pytest.raises(ValueError):
        compute_intra_decile_impacts(
            baseline_simulation=baseline,
            reform_simulation=reform,
            income_variable="household_net_income",
            decile_variable="household_income_decile",
            entity="household",
            quantiles=1,
        )


def test_intra_decile_with_decile_variable():
    """Using a pre-computed decile_variable groups by that variable."""
    baseline = _make_sim(
        {
            "household_net_income": [50000.0, 60000.0, 70000.0, 80000.0],
            "household_weight": [1.0, 1.0, 1.0, 1.0],
            "household_count_people": [2.0, 2.0, 2.0, 2.0],
            "household_wealth_decile": [1, 1, 2, 2],
        }
    )
    reform = _make_sim(
        {
            "household_net_income": [55000.0, 66000.0, 77000.0, 88000.0],
            "household_weight": [1.0, 1.0, 1.0, 1.0],
            "household_count_people": [2.0, 2.0, 2.0, 2.0],
            "household_wealth_decile": [1, 1, 2, 2],
        }
    )

    # Only 2 deciles present, so use quantiles=2
    results = compute_intra_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_wealth_decile",
        entity="household",
        quantiles=2,
    )

    # 3 rows: decile 1, decile 2, overall (decile=0)
    assert len(results.outputs) == 3

    decile_1 = next(r for r in results.outputs if r.decile == 1)
    decile_2 = next(r for r in results.outputs if r.decile == 2)

    # All gains are 10% → all in gain_more_than_5pct
    assert (
        decile_1.gain_more_than_5pct == 1.0
        or abs(decile_1.gain_more_than_5pct - 1.0) < 1e-9
    )
    assert (
        decile_2.gain_more_than_5pct == 1.0
        or abs(decile_2.gain_more_than_5pct - 1.0) < 1e-9
    )
    assert results.dataframe["decile"].tolist() == [1, 2, 0]
    assert (
        results.dataframe.loc[
            results.dataframe["decile"] == 1, "gain_more_than_5pct"
        ].iloc[0]
        == 1.0
    )


# ---------------------------------------------------------------------------
# DecileImpact with decile_variable tests
# ---------------------------------------------------------------------------


def test_decile_impact_with_decile_variable():
    """DecileImpact uses pre-computed grouping when decile_variable is set."""
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [40000.0, 60000.0, 80000.0, 100000.0],
            "household_weight": [1.0, 1.0, 1.0, 1.0],
            "household_wealth_decile": [1, 1, 2, 2],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [42000.0, 62000.0, 82000.0, 102000.0],
            "household_weight": [1.0, 1.0, 1.0, 1.0],
            "household_wealth_decile": [1, 1, 2, 2],
        },
        variables=variables,
    )

    di = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_wealth_decile",
        entity="household",
        decile=1,
    )
    di.run()

    # Decile 1: households with income 40k, 60k → baseline mean = 50k
    assert abs(di.baseline_mean - 50000.0) < 1e-6
    assert abs(di.reform_mean - 52000.0) < 1e-6
    assert abs(di.absolute_change - 2000.0) < 1e-6


def test_decile_impact_uses_household_weights_after_person_weighted_grouping():
    """Group statistics describe households, not people in those households."""
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [10.0, 30.0],
            "household_weight": [1.0, 3.0],
            "household_count_people": [100.0, 1.0],
            "household_income_decile": [1, 1],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [20.0, 50.0],
            "household_weight": [1.0, 3.0],
            "household_count_people": [100.0, 1.0],
            "household_income_decile": [1, 1],
        },
        variables=variables,
    )

    impact = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        decile=1,
        quantiles=1,
    )
    impact.run()

    assert impact.baseline_mean == pytest.approx(25.0)
    assert impact.reform_mean == pytest.approx(42.5)
    assert impact.absolute_change == pytest.approx(17.5)
    assert impact.relative_change == pytest.approx(70.0)
    assert impact.count_better_off == pytest.approx(4.0)
    assert impact.count_worse_off == pytest.approx(0.0)
    assert impact.count_no_change == pytest.approx(0.0)


def test_decile_impact_counts_better_worse_and_no_change_separately():
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [10.0, 20.0, 30.0],
            "household_weight": [2.0, 3.0, 5.0],
            "household_count_people": [1.0, 1.0, 1.0],
            "household_income_decile": [1, 1, 1],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [11.0, 19.0, 30.0],
            "household_weight": [2.0, 3.0, 5.0],
            "household_count_people": [1.0, 1.0, 1.0],
            "household_income_decile": [1, 1, 1],
        },
        variables=variables,
    )

    impact = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        decile=1,
        quantiles=1,
    )
    impact.run()

    assert impact.count_better_off == pytest.approx(2.0)
    assert impact.count_worse_off == pytest.approx(3.0)
    assert impact.count_no_change == pytest.approx(5.0)


def test_decile_impact_relative_change_is_null_for_zero_group_baseline():
    """Negative measured income remains included in a valid wealth group."""
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [-10.0, 10.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_wealth_decile": [1, 1],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [-5.0, 15.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_wealth_decile": [1, 1],
        },
        variables=variables,
    )

    impact = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_wealth_decile",
        entity="household",
        decile=1,
        quantiles=1,
    )
    impact.run()

    assert impact.baseline_mean == pytest.approx(0.0)
    assert impact.reform_mean == pytest.approx(5.0)
    assert impact.absolute_change == pytest.approx(5.0)
    assert impact.relative_change is None
    assert impact.count_better_off == pytest.approx(2.0)


def test_decile_impact_empty_group_has_null_statistics_and_zero_counts():
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [100.0],
            "household_weight": [1.0],
            "household_count_people": [1.0],
            "household_income_decile": [1],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [110.0],
            "household_weight": [1.0],
            "household_count_people": [1.0],
            "household_income_decile": [1],
        },
        variables=variables,
    )

    impact = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        decile=2,
        quantiles=2,
    )
    impact.run()

    assert impact.baseline_mean is None
    assert impact.reform_mean is None
    assert impact.absolute_change is None
    assert impact.relative_change is None
    assert impact.count_better_off == pytest.approx(0.0)
    assert impact.count_worse_off == pytest.approx(0.0)
    assert impact.count_no_change == pytest.approx(0.0)


def test_decile_impact_zero_weight_household_does_not_affect_results():
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [10.0, 1000.0],
            "household_weight": [1.0, 0.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [20.0, 0.0],
            "household_weight": [1.0, 0.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        },
        variables=variables,
    )

    impact = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        decile=1,
        quantiles=1,
    )
    impact.run()

    assert impact.baseline_mean == pytest.approx(10.0)
    assert impact.reform_mean == pytest.approx(20.0)
    assert impact.absolute_change == pytest.approx(10.0)
    assert impact.relative_change == pytest.approx(100.0)
    assert impact.count_better_off == pytest.approx(1.0)
    assert impact.count_worse_off == pytest.approx(0.0)


def test_decile_impact_uses_baseline_group_membership():
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [10.0, 20.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [1000.0, -1000.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
        },
        variables=variables,
    )

    impact = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        entity="household",
        decile=1,
        quantiles=2,
    )
    impact.run()

    assert impact.baseline_mean == pytest.approx(10.0)
    assert impact.reform_mean == pytest.approx(1000.0)


def test_decile_impact_excludes_invalid_precomputed_groups():
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [10.0, 20.0, 1000.0, 1000.0, 1000.0, 1000.0],
            "household_weight": [1.0] * 6,
            "household_count_people": [1.0] * 6,
            "household_income_decile": [1, 2, -1, 0, 3, np.nan],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [11.0, 22.0, 0.0, 0.0, 0.0, 0.0],
            "household_weight": [1.0] * 6,
            "household_count_people": [1.0] * 6,
            "household_income_decile": [1, 2, -1, 0, 3, np.nan],
        },
        variables=variables,
    )

    impacts = []
    for decile in (1, 2):
        impact = DecileImpact.model_construct(
            baseline_simulation=baseline,
            reform_simulation=reform,
            income_variable="household_net_income",
            decile_variable="household_income_decile",
            entity="household",
            decile=decile,
            quantiles=2,
        )
        impact.run()
        impacts.append(impact)

    assert impacts[0].baseline_mean == pytest.approx(10.0)
    assert impacts[0].absolute_change == pytest.approx(1.0)
    assert impacts[0].count_better_off == pytest.approx(1.0)
    assert impacts[1].baseline_mean == pytest.approx(20.0)
    assert impacts[1].absolute_change == pytest.approx(2.0)
    assert impacts[1].count_better_off == pytest.approx(1.0)


def test_decile_impact_rejects_missing_reform_income_for_included_household():
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [10.0, 20.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [11.0, np.nan],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        },
        variables=variables,
    )

    impact = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        decile=1,
        quantiles=1,
    )

    with pytest.raises(ValueError):
        impact.run()


def test_decile_impact_allows_missing_reform_income_for_excluded_household():
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [10.0, 20.0],
            "household_weight": [1.0, 100.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, -1],
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": [11.0, np.nan],
            "household_weight": [1.0, 100.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, -1],
        },
        variables=variables,
    )

    impact = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        decile=1,
        quantiles=1,
    )
    impact.run()

    assert impact.baseline_mean == pytest.approx(10.0)
    assert impact.reform_mean == pytest.approx(11.0)
    assert impact.absolute_change == pytest.approx(1.0)


def test_decile_impact_rejects_misaligned_simulation_observations():
    variables = [_make_variable_mock("household_net_income", "household")]
    baseline = _make_sim(
        {
            "household_net_income": [10.0, 20.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        },
        variables=variables,
        index=["a", "b"],
    )
    reform = _make_sim(
        {
            "household_net_income": [11.0, 21.0],
            "household_weight": [1.0, 1.0],
            "household_count_people": [1.0, 1.0],
            "household_income_decile": [1, 1],
        },
        variables=variables,
        index=["a", "c"],
    )

    impact = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_income_decile",
        entity="household",
        decile=1,
        quantiles=1,
    )

    with pytest.raises(ValueError):
        impact.run()


def test_calculate_decile_impacts_with_decile_variable(monkeypatch):
    """calculate_decile_impacts passes pre-computed grouping through."""
    version = _make_version("household_net_income", "household")
    baseline = Simulation.model_construct(
        tax_benefit_model_version=version,
        output_dataset=MagicMock(
            data=MagicMock(
                household=MicroDataFrame(
                    pd.DataFrame(
                        {
                            "household_net_income": [10.0, 20.0, 100.0, 200.0],
                            "household_weight": [1.0, 1.0, 1.0, 1.0],
                            "household_wealth_decile": [2, 2, 1, 1],
                        }
                    ),
                    weights="household_weight",
                )
            )
        ),
    )
    reform = Simulation.model_construct(
        tax_benefit_model_version=version,
        output_dataset=MagicMock(
            data=MagicMock(
                household=MicroDataFrame(
                    pd.DataFrame(
                        {
                            "household_net_income": [11.0, 21.0, 110.0, 210.0],
                            "household_weight": [1.0, 1.0, 1.0, 1.0],
                            "household_wealth_decile": [2, 2, 1, 1],
                        }
                    ),
                    weights="household_weight",
                )
            )
        ),
    )

    monkeypatch.setattr(
        "policyengine.outputs.decile_impact.Simulation.ensure",
        lambda self: None,
    )

    results = calculate_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        decile_variable="household_wealth_decile",
        entity="household",
        quantiles=2,
    )

    decile_1 = next(r for r in results.outputs if r.decile == 1)
    decile_2 = next(r for r in results.outputs if r.decile == 2)

    assert decile_1.decile_variable == "household_wealth_decile"
    assert decile_1.baseline_mean == 150.0
    assert decile_1.reform_mean == 160.0
    assert decile_1.absolute_change == 10.0
    assert decile_2.baseline_mean == 15.0
    assert decile_2.absolute_change == 1.0
    assert results.dataframe["decile"].tolist() == [1, 2]
    assert results.dataframe["decile_variable"].tolist() == [
        "household_wealth_decile",
        "household_wealth_decile",
    ]


def test_decile_impact_weighted_grouping_default():
    """Without decile_variable, DecileImpact computes weighted groups."""
    n = 100
    incomes = np.linspace(10000, 100000, n)
    reform_incomes = incomes + 1000
    variables = [_make_variable_mock("household_net_income", "household")]

    baseline = _make_sim(
        {
            "household_net_income": incomes,
            "household_weight": np.ones(n),
            "household_count_people": np.ones(n),
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": reform_incomes,
            "household_weight": np.ones(n),
            "household_count_people": np.ones(n),
        },
        variables=variables,
    )

    di = DecileImpact.model_construct(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable="household_net_income",
        entity="household",
        decile=1,
    )
    di.run()

    # Decile 1 should be the lowest-income group
    # With uniform spacing, each decile has ~10 households
    assert di.baseline_mean is not None
    assert di.absolute_change is not None
    assert abs(di.absolute_change - 1000.0) < 1e-6


def test_decile_impact_defaults_to_household_net_income():
    """DecileImpact measures household net income unless configured otherwise."""
    impact = DecileImpact.model_construct(
        baseline_simulation=MagicMock(),
        reform_simulation=MagicMock(),
        decile=1,
    )

    assert impact.income_variable == "household_net_income"


def test_calculate_decile_impacts_uses_supplied_simulations(monkeypatch):
    """The helper reuses simulations and defaults to household net income."""
    version = _make_version("household_net_income", "household")
    baseline = Simulation.model_construct(
        tax_benefit_model_version=version,
        output_dataset=MagicMock(
            data=MagicMock(
                household=MicroDataFrame(
                    pd.DataFrame(
                        {
                            "household_net_income": [
                                40000.0,
                                60000.0,
                                80000.0,
                                100000.0,
                            ],
                            "household_weight": [1.0, 1.0, 1.0, 1.0],
                            "household_count_people": [1.0, 1.0, 1.0, 1.0],
                        }
                    ),
                    weights="household_weight",
                )
            )
        ),
    )
    reform = Simulation.model_construct(
        tax_benefit_model_version=version,
        output_dataset=MagicMock(
            data=MagicMock(
                household=MicroDataFrame(
                    pd.DataFrame(
                        {
                            "household_net_income": [
                                41000.0,
                                61000.0,
                                81000.0,
                                101000.0,
                            ],
                            "household_weight": [1.0, 1.0, 1.0, 1.0],
                            "household_count_people": [1.0, 1.0, 1.0, 1.0],
                        }
                    ),
                    weights="household_weight",
                )
            )
        ),
    )
    ensure_calls = []

    def fake_ensure(self):
        ensure_calls.append(self.id)

    monkeypatch.setattr(
        "policyengine.outputs.decile_impact.Simulation.ensure",
        fake_ensure,
    )

    results = calculate_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        entity="household",
        quantiles=2,
    )

    assert len(ensure_calls) == 2
    assert len(results.outputs) == 2
    assert all(
        result.income_variable == "household_net_income" for result in results.outputs
    )
    assert all(
        abs(result.absolute_change - 1000.0) < 1e-6 for result in results.outputs
    )


def test_calculate_decile_impacts_accepts_explicit_equiv_hbai_income(monkeypatch):
    """Callers can explicitly select equivalised HBAI net income."""
    variable = "equiv_hbai_household_net_income"
    version = _make_version(variable, "household")
    baseline = Simulation.model_construct(
        tax_benefit_model_version=version,
        output_dataset=MagicMock(
            data=MagicMock(
                household=MicroDataFrame(
                    pd.DataFrame(
                        {
                            variable: [10000.0, 20000.0, 30000.0, 40000.0],
                            "household_weight": [1.0, 1.0, 1.0, 1.0],
                            "household_count_people": [1.0, 1.0, 1.0, 1.0],
                        }
                    ),
                    weights="household_weight",
                )
            )
        ),
    )
    reform = Simulation.model_construct(
        tax_benefit_model_version=version,
        output_dataset=MagicMock(
            data=MagicMock(
                household=MicroDataFrame(
                    pd.DataFrame(
                        {
                            variable: [10500.0, 20500.0, 30500.0, 40500.0],
                            "household_weight": [1.0, 1.0, 1.0, 1.0],
                            "household_count_people": [1.0, 1.0, 1.0, 1.0],
                        }
                    ),
                    weights="household_weight",
                )
            )
        ),
    )

    monkeypatch.setattr(
        "policyengine.outputs.decile_impact.Simulation.ensure",
        lambda self: None,
    )

    results = calculate_decile_impacts(
        baseline_simulation=baseline,
        reform_simulation=reform,
        income_variable=variable,
        entity="household",
        quantiles=2,
    )

    assert all(result.income_variable == variable for result in results.outputs)
    assert all(result.absolute_change == 500.0 for result in results.outputs)


def test_calculate_decile_impacts_ensures_constructed_simulations(
    uk_test_dataset, monkeypatch
):
    """calculate_decile_impacts populates outputs when constructing simulations internally."""
    household_df = pd.DataFrame(uk_test_dataset.data.household)
    household_df["household_net_income"] = [
        10000.0,
        20000.0,
        30000.0,
    ]
    household_df["household_count_people"] = [2.0, 2.0, 2.0]
    uk_test_dataset.data.household = MicroDataFrame(
        household_df,
        weights="household_weight",
    )

    ensure_calls = []

    def fake_ensure(self):
        ensure_calls.append(self.id)
        self.output_dataset = uk_test_dataset

    monkeypatch.setattr(
        "policyengine.outputs.decile_impact.Simulation.ensure",
        fake_ensure,
    )

    results = calculate_decile_impacts(
        dataset=uk_test_dataset,
        tax_benefit_model_version=_make_version(
            "household_net_income",
            "household",
        ),
        quantiles=3,
    )

    assert len(ensure_calls) == 2
    assert len(results.outputs) == 3
    assert all(
        result.income_variable == "household_net_income" for result in results.outputs
    )
    assert all(abs(result.absolute_change) < 1e-9 for result in results.outputs)
