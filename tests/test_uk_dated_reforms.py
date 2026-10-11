"""UK household reform dates share the wrapper policy's effective-date reading."""

import pytest

import policyengine as pe
import policyengine.tax_benefit_models.uk.household as uk_household

INCOME_TAX_RATE = "gov.hmrc.income_tax.rates.uk[0].rate"


@pytest.mark.parametrize(
    ("schedule", "expected"),
    [
        (0.21, {"2027-01-01.2100-12-31": 0.21}),
        ({"2027-04-06": 0.21}, {"2027-04-06.2100-12-31": 0.21}),
        (
            {"2027-04-06.2028-04-05": 0.21},
            {"2027-04-06.2028-04-05": 0.21},
        ),
        (
            {"2028-04-06": 0.22, "2027-04-06": 0.21},
            {
                "2028-04-06.2100-12-31": 0.22,
                "2027-04-06.2028-04-05": 0.21,
            },
        ),
    ],
    ids=["scalar", "effective-date", "interval", "reverse-date-schedule"],
)
def test_household_constructor_receives_inclusive_ranges(
    monkeypatch, schedule, expected
):
    captured = {}

    class CapturingSimulation:
        def __init__(self, *, situation, reform):
            captured["reform"] = reform

        def calculate(self, variable, period, map_to):
            return [0.0]

    monkeypatch.setattr("policyengine_uk.Simulation", CapturingSimulation)
    monkeypatch.setattr(
        uk_household,
        "_default_output_columns",
        lambda extra: {"person": ["income_tax"]},
    )

    pe.uk.calculate_household(
        people=[{"age": 40, "employment_income": 30_000}],
        year=2027,
        reform={INCOME_TAX_RATE: schedule},
    )

    assert captured["reform"] == {INCOME_TAX_RATE: expected}
    assert all("." in key for key in captured["reform"][INCOME_TAX_RATE])


def test_household_reform_keeps_unknown_path_validation(monkeypatch):
    def unexpected_simulation(**kwargs):
        pytest.fail("An invalid reform should fail before simulation construction")

    monkeypatch.setattr("policyengine_uk.Simulation", unexpected_simulation)

    with pytest.raises(ValueError, match="did you mean"):
        pe.uk.calculate_household(
            people=[{"age": 40}],
            year=2027,
            reform={"gov.hmrc.income_tax.rates.uk[0].rat": 0.21},
        )


def test_household_april_effective_date_changes_fiscal_year_income_tax():
    pytest.importorskip("policyengine_uk.utils.dated_reforms")

    inputs = {"people": [{"age": 40, "employment_income": 30_000}], "year": 2027}
    baseline = pe.uk.calculate_household(**inputs)
    reformed = pe.uk.calculate_household(
        **inputs,
        reform={INCOME_TAX_RATE: {"2027-04-06": 0.21}},
    )

    assert reformed.person[0].income_tax - baseline.person[
        0
    ].income_tax == pytest.approx(174.30, abs=0.01)


@pytest.mark.parametrize(("year", "expected_change"), [(2027, 174.30), (2028, 0.0)])
def test_household_interval_reform_expires_after_fiscal_year(year, expected_change):
    pytest.importorskip("policyengine_uk.utils.dated_reforms")

    inputs = {"people": [{"age": 40, "employment_income": 30_000}], "year": year}
    baseline = pe.uk.calculate_household(**inputs)
    reformed = pe.uk.calculate_household(
        **inputs,
        reform={INCOME_TAX_RATE: {"2027-04-06.2028-04-05": 0.21}},
    )

    assert reformed.person[0].income_tax - baseline.person[
        0
    ].income_tax == pytest.approx(expected_change, abs=0.01)


def test_merged_override_periods_come_last_and_win_where_they_overlap():
    from policyengine.utils.parametric_reforms import merge_reform_dicts

    policy = {
        INCOME_TAX_RATE: {
            "2027-01-01.2100-12-31": 0.21,
            "2028-01-01.2100-12-31": 0.22,
        }
    }
    dynamic = {INCOME_TAX_RATE: {"2027-01-01.2100-12-31": 0.30}}
    merged = merge_reform_dicts(policy, dynamic)
    assert list(merged[INCOME_TAX_RATE].items()) == [
        ("2028-01-01.2100-12-31", 0.22),
        ("2027-01-01.2100-12-31", 0.30),
    ]
    # The inputs are not changed.
    assert list(policy[INCOME_TAX_RATE]) == [
        "2027-01-01.2100-12-31",
        "2028-01-01.2100-12-31",
    ]


