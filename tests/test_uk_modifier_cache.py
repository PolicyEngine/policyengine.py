"""Each step on a built UK simulation refreshes what the next step reads.

policyengine-uk keeps each value it calculates. After building the
simulation, the UK population route runs the policy modifier, then the
dynamic's parameter values (written late, after a policy modifier), then the
dynamic modifier, and each can change what earlier values were calculated
from. These tests run one synthetic parent and child through that route, with
the real model, and check that each step and the output read values calculated
from the simulation as the step before left it, while the values a modifier
stores with ``set_input`` stay (PolicyEngine/policyengine.py#717).
"""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest
from microdf import MicroDataFrame

pytest.importorskip("policyengine_uk")

from policyengine.core import Dynamic, Policy, Simulation  # noqa: E402
from policyengine.tax_benefit_models.common.reform import (  # noqa: E402
    compile_reform_to_dynamic,
)
from policyengine.tax_benefit_models.uk.datasets import (  # noqa: E402
    PolicyEngineUKDataset,
    UKYearData,
)
from policyengine.tax_benefit_models.uk.model import uk_latest  # noqa: E402

YEAR = 2027
BENEFIT = "child_benefit"
NET_INCOME = "household_net_income"
ELDEST = "gov.hmrc.child_benefit.amount.eldest"


def values(microsim, variable):
    return np.asarray(microsim.calculate(variable, YEAR)).copy()


@pytest.fixture
def family(monkeypatch, tmp_path):
    """One synthetic parent and child, supplied in memory."""

    def table(columns, weights):
        return MicroDataFrame(pd.DataFrame(columns), weights=weights)

    dataset = PolicyEngineUKDataset(
        name="modifier-family",
        description="One synthetic parent and child",
        year=YEAR,
        filepath=None,
        data=UKYearData(
            person=table(
                {
                    "person_id": [101, 102],
                    "person_benunit_id": [11, 11],
                    "person_household_id": [1, 1],
                    "person_weight": [1.0, 1.0],
                    "age": [30, 2],
                    "gender": ["FEMALE", "FEMALE"],
                    "employment_income": [25_000.0, 0.0],
                    "hours_worked": [1_500.0, 0.0],
                },
                "person_weight",
            ),
            benunit=table(
                {"benunit_id": [11], "benunit_weight": [1.0]}, "benunit_weight"
            ),
            household=table(
                {
                    "household_id": [1],
                    "household_weight": [1.0],
                    "region": ["LONDON"],
                    "tenure_type": ["RENT_PRIVATELY"],
                    "rent": [12_000.0],
                    "council_tax": [1_500.0],
                },
                "household_weight",
            ),
        ),
    )
    supplied = {
        entity: pd.DataFrame(table).copy(deep=True)
        for entity, table in dataset.data.entity_data.items()
    }

    def unexpected_load(self):
        raise AssertionError("A dataset supplied in memory must not load from disk")

    monkeypatch.setattr(PolicyEngineUKDataset, "load", unexpected_load)
    # The package's ``model`` attribute shadows the submodule's name.
    model_module = importlib.import_module("policyengine.tax_benefit_models.uk.model")
    monkeypatch.setattr(
        model_module,
        "_output_dataset_filepath",
        lambda simulation: tmp_path / f"{simulation.id}.h5",
    )
    yield dataset
    # The run leaves the caller's tables as supplied.
    for entity, table in dataset.data.entity_data.items():
        pd.testing.assert_frame_equal(pd.DataFrame(table), supplied[entity])


def run(dataset, *, policy=None, dynamic=None):
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
        policy=policy,
        dynamic=dynamic,
    )
    simulation.run()
    return simulation


def output(simulation, entity, variable):
    return np.asarray(getattr(simulation.output_dataset.data, entity)[variable])


def benefit_rise(callback=None):
    """A dynamic adding £1,000 a year to the eldest child's Child Benefit."""
    from policyengine_uk import CountryTaxBenefitSystem

    weekly = CountryTaxBenefitSystem().parameters.get_child(ELDEST)(str(YEAR))
    dynamic = compile_reform_to_dynamic(
        {ELDEST: weekly + 1_000 / 52}, year=YEAR, model_version=uk_latest
    )
    dynamic.simulation_modifier = callback
    return dynamic


