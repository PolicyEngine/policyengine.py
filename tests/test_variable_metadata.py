"""Tests for public variable metadata copied from country models."""

import datetime
import importlib
import json
from enum import Enum
from types import SimpleNamespace

import pytest
from policyengine_core.parameters import ParameterNode as CoreParameterNode

from policyengine.core import EnumValue, TaxBenefitModel, TaxBenefitModelVersion
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
    country_system = importlib.import_module(country_system_module).system

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


class _FilingStatus(Enum):
    SINGLE = "Single"
    JOINT = "Joint"
    HEAD_OF_HOUSEHOLD = "Head of household"


class _NumberedStatus(Enum):
    FIRST = 1
    SECOND = 2


def _enum_core_variable(name: str, possible_values: type[Enum]) -> SimpleNamespace:
    first_member = next(iter(possible_values))
    return SimpleNamespace(
        name=name,
        label=name.replace("_", " ").capitalize(),
        entity=SimpleNamespace(key="tax_unit"),
        documentation=None,
        value_type=str,
        default_value=first_member.name,
        possible_values=possible_values,
        adds=None,
        subtracts=None,
    )


def test_populate_variables_records_enum_values_with_their_labels_in_order():
    model = _model_version()
    filing_status = _enum_core_variable("filing_status", _FilingStatus)
    system = SimpleNamespace(
        variables={filing_status.name: filing_status},
        parameters=None,
    )

    MicrosimulationModelVersion._populate_variables(model, system)

    variable = model.get_variable("filing_status")
    assert variable.possible_values == ["SINGLE", "JOINT", "HEAD_OF_HOUSEHOLD"]
    assert variable.enum_values == [
        EnumValue(value="SINGLE", label="Single"),
        EnumValue(value="JOINT", label="Joint"),
        EnumValue(value="HEAD_OF_HOUSEHOLD", label="Head of household"),
    ]
    assert json.loads(variable.model_dump_json(include={"enum_values"})) == {
        "enum_values": [
            {"value": "SINGLE", "label": "Single"},
            {"value": "JOINT", "label": "Joint"},
            {"value": "HEAD_OF_HOUSEHOLD", "label": "Head of household"},
        ]
    }


def test_enum_values_keep_integer_labels_as_declared():
    # The Public API's /{country}/metadata publishes an enum member's
    # declared value unchanged, so an integer stays an integer.
    model = _model_version()
    numbered_status = _enum_core_variable("numbered_status", _NumberedStatus)
    system = SimpleNamespace(
        variables={numbered_status.name: numbered_status},
        parameters=None,
    )

    MicrosimulationModelVersion._populate_variables(model, system)

    enum_values = model.get_variable("numbered_status").enum_values
    assert [(enum_value.value, enum_value.label) for enum_value in enum_values] == [
        ("FIRST", 1),
        ("SECOND", 2),
    ]
    assert all(type(enum_value.label) is int for enum_value in enum_values)
    assert json.loads(
        model.get_variable("numbered_status").model_dump_json(include={"enum_values"})
    ) == {
        "enum_values": [
            {"value": "FIRST", "label": 1},
            {"value": "SECOND", "label": 2},
        ]
    }


def test_variables_without_possible_values_have_no_enum_values():
    model = _model_version()
    core_variable = SimpleNamespace(
        name="minimal_input",
        label="Minimal input",
        entity=SimpleNamespace(key="person"),
        documentation=None,
        value_type=int,
        default_value=0,
        adds=None,
        subtracts=None,
    )
    system = SimpleNamespace(
        variables={core_variable.name: core_variable},
        parameters=None,
    )

    MicrosimulationModelVersion._populate_variables(model, system)

    assert model.get_variable("minimal_input").enum_values is None


@pytest.mark.parametrize(
    ("model", "country_system_module"),
    [(uk_latest, "policyengine_uk.system"), (us_latest, "policyengine_us.system")],
    ids=["uk", "us"],
)
def test_country_models_publish_every_enum_label(model, country_system_module):
    country_system = importlib.import_module(country_system_module).system

    enum_variable_count = 0
    for name, core_variable in country_system.variables.items():
        possible_values = getattr(core_variable, "possible_values", None)
        variable = model.get_variable(name)
        if possible_values is None:
            assert variable.enum_values is None, name
            continue
        enum_variable_count += 1
        assert [
            (enum_value.value, enum_value.label) for enum_value in variable.enum_values
        ] == [(member.name, member.value) for member in possible_values], name
        assert [type(enum_value.label) for enum_value in variable.enum_values] == [
            type(member.value) for member in possible_values
        ], name
        assert [enum_value.value for enum_value in variable.enum_values] == (
            variable.possible_values
        ), name
    assert enum_variable_count > 0


