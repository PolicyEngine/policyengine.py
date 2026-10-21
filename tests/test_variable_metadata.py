"""Tests for public variable metadata copied from country models."""

import datetime
import json
from types import SimpleNamespace

import pytest

from policyengine.core import TaxBenefitModel, TaxBenefitModelVersion
from policyengine.tax_benefit_models.common.model_version import (
    MicrosimulationModelVersion,
)
from policyengine.tax_benefit_models.uk import uk_latest
from policyengine.tax_benefit_models.us import us_latest

SELECTED_METADATA_FIELDS = {
    "definition_period",
    "unit",
    "quantity_type",
    "reference",
    "defined_for",
    "min_value",
    "max_value",
    "is_period_size_independent",
    "metadata",
}


def _model_version() -> TaxBenefitModelVersion:
    return TaxBenefitModelVersion(
        id="test@1",
        model=TaxBenefitModel(id="test", name="Test"),
        version="1",
    )


def test_populate_variables_exposes_selected_country_metadata():
    model = _model_version()
    core_variable = SimpleNamespace(
        name="sample_income",
        label="Sample income",
        entity=SimpleNamespace(key="person"),
        documentation="Income used to test metadata projection.",
        value_type=float,
        default_value=0.0,
        possible_values=None,
        adds=None,
        subtracts=None,
        definition_period="year",
        unit="currency-GBP",
        quantity_type="flow",
        reference=[
            "Example Act 2026",
            {"title": "Example guidance", "published": datetime.date(2026, 1, 1)},
        ],
        defined_for="is_adult",
        min_value=0,
        max_value=1_000_000.0,
        is_period_size_independent=False,
        metadata={"source": {"years": (2025, 2026)}},
    )
    system = SimpleNamespace(
        variables={core_variable.name: core_variable},
        parameters=None,
    )

    MicrosimulationModelVersion._populate_variables(model, system)

    variable = model.get_variable("sample_income")
    assert variable.definition_period == "year"
    assert variable.unit == "currency-GBP"
    assert variable.quantity_type == "flow"
    assert variable.reference == [
        "Example Act 2026",
        {"title": "Example guidance", "published": "2026-01-01"},
    ]
    assert variable.defined_for == "is_adult"
    assert variable.min_value == 0
    assert variable.max_value == 1_000_000.0
    assert variable.is_period_size_independent is False
    assert variable.metadata == {"source": {"years": [2025, 2026]}}

    payload = json.loads(variable.model_dump_json(include=SELECTED_METADATA_FIELDS))
    assert payload["reference"][1]["published"] == "2026-01-01"
    assert payload["metadata"] == {"source": {"years": [2025, 2026]}}


def test_selected_metadata_defaults_preserve_older_country_models():
    model = _model_version()
    core_variable = SimpleNamespace(
        name="minimal_input",
        label="Minimal input",
        entity=SimpleNamespace(key="person"),
        documentation=None,
        value_type=int,
        default_value=0,
        possible_values=None,
        adds=None,
        subtracts=None,
    )
    system = SimpleNamespace(
        variables={core_variable.name: core_variable},
        parameters=None,
    )

    MicrosimulationModelVersion._populate_variables(model, system)

    variable = model.get_variable("minimal_input")
    assert variable.definition_period is None
    assert variable.unit is None
    assert variable.quantity_type is None
    assert variable.reference is None
    assert variable.defined_for is None
    assert variable.min_value is None
    assert variable.max_value is None
    assert variable.is_period_size_independent is None
    assert variable.metadata == {}


def test_uk_model_exposes_selected_variable_metadata():
    employment_income = uk_latest.get_variable("employment_income")
    assert employment_income.definition_period == "year"
    assert employment_income.unit == "currency-GBP"
    assert employment_income.quantity_type == "flow"
    assert employment_income.reference == [
        "Income Tax (Earnings and Pensions) Act 2003 s. 1(1)(a)"
    ]
    assert employment_income.is_period_size_independent is False
    assert employment_income.metadata == {}

    child_benefit = uk_latest.get_variable("child_benefit")
    assert child_benefit.defined_for == "would_claim_child_benefit"
    assert child_benefit.min_value is None
    assert child_benefit.max_value is None