@pytest.mark.parametrize(
    "with_dynamic_modifier",
    [False, True],
    ids=["dynamic-values-only", "dynamic-modifier-reads"],
)
def test_late_dynamic_values_reach_values_the_policy_modifier_calculated(
    family, with_dynamic_modifier
):
    """The policy modifier calculates Child Benefit and net income; the
    dynamic's values, written after it, raise Child Benefit by £1,000. The
    dynamic modifier and the output read the raised amount."""
    captured = {}
    events = []

    def warm(microsim):
        events.append("policy modifier")
        captured["before"] = values(microsim, BENEFIT)
        assert captured["before"][0] > 0
        values(microsim, NET_INCOME)
        return microsim

    def read(microsim):
        events.append("dynamic modifier")
        np.testing.assert_allclose(
            values(microsim, BENEFIT), captured["before"] + 1_000, atol=0.01
        )
        return microsim

    warmed = run(
        family,
        policy=Policy(name="Warm", simulation_modifier=warm),
        dynamic=benefit_rise(read if with_dynamic_modifier else None),
    )
    # Without a policy modifier the dynamic's values join the construction
    # reform, so nothing is calculated before them.
    cold = run(family, dynamic=benefit_rise())

    expected = output(cold, "benunit", BENEFIT)
    np.testing.assert_allclose(expected, captured["before"] + 1_000, atol=0.01)
    np.testing.assert_allclose(output(warmed, "benunit", BENEFIT), expected, atol=0.01)
    np.testing.assert_allclose(
        output(warmed, "household", NET_INCOME),
        output(cold, "household", NET_INCOME),
        atol=0.01,
    )
    assert events == (
        ["policy modifier", "dynamic modifier"]
        if with_dynamic_modifier
        else ["policy modifier"]
    )


def test_policy_modifier_inputs_stay_and_what_it_calculated_is_refreshed(family):
    """A policy modifier calculates net income, then stores Child Benefit
    £1,000 higher with ``set_input``. The stored amount stays through every
    step, and net income read after the modifier includes it, as when the
    modifier stores the same amount without calculating net income first."""
    from policyengine_uk import CountryTaxBenefitSystem

    weekly = CountryTaxBenefitSystem().parameters.get_child(ELDEST)(str(YEAR))
    # A rise of one penny a week, written late after the policy modifier.
    late_values = compile_reform_to_dynamic(
        {ELDEST: weekly + 0.01}, year=YEAR, model_version=uk_latest
    ).parameter_values
    stored = {}

    def raise_benefit(arm, calculate_net_income_first):
        def modifier(microsim):
            if calculate_net_income_first:
                values(microsim, NET_INCOME)
            stored[arm] = values(microsim, BENEFIT) + 1_000
            microsim.set_input(BENEFIT, YEAR, stored[arm])
            return microsim

        return modifier

    def read(microsim):
        np.testing.assert_allclose(values(microsim, BENEFIT), stored["warmed"])
        return microsim

    warmed = run(
        family,
        policy=Policy(name="Warm", simulation_modifier=raise_benefit("warmed", True)),
        dynamic=Dynamic(name="Late", parameter_values=late_values)
        + Dynamic(name="Read", simulation_modifier=read),
    )
    cold = run(
        family,
        policy=Policy(name="Cold", simulation_modifier=raise_benefit("cold", False)),
        dynamic=Dynamic(name="Late", parameter_values=late_values),
    )

    np.testing.assert_allclose(stored["warmed"], stored["cold"])
    np.testing.assert_allclose(output(warmed, "benunit", BENEFIT), stored["warmed"])
    np.testing.assert_allclose(output(cold, "benunit", BENEFIT), stored["cold"])
    np.testing.assert_allclose(
        output(warmed, "household", NET_INCOME),
        output(cold, "household", NET_INCOME),
        atol=0.01,
    )


def test_a_failed_modifier_ends_the_run_after_dropping_what_it_calculated(family):
    """A policy modifier that fails after calculating stops the run: the
    error reaches the caller, no later step runs, and the simulation keeps
    its inputs but none of the values the modifier calculated."""
    captured = {}
    events = []

    def fail(microsim):
        events.append("policy modifier")
        captured["microsim"] = microsim
        values(microsim, BENEFIT)
        raise RuntimeError("policy modifier failed")

    def later(microsim):
        events.append("dynamic modifier")
        return microsim

    with pytest.raises(RuntimeError, match="policy modifier failed"):
        run(
            family,
            policy=Policy(name="Fails", simulation_modifier=fail),
            dynamic=benefit_rise(later),
        )

    microsim = captured["microsim"]
    assert events == ["policy modifier"]
    assert microsim.get_holder(BENEFIT).get_array(YEAR) is None
    assert microsim.get_holder("age").get_array(YEAR) is not None
