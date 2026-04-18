"""Unit tests for IntraDecileImpact and DecileImpact with decile_variable."""

from typing import Optional
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
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


def _make_sim(household_data: dict, variables: Optional[list] = None) -> MagicMock:
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


def test_intra_decile_overall_is_mean_of_deciles():
    """The overall row (decile=0) is the arithmetic mean of deciles 1-10."""
    n = 100
    incomes = np.linspace(10000, 100000, n)
    # Give a small gain so results aren't trivially all in one bucket
    reform_incomes = incomes * 1.02  # 2% gain (falls in gain_less_than_5pct)
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

    decile_rows = [r for r in results.outputs if r.decile != 0]
    overall = next(r for r in results.outputs if r.decile == 0)

    assert len(decile_rows) == 10

    expected_gain = sum(r.gain_less_than_5pct for r in decile_rows) / 10
    assert abs(overall.gain_less_than_5pct - expected_gain) < 1e-9

    expected_no_change = sum(r.no_change for r in decile_rows) / 10
    assert abs(overall.no_change - expected_no_change) < 1e-9


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


def test_decile_impact_qcut_default():
    """Without decile_variable, DecileImpact uses qcut (default behavior)."""
    n = 100
    incomes = np.linspace(10000, 100000, n)
    reform_incomes = incomes + 1000
    variables = [_make_variable_mock("household_net_income", "household")]

    baseline = _make_sim(
        {
            "household_net_income": incomes,
            "household_weight": np.ones(n),
        },
        variables=variables,
    )
    reform = _make_sim(
        {
            "household_net_income": reform_incomes,
            "household_weight": np.ones(n),
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


def test_calculate_decile_impacts_uses_supplied_simulations(monkeypatch):
    """calculate_decile_impacts can reuse simulations that already have outputs."""
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
        income_variable="household_net_income",
        entity="household",
        quantiles=2,
    )

    assert len(ensure_calls) == 2
    assert len(results.outputs) == 2
    assert all(
        abs(result.absolute_change - 1000.0) < 1e-6 for result in results.outputs
    )


def test_calculate_decile_impacts_ensures_constructed_simulations(
    uk_test_dataset, monkeypatch
):
    """calculate_decile_impacts populates outputs when constructing simulations internally."""
    household_df = pd.DataFrame(uk_test_dataset.data.household)
    household_df["equiv_hbai_household_net_income"] = [
        10000.0,
        20000.0,
        30000.0,
    ]
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
            "equiv_hbai_household_net_income",
            "household",
        ),
        quantiles=3,
    )

    assert len(ensure_calls) == 2
    assert len(results.outputs) == 3
    assert all(abs(result.absolute_change) < 1e-9 for result in results.outputs)