def test_us_filing_status_publishes_its_labels():
    filing_status = us_latest.get_variable("filing_status")

    assert EnumValue(value="SINGLE", label="Single") in filing_status.enum_values
    assert EnumValue(value="JOINT", label="Joint") in filing_status.enum_values


def test_us_integer_valued_enum_publishes_integer_labels():
    eligibility = us_latest.get_variable("il_personal_exemption_eligibility_status")

    assert [
        (enum_value.value, enum_value.label) for enum_value in eligibility.enum_values
    ] == [("BOTH_ELIGIBLE", 1), ("PARTIALLY_ELIGIBLE", 2), ("NOT_ELIGIBLE", 3)]
    assert all(type(enum_value.label) is int for enum_value in eligibility.enum_values)


def _components_parameter_tree() -> CoreParameterNode:
    return CoreParameterNode(
        "",
        data={
            "gov": {
                "example": {
                    "components": {
                        "description": "Income components, which change in 2026",
                        "values": {
                            "2020-01-01": ["wages"],
                            "2026-01-01": ["wages", "tips"],
                        },
                    },
                    "deductions": {
                        "description": "Deductions",
                        "values": {"2020-01-01": ["pension_contributions"]},
                    },
                }
            }
        },
    )


def _summed_core_variable(name: str, adds, subtracts) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        label=name.replace("_", " ").capitalize(),
        entity=SimpleNamespace(key="person"),
        documentation=None,
        value_type=float,
        default_value=0.0,
        possible_values=None,
        adds=adds,
        subtracts=subtracts,
    )


def test_populate_variables_records_parameter_paths_named_by_adds_and_subtracts():
    model = _model_version()
    parameter_named = _summed_core_variable(
        "net_income", "gov.example.components", "gov.example.deductions"
    )
    variable_named = _summed_core_variable("gross_income", ["wages", "tips"], None)
    system = SimpleNamespace(
        variables={
            parameter_named.name: parameter_named,
            variable_named.name: variable_named,
        },
        parameters=_components_parameter_tree(),
    )

    MicrosimulationModelVersion._populate_variables(model, system)

    net_income = model.get_variable("net_income")
    assert net_income.adds_parameter_path == "gov.example.components"
    assert net_income.subtracts_parameter_path == "gov.example.deductions"
    # The lists resolved as of 2025-01-01 are unchanged for existing users.
    assert net_income.adds == ["wages"]
    assert net_income.subtracts == ["pension_contributions"]
    assert json.loads(
        net_income.model_dump_json(
            include={"adds_parameter_path", "subtracts_parameter_path"}
        )
    ) == {
        "adds_parameter_path": "gov.example.components",
        "subtracts_parameter_path": "gov.example.deductions",
    }
    gross_income = model.get_variable("gross_income")
    assert gross_income.adds == ["wages", "tips"]
    assert gross_income.adds_parameter_path is None
    assert gross_income.subtracts_parameter_path is None


def test_parameter_path_is_published_when_the_parameter_cannot_be_resolved():
    model = _model_version()
    core_variable = _summed_core_variable("net_income", "gov.example.missing", None)
    system = SimpleNamespace(
        variables={core_variable.name: core_variable},
        parameters=_components_parameter_tree(),
    )

    MicrosimulationModelVersion._populate_variables(model, system)

    variable = model.get_variable("net_income")
    assert variable.adds is None
    assert variable.adds_parameter_path == "gov.example.missing"


@pytest.mark.parametrize(
    ("model", "country_system_module"),
    [(uk_latest, "policyengine_uk.system"), (us_latest, "policyengine_us.system")],
    ids=["uk", "us"],
)
def test_country_models_publish_every_parameter_named_by_adds_or_subtracts(
    model, country_system_module
):
    country_system = importlib.import_module(country_system_module).system

    for name, core_variable in country_system.variables.items():
        variable = model.get_variable(name)
        for attribute in ("adds", "subtracts"):
            declared = getattr(core_variable, attribute, None)
            published_path = getattr(variable, f"{attribute}_parameter_path")
            if isinstance(declared, str):
                assert published_path == declared, (name, attribute)
                assert published_path in model.parameters_by_name, (name, attribute)
            else:
                assert published_path is None, (name, attribute)


def test_us_model_publishes_parameter_named_parts():
    adds_paths = [
        variable for variable in us_latest.variables if variable.adds_parameter_path
    ]
    subtracts_paths = [
        variable
        for variable in us_latest.variables
        if variable.subtracts_parameter_path
    ]

    assert len(adds_paths) >= 200
    assert len(subtracts_paths) >= 1
    household_state_benefits = us_latest.get_variable("household_state_benefits")
    assert (
        household_state_benefits.adds_parameter_path
        == "gov.household.household_state_benefits"
    )
    assert isinstance(household_state_benefits.adds, list)
