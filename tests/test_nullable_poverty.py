"""Synthetic nullable-status contract checks; no country model or dataset needed."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
from microdf import MicroDataFrame

from policyengine.core import (
    Dataset,
    Simulation,
    TaxBenefitModel,
    TaxBenefitModelVersion,
    Variable,
)
from policyengine.core.dataset import YearData
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.outputs.change_aggregate import ChangeAggregate, ChangeAggregateType
from policyengine.outputs.poverty import (
    UK_POVERTY_VARIABLES,
    Poverty,
    calculate_uk_poverty_by_age,
    calculate_uk_poverty_by_gender,
    calculate_uk_poverty_rates,
    calculate_us_poverty_by_age,
    calculate_us_poverty_by_gender,
    calculate_us_poverty_by_race,
    calculate_us_poverty_rates,
)

ALIASES = (
    "in_poverty",
    "in_deep_poverty",
    "person_in_poverty",
    "spm_unit_is_in_spm_poverty",
    "spm_unit_is_in_deep_spm_poverty",
)


class SyntheticYearData(YearData):
    person: MicroDataFrame
    spm_unit: MicroDataFrame
    household: MicroDataFrame

    @property
    def entity_data(self):
        return {
            "person": self.person,
            "spm_unit": self.spm_unit,
            "household": self.household,
        }


def make_sim(statuses=(1.0, 0.0, np.nan), weights=(2.0, 3.0, 100.0)):
    """Two people in unit 1; unit 3 is outside the measurement universe."""
    model = TaxBenefitModelVersion(
        model=TaxBenefitModel(id="synthetic"), version="test"
    )
    spm = MicroDataFrame(
        {
            "spm_unit_id": [1, 2, 3],
            "spm_unit_weight": weights,
            "spm_unit_amount": [10.0, 20.0, 30.0],
            "spm_unit_test_indicator": [1.0, 1.0, 1.0],
            **{name: statuses for name in ALIASES[3:]},
        },
        weights="spm_unit_weight",
    )
    person = MicroDataFrame(
        {
            "person_id": [1, 2, 3, 4],
            "spm_unit_id": [1, 1, 2, 3],
            "household_id": [1, 1, 2, 3],
            "person_weight": [weights[0], weights[0], weights[1], weights[2]],
            "person_amount": [10.0, 20.0, 30.0, 40.0],
            "person_test_indicator": [1.0, 1.0, 1.0, 1.0],
            "age": [10, 35, 40, 75],
            "is_male": [True, True, True, False],
            "race": ["WHITE", "WHITE", "WHITE", "BLACK"],
            **{
                name: [statuses[0], statuses[0], statuses[1], statuses[2]]
                for name in (*ALIASES[:3], *UK_POVERTY_VARIABLES.values())
            },
        },
        weights="person_weight",
    )
    household = MicroDataFrame(
        {
            "household_id": [1, 2, 3],
            "household_weight": weights,
            "household_amount": [10.0, 20.0, 30.0],
            "household_test_indicator": [1.0, 1.0, 1.0],
        },
        weights="household_weight",
    )
    for entity, frame in (
        ("person", person),
        ("spm_unit", spm),
        ("household", household),
    ):
        for name in frame.columns:
            if name not in model.variables_by_name:
                model.add_variable(
                    Variable(
                        id=name,
                        name=name,
                        entity=entity,
                        tax_benefit_model_version=model,
                    )
                )
    dataset = Dataset(
        name="Synthetic nullable SPM statuses",
        description="Small unit fixture; not a certified population dataset.",
        year=2025,
        data=SyntheticYearData(person=person, spm_unit=spm, household=household),
    )
    return Simulation(
        dataset=dataset, output_dataset=dataset, tax_benefit_model_version=model
    )


@pytest.mark.parametrize("alias", ALIASES)
@pytest.mark.parametrize(
    "entity,headcount,population", [("person", 4.0, 7.0), ("native", 2.0, 5.0)]
)
def test_nullable_status_uses_eligible_weight_and_entity_projection(
    alias, entity, headcount, population
):
    sim = make_sim()
    if entity == "native":
        entity = sim.tax_benefit_model_version.get_variable(alias).entity
        if entity == "person":
            headcount, population = 4.0, 7.0
    result = Poverty(simulation=sim, poverty_variable=alias, entity=entity)
    result.run()
    assert result.headcount == headcount
    assert result.total_population == population
    assert result.rate == pytest.approx(headcount / population)


@pytest.mark.parametrize("alias", ALIASES)
@pytest.mark.parametrize(
    "case", ["all_missing", "zero_weight", "outside_only", "empty_filter"]
)
def test_empty_eligible_denominator_is_null(alias, case):
    sim = make_sim(
        statuses=(np.nan, np.nan, np.nan)
        if case == "all_missing"
        else (1.0, 0.0, np.nan),
        weights=(0.0, 0.0, 100.0) if case == "zero_weight" else (2.0, 3.0, 100.0),
    )
    filters = {}
    if case in ("outside_only", "empty_filter"):
        filters = {
            "filter_variable": "age",
            "filter_variable_geq": 65 if case == "outside_only" else 100,
        }
    result = Poverty(simulation=sim, poverty_variable=alias, **filters)
    result.run()
    assert result.headcount == 0.0
    assert result.total_population == 0.0
    assert result.rate is None
    payload = result.model_dump(include={"headcount", "total_population", "rate"})
    assert json.loads(json.dumps(payload, allow_nan=False))["rate"] is None


@pytest.mark.parametrize("alias", ALIASES)
def test_eligible_nonpoor_is_a_measured_zero(alias):
    result = Poverty(
        simulation=make_sim(statuses=(0.0, 0.0, np.nan)), poverty_variable=alias
    )
    result.run()
    assert result.total_population == 7.0
    assert result.rate == 0.0


@pytest.mark.parametrize(
    "calculate",
    [
        calculate_us_poverty_rates,
        calculate_us_poverty_by_age,
        calculate_us_poverty_by_gender,
        calculate_us_poverty_by_race,
        calculate_uk_poverty_rates,
        calculate_uk_poverty_by_age,
        calculate_uk_poverty_by_gender,
    ],
)
@pytest.mark.parametrize("all_missing", [False, True])
def test_poverty_collections_export_nullable_strict_json(calculate, all_missing):
    sim = make_sim(
        statuses=(np.nan, np.nan, np.nan) if all_missing else (1.0, 0.0, np.nan)
    )
    result = calculate(sim)
    records = result.dataframe.to_dict("records")
    assert str(result.dataframe["rate"].dtype) == "Float64"
    for record, output in zip(records, result.outputs):
        assert record["rate"] == output.rate
    json.dumps(records, allow_nan=False)
    if all_missing:
        assert all(record["rate"] is None for record in records)
    elif "by_" in calculate.__name__:
        assert any(record["rate"] is None for record in records)
        assert any(record["rate"] is not None for record in records)


@pytest.mark.parametrize("alias", ALIASES)
@pytest.mark.parametrize(
    "kind,expected",
    [
        (AggregateType.SUM, 4.0),
        (AggregateType.COUNT, 7.0),
        (AggregateType.MEAN, 4.0 / 7.0),
    ],
)
def test_generic_aggregate_preserves_nullable_status(alias, kind, expected):
    result = Aggregate(
        simulation=make_sim(), variable=alias, entity="person", aggregate_type=kind
    )
    result.run()
    assert result.result == pytest.approx(expected)


@pytest.mark.parametrize("all_missing", [False, True])
@pytest.mark.parametrize("change", [False, True])
def test_generic_empty_mean_is_null(all_missing, change):
    sim = make_sim(
        statuses=(np.nan, np.nan, np.nan) if all_missing else (1.0, 0.0, np.nan),
        weights=(2.0, 3.0, 100.0) if all_missing else (0.0, 0.0, 100.0),
    )
    if change:
        result = ChangeAggregate(
            baseline_simulation=sim,
            reform_simulation=sim,
            variable=ALIASES[3],
            entity="person",
            aggregate_type=ChangeAggregateType.MEAN,
        )
    else:
        result = Aggregate(
            simulation=sim,
            variable=ALIASES[3],
            entity="person",
            aggregate_type=AggregateType.MEAN,
        )
    result.run()
    assert result.result is None
    json.dumps({"result": result.result}, allow_nan=False)


@pytest.fixture
def us_household_module(monkeypatch):
    """Load the real facade with model metadata stubbed, without country imports."""
    import policyengine

    fake_model = ModuleType("policyengine.tax_benefit_models.us.model")
    fake_model.us_latest = make_sim().tax_benefit_model_version
    monkeypatch.setitem(sys.modules, fake_model.__name__, fake_model)
    name = "policyengine.tax_benefit_models.us._nullable_household_test"
    source = Path(policyengine.__file__).parent / "tax_benefit_models/us/household.py"
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "value,expected",
    [
        (np.nan, None),
        (np.float32("nan"), None),
        (np.inf, None),
        (-np.inf, None),
        (1.0, 1.0),
        (0.0, 0.0),
        ("WHITE", "WHITE"),
        (None, None),
    ],
)
def test_household_nullable_scalar_is_strict_json(us_household_module, value, expected):
    result = us_household_module._safe_convert(value)
    assert result == expected
    json.dumps({"value": result}, allow_nan=False)


@pytest.mark.parametrize("axes_active", [False, True])
def test_household_facade_exports_all_nullable_aliases(
    us_household_module, monkeypatch, tmp_path, axes_active
):
    """Exercise result assembly with synthetic country outputs, including axes."""
    calculated = []

    class SyntheticCountrySimulation:
        def __init__(self, **kwargs):
            pass

        def calculate(self, variable, period, map_to):
            calculated.append((variable, period, map_to))
            return np.array([np.nan, 1.0]) if axes_active else np.array([np.nan])

    country = ModuleType("policyengine_us")
    country.Simulation = SyntheticCountrySimulation
    monkeypatch.setitem(sys.modules, "policyengine_us", country)
    columns = {"person": list(ALIASES[:3]), "spm_unit": list(ALIASES[3:])}
    monkeypatch.setattr(
        us_household_module, "_default_output_columns", lambda extras: columns
    )
    if axes_active:
        monkeypatch.setattr(
            us_household_module, "normalize_axes", lambda **kwargs: [[{}]]
        )

    result = us_household_module.calculate_household(people=[{}], year=2025)
    expected = [None, 1.0] if axes_active else None
    for alias in ALIASES[:3]:
        assert result.person[0][alias] == expected
    for alias in ALIASES[3:]:
        assert result.spm_unit[alias] == expected
    assert set(calculated) == {
        (alias, 2025, entity)
        for entity, aliases in columns.items()
        for alias in aliases
    }
    records = result.to_dict()
    assert json.loads(json.dumps(records, allow_nan=False)) == records
    assert json.loads(result.write(tmp_path / "household.json").read_text()) == records


@pytest.mark.parametrize(
    "kind,expected",
    [
        (ChangeAggregateType.SUM, -4.0),
        (ChangeAggregateType.COUNT, 4.0),
        (ChangeAggregateType.MEAN, -1.0),
    ],
)
def test_change_aggregate_requires_observed_status_in_both_simulations(kind, expected):
    result = ChangeAggregate(
        baseline_simulation=make_sim(),
        reform_simulation=make_sim(statuses=(0.0, np.nan, 1.0)),
        variable=ALIASES[3],
        entity="person",
        aggregate_type=kind,
    )
    result.run()
    assert result.result == expected


@pytest.mark.parametrize("change", [False, True])
def test_filtered_empty_generic_mean_is_null(change):
    sim = make_sim()
    options = {
        "variable": ALIASES[3],
        "entity": "person",
        "filter_variable": "age",
        "filter_variable_geq": 100,
    }
    if change:
        result = ChangeAggregate(
            baseline_simulation=sim,
            reform_simulation=sim,
            aggregate_type=ChangeAggregateType.MEAN,
            **options,
        )
    else:
        result = Aggregate(simulation=sim, aggregate_type=AggregateType.MEAN, **options)
    result.run()
    assert result.result is None


def make_summary(caller, simulation, variable, entity, **filters):
    if caller == "Poverty":
        return Poverty(
            simulation=simulation, poverty_variable=variable, entity=entity, **filters
        )
    if caller == "Aggregate":
        return Aggregate(
            simulation=simulation,
            variable=variable,
            entity=entity,
            aggregate_type=AggregateType.COUNT,
            **filters,
        )
    return ChangeAggregate(
        baseline_simulation=simulation,
        reform_simulation=simulation,
        variable=variable,
        entity=entity,
        aggregate_type=ChangeAggregateType.COUNT,
        **filters,
    )


@pytest.mark.parametrize("alias", ALIASES)
@pytest.mark.parametrize("caller", ["Poverty", "Aggregate", "ChangeAggregate"])
@pytest.mark.parametrize("as_filter", [False, True])
def test_undefined_status_aggregation_raises_before_outside_becomes_zero(
    alias, caller, as_filter
):
    sim = make_sim(statuses=(np.nan, np.nan, np.nan))
    source = sim.tax_benefit_model_version.get_variable(alias).entity
    target = "spm_unit" if source == "person" else "household"
    filters = {}
    variable = alias
    if as_filter:
        variable = (
            f"{target}_test_indicator" if caller == "Poverty" else f"{target}_amount"
        )
        filters = {"filter_variable": alias, "filter_variable_eq": 0.0}
    result = make_summary(caller, sim, variable, target, **filters)
    with pytest.raises(ValueError) as error:
        result.run()
    message = str(error.value)
    assert message.startswith(f"{caller}.")
    assert alias in message
    assert f"from '{source}' to '{target}'" in message
    assert "native entity or project it to 'person'" in message
    assert (
        "filter_variable" in message if as_filter else "filter_variable" not in message
    )


@pytest.mark.parametrize("alias", ALIASES)
@pytest.mark.parametrize("caller", ["Poverty", "Aggregate", "ChangeAggregate"])
@pytest.mark.parametrize("target", ["native", "person"])
def test_nullable_status_filters_allow_native_and_person_projection(
    alias, caller, target
):
    sim = make_sim()
    if target == "native":
        target = sim.tax_benefit_model_version.get_variable(alias).entity
    variable = f"{target}_test_indicator" if caller == "Poverty" else f"{target}_amount"
    result = make_summary(
        caller, sim, variable, target, filter_variable=alias, filter_variable_eq=0.0
    )
    result.run()
    if caller == "Poverty":
        assert result.total_population == 3.0
        assert result.headcount == 3.0
    else:
        assert result.result == 3.0


def test_generic_amount_upward_mapping_remains_available():
    result = Aggregate(
        simulation=make_sim(),
        variable="person_amount",
        entity="spm_unit",
        aggregate_type=AggregateType.SUM,
    )
    result.run()
    assert result.result == 4150.0
