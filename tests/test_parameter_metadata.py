"""Tests for the economy and household flags each parameter publishes."""

import importlib
import json
from types import SimpleNamespace

import pytest
from policyengine_core.parameters import Parameter as CoreParameter
from policyengine_core.parameters import ParameterNode as CoreParameterNode

from policyengine.core import Parameter, TaxBenefitModel, TaxBenefitModelVersion
from policyengine.tax_benefit_models.common.model_version import (
    MicrosimulationModelVersion,
)


def _model_version() -> TaxBenefitModelVersion:
    return TaxBenefitModelVersion(
        id="test@1",
        model=TaxBenefitModel(id="test", name="Test"),
        version="1",
    )


@pytest.fixture(params=["uk", "us"])
def country(request) -> SimpleNamespace:
    """The country's published model version and its core tax-benefit system.

    Skips when the country package is not installed. The model is imported
    here, after that check, because the country module defines it only when
    the package is installed.
    """
    country_id = request.param
    country_system = pytest.importorskip(f"policyengine_{country_id}.system").system
    country_module = importlib.import_module(
        f"policyengine.tax_benefit_models.{country_id}"
    )
    return SimpleNamespace(
        id=country_id,
        model=getattr(country_module, f"{country_id}_latest"),
        system=country_system,
    )


def _flagged_parameter(metadata: dict) -> dict:
    return {
        "description": "An example amount",
        "values": {"2020-01-01": 100},
        "metadata": metadata,
    }


def test_populate_parameters_records_economy_and_household_flags():
    model = _model_version()
    parameters = CoreParameterNode(
        "",
        data={
            "gov": {
                "example": {
                    "economy_only": _flagged_parameter({"household": False}),
                    "household_only": _flagged_parameter({"economy": False}),
                    "unflagged": _flagged_parameter({}),
                }
            }
        },
    )
    system = SimpleNamespace(parameters=parameters, variables={})

    MicrosimulationModelVersion._populate_parameters(model, system)

    economy_only = model.get_parameter("gov.example.economy_only")
    assert (economy_only.economy, economy_only.household) == (True, False)
    household_only = model.get_parameter("gov.example.household_only")
    assert (household_only.economy, household_only.household) == (False, True)
    # As in the country packages' metadata, an absent flag means the
    # parameter is offered.
    unflagged = model.get_parameter("gov.example.unflagged")
    assert (unflagged.economy, unflagged.household) == (True, True)
    assert json.loads(
        household_only.model_dump_json(include={"economy", "household"})
    ) == {
        "economy": False,
        "household": True,
    }


def test_parameter_flags_default_to_offered():
    model = _model_version()
    manually_built = Parameter(
        name="gov.example.amount", tax_benefit_model_version=model
    )

    assert manually_built.economy is True
    assert manually_built.household is True


def test_country_models_publish_each_parameters_flags(country):
    model = country.model
    country_system = country.system

    for core_parameter in country_system.parameters.get_descendants():
        if not isinstance(core_parameter, CoreParameter):
            continue
        parameter = model.get_parameter(core_parameter.name)
        assert parameter.economy is bool(
            core_parameter.metadata.get("economy", True)
        ), core_parameter.name
        assert parameter.household is bool(
            core_parameter.metadata.get("household", True)
        ), core_parameter.name
    assert any(not parameter.economy for parameter in model.parameters)
    assert any(not parameter.household for parameter in model.parameters)