class _StopRun(Exception):
    pass


def _run_population_route(monkeypatch, policy, dynamic, events):
    """Run the UK population route up to its first calculation."""
    import importlib

    import pandas as pd
    from microdf import MicroDataFrame

    import policyengine.utils.parametric_reforms as parametric_reforms
    from policyengine.core import Simulation
    from policyengine.tax_benefit_models.uk.datasets import (
        PolicyEngineUKDataset,
        UKYearData,
    )

    # The package's ``model`` attribute shadows the submodule's name.
    uk_model = importlib.import_module("policyengine.tax_benefit_models.uk.model")

    class RecordingMicrosimulation:
        def __init__(self, *, dataset, reform=None):
            events.append(("construct", reform))

        def calculate(self, *args, **kwargs):
            raise _StopRun

    monkeypatch.setattr("policyengine_uk.Microsimulation", RecordingMicrosimulation)
    monkeypatch.setattr(uk_model, "_policyengine_uk_input", lambda dataset: None)
    monkeypatch.setattr(
        parametric_reforms,
        "simulation_modifier_from_parameter_values",
        lambda values: (
            lambda sim: events.append(
                ("late parameter values", [(v.parameter.name, v.value) for v in values])
            )
        ),
    )

    def table(columns, weights):
        return MicroDataFrame(pd.DataFrame(columns), weights=weights)

    dataset = PolicyEngineUKDataset(
        id="order",
        name="order",
        description="order",
        filepath=None,
        year=2028,
        data=UKYearData(
            person=table(
                {
                    "person_id": [1],
                    "person_benunit_id": [1],
                    "person_household_id": [1],
                    "person_weight": [1.0],
                },
                "person_weight",
            ),
            benunit=table(
                {"benunit_id": [1], "benunit_weight": [1.0]}, "benunit_weight"
            ),
            household=table(
                {"household_id": [1], "household_weight": [1.0]}, "household_weight"
            ),
        ),
    )
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.uk.model,
        policy=policy,
        dynamic=dynamic,
    )
    with pytest.raises(_StopRun):
        pe.uk.model.run(simulation)


@pytest.mark.parametrize(
    "policy_kind, dynamic_kind, expected",
    [
        (
            "parametric",
            "parametric",
            [("construct", {INCOME_TAX_RATE: {"2027-04-06.2100-12-31": 0.30}})],
        ),
        (
            "parametric",
            "custom",
            [
                ("construct", {INCOME_TAX_RATE: {"2027-04-06.2100-12-31": 0.21}}),
                "dynamic modifier",
            ],
        ),
        (
            # The dynamic still follows the custom policy, as before #572.
            "custom",
            "parametric",
            [
                ("construct", None),
                "policy modifier",
                ("late parameter values", [(INCOME_TAX_RATE, 0.30)]),
            ],
        ),
        (
            "custom",
            "custom",
            [("construct", None), "policy modifier", "dynamic modifier"],
        ),
    ],
)
def test_population_route_applies_policy_before_dynamic(
    monkeypatch, policy_kind, dynamic_kind, expected
):
    from policyengine.core import Dynamic, Policy
    from policyengine.tax_benefit_models.common.reform import (
        _reform_dict_to_parameter_values,
    )

    events = []

    def make(cls, kind, value, name):
        if kind == "custom":
            return cls(name=name, simulation_modifier=lambda sim: events.append(name))
        return cls(
            name=name,
            parameter_values=_reform_dict_to_parameter_values(
                {INCOME_TAX_RATE: {"2027-04-06": value}},
                year=2028,
                model_version=pe.uk.model,
            ),
        )

    _run_population_route(
        monkeypatch,
        make(Policy, policy_kind, 0.21, "policy modifier"),
        make(Dynamic, dynamic_kind, 0.30, "dynamic modifier"),
        events,
    )
    assert events == expected
