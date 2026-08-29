"""Tests for public variable metadata copied from country models."""

import datetime
import json
from types import SimpleNamespace

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

    personal_rent = uk_latest.get_variable("personal_rent")
    assert personal_rent.defined_for == "is_household_head"
    assert personal_rent.min_value is None
    assert personal_rent.max_value is None


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
