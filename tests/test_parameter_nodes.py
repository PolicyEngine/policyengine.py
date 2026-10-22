"""Tests for public parameter-node projection from country models."""

import importlib
from types import SimpleNamespace

import pytest
from policyengine_core.parameters import ParameterNode as CoreParameterNode
from policyengine_core.parameters import ParameterScale as CoreParameterScale

from policyengine.core import TaxBenefitModel, TaxBenefitModelVersion
from policyengine.tax_benefit_models.common.model_version import (
    MicrosimulationModelVersion,
)
from policyengine.tax_benefit_models.uk import uk_latest
from policyengine.tax_benefit_models.us import us_latest


def _model_version() -> TaxBenefitModelVersion:
    return TaxBenefitModelVersion(
        id="test@1",
        model=TaxBenefitModel(id="test", name="Test"),
        version="1",
    )


def test_populate_parameters_excludes_empty_organizational_nodes():
    populated_node = CoreParameterNode(
        "gov.example",
        data={
            "amount": {
                "description": "Example amount",
                "values": {"2026-01-01": 10},
            }
        },
    )
    empty_node = CoreParameterNode("generated_artifacts", data={})
    descendants = [populated_node, empty_node]
    system = SimpleNamespace(
        parameters=SimpleNamespace(
            get_descendants=lambda: iter(descendants),
        )
    )
    model = _model_version()

    MicrosimulationModelVersion._populate_parameters(model, system)

    assert [node.name for node in model.parameter_nodes] == ["gov.example"]
    assert set(model.parameter_nodes_by_name) == {"gov.example"}


@pytest.mark.parametrize("model", [uk_latest, us_latest], ids=["uk", "us"])
def test_country_models_do_not_expose_python_cache_nodes(model):
    assert all(
        "__pycache__" not in node.name.split(".") for node in model.parameter_nodes
    )
    assert all(
        "__pycache__" not in name.split(".") for name in model.parameter_nodes_by_name
    )


def _bracket(rate: float, threshold: float) -> dict:
    return {
        "rate": {"values": {"2020-01-01": rate}},
        "threshold": {"values": {"2020-01-01": threshold}},
    }


def _system_with_bracket_schedules() -> SimpleNamespace:
    parameters = CoreParameterNode(
        "",
        data={
            "gov": {
                "tax": {
                    "rates": {
                        "description": "Income tax rates by band",
                        "metadata": {
                            "label": "Income tax rates",
                            "type": "marginal_rate",
                        },
                        "brackets": [_bracket(0.1, 0), _bracket(0.2, 1_000)],
                    },
                    "unlabelled_rates": {
                        "description": "A schedule with no stored label",
                        "metadata": {"type": "marginal_rate"},
                        "brackets": [_bracket(0.05, 0)],
                    },
                }
            }
        },
    )
    return SimpleNamespace(parameters=parameters, variables={})


def test_populate_parameters_publishes_bracket_schedules_as_labelled_nodes():
    model = _model_version()

    MicrosimulationModelVersion._populate_parameters(
        model, _system_with_bracket_schedules()
    )

    schedule = model.get_parameter_node("gov.tax.rates")
    assert schedule.label == "Income tax rates"
    assert schedule.description == "Income tax rates by band"
    assert schedule.id == "test@1-gov.tax.rates"
    assert model.get_parameter_node("gov.tax.unlabelled_rates").label is None
    node_names = [node.name for node in model.parameter_nodes]
    # Each schedule precedes its brackets, which stay nodes of their own.
    assert node_names.index("gov.tax.rates") < node_names.index("gov.tax.rates[0]")
    assert {"gov.tax.rates[0]", "gov.tax.rates[1]"} <= set(node_names)
    assert model.get_parameter("gov.tax.rates[1].rate").label == (
        "Income tax rates (bracket 2 rate)"
    )


def test_populate_parameters_leaves_out_bracket_schedules_without_brackets():
    parameters = CoreParameterNode(
        "",
        data={
            "gov": {
                "tax": {
                    "empty_rates": {
                        "description": "A schedule whose brackets are not set yet",
                        "metadata": {"label": "Empty rates", "type": "marginal_rate"},
                        "brackets": [],
                    },
                    "rates": {
                        "metadata": {"label": "Income tax rates"},
                        "brackets": [_bracket(0.1, 0)],
                    },
                }
            }
        },
    )
    assert isinstance(parameters.gov.tax.empty_rates, CoreParameterScale)
    model = _model_version()

    MicrosimulationModelVersion._populate_parameters(
        model, SimpleNamespace(parameters=parameters, variables={})
    )

    assert "gov.tax.empty_rates" not in model.parameter_nodes_by_name
    assert all(node.name != "gov.tax.empty_rates" for node in model.parameter_nodes)
    assert "gov.tax.rates" in model.parameter_nodes_by_name


@pytest.mark.parametrize(
    ("model", "country_system_module"),
    [(uk_latest, "policyengine_uk.system"), (us_latest, "policyengine_us.system")],
    ids=["uk", "us"],
)
def test_country_models_publish_every_bracket_schedule(model, country_system_module):
    country_system = importlib.import_module(country_system_module).system

    schedules = [
        core_parameter
        for core_parameter in country_system.parameters.get_descendants()
        if isinstance(core_parameter, CoreParameterScale) and core_parameter.brackets
    ]
    assert schedules
    for core_schedule in schedules:
        schedule = model.get_parameter_node(core_schedule.name)
        assert schedule.label == core_schedule.metadata.get("label"), core_schedule.name
        assert schedule.description == core_schedule.description


def test_uk_income_tax_schedule_is_a_labelled_node():
    schedule = uk_latest.get_parameter_node("gov.hmrc.income_tax.rates.uk")

    assert schedule.label == "Income Tax main rates"
    assert "gov.hmrc.income_tax.rates.uk[0]" in uk_latest.parameter_nodes_by_name


@pytest.mark.parametrize(
    ("model", "schedule_name", "stored_label"),
    [
        (uk_latest, "gov.hmrc.income_tax.rates.uk", "Income Tax main rates"),
        (uk_latest, "gov.hmrc.income_tax.rates.dividends", None),
        (us_latest, "gov.irs.income.bracket.rates", "Individual income tax rates"),
        (us_latest, "gov.contrib.ubi_center.basic_income.amount.person.by_age", None),
    ],
    ids=["uk-labelled", "uk-unlabelled", "us-labelled", "us-unlabelled"],
)
def test_country_schedules_publish_their_stored_label_or_none(
    model, schedule_name, stored_label
):
    # A schedule without a stored label publishes None; consumers generate
    # one from its name.
    assert model.get_parameter_node(schedule_name).label == stored_label