def test_us_model_exposes_selected_variable_metadata():
    employment_income = us_latest.get_variable("employment_income")
    assert employment_income.definition_period == "year"
    assert employment_income.unit == "currency-USD"
    assert employment_income.quantity_type == "flow"
    assert employment_income.reference == [
        "https://www.law.cornell.edu/uscode/text/26/3401#a"
    ]
    assert employment_income.is_period_size_independent is False
    assert employment_income.metadata == {}


def test_populate_variables_records_input_flags_and_module():
    model = _model_version()
    entered_input = SimpleNamespace(
        name="hours_worked",
        label="Hours worked",
        entity=SimpleNamespace(key="person"),
        documentation=None,
        value_type=float,
        default_value=0.0,
        possible_values=None,
        adds=None,
        subtracts=None,
        is_input_variable=lambda: True,
        hidden_input=True,
        module_name="household.labor.hours_worked",
    )
    calculated_value = SimpleNamespace(
        name="total_income",
        label="Total income",
        entity=SimpleNamespace(key="person"),
        documentation=None,
        value_type=float,
        default_value=0.0,
        possible_values=None,
        adds=["hours_worked"],
        subtracts=None,
        is_input_variable=lambda: False,
        hidden_input=False,
        module_name="household.income.total_income",
    )
    system = SimpleNamespace(
        variables={
            entered_input.name: entered_input,
            calculated_value.name: calculated_value,
        },
        parameters=None,
    )

    MicrosimulationModelVersion._populate_variables(model, system)

    hours_worked = model.get_variable("hours_worked")
    assert hours_worked.is_input_variable is True
    assert hours_worked.hidden_input is True
    assert hours_worked.module_name == "household.labor.hours_worked"
    total_income = model.get_variable("total_income")
    assert total_income.is_input_variable is False
    assert total_income.hidden_input is False
    assert total_income.module_name == "household.income.total_income"
    payload = json.loads(
        total_income.model_dump_json(
            include={"is_input_variable", "hidden_input", "module_name"}
        )
    )
    assert payload == {
        "is_input_variable": False,
        "hidden_input": False,
        "module_name": "household.income.total_income",
    }


def test_input_flags_and_module_default_to_unrecorded_for_older_country_models():
    model = _model_version()
    core_variable = SimpleNamespace(
        name="minimal_input",
        label="Minimal input",
        entity=SimpleNamespace(key="person"),
        documentation=None,
        value_type=int,
        default_value=0,
        possible_values=None,
        adds=None,
        subtracts=None,
    )
    system = SimpleNamespace(
        variables={core_variable.name: core_variable},
        parameters=None,
    )

    MicrosimulationModelVersion._populate_variables(model, system)

    variable = model.get_variable("minimal_input")
    assert variable.is_input_variable is None
    assert variable.hidden_input is None
    assert variable.module_name is None


@pytest.mark.parametrize(
    ("model", "country_system_module"),
    [(uk_latest, "policyengine_uk.system"), (us_latest, "policyengine_us.system")],
    ids=["uk", "us"],
)
def test_country_models_publish_input_flags_and_modules_as_core_declares_them(
    model, country_system_module
):
    country_system = pytest.importorskip(country_system_module).system

    for name, core_variable in country_system.variables.items():
        variable = model.get_variable(name)
        assert variable.is_input_variable is core_variable.is_input_variable(), name
        assert variable.hidden_input is core_variable.hidden_input, name
        assert variable.module_name == core_variable.module_name, name
    assert model.get_variable("age").is_input_variable is True
    assert any(variable.is_input_variable is False for variable in model.variables)


def test_us_model_publishes_hidden_inputs():
    hidden_inputs = [
        variable.name for variable in us_latest.variables if variable.hidden_input
    ]

    assert hidden_inputs, "The US package hides some inputs from input lists"
