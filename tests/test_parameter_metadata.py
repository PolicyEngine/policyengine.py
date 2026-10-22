"""Tests for the economy and household flags each parameter publishes."""

import json
from types import SimpleNamespace

from policyengine_core.parameters import Parameter as CoreParameter
from policyengine_core.parameters import ParameterNode as CoreParameterNode

from policyengine.core import Parameter
from policyengine.tax_benefit_models.common.model_version import (
    MicrosimulationModelVersion,
)
from tests.fixtures.country_model_fixtures import make_empty_model_version


def _flagged_parameter(metadata: dict) -> dict:
    return {
        "description": "An example amount",
        "values": {"2020-01-01": 100},
        "metadata": metadata,
    }


def test_populate_parameters_records_economy_and_household_flags():
    model = make_empty_model_version()
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
    model = make_empty_model_version()
    manually_built = Parameter(
        name="gov.example.amount", tax_benefit_model_version=model
    )

    assert manually_built.economy is True
    assert manually_built.household is True


def test_country_models_publish_each_parameters_flags(country_model):
    model = country_model.model_version
    country_system = country_model.core_system

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


# (economy, household) as the country packages' parameter files declare them,
# directly or through propagate_metadata_to_children.
PINNED_PARAMETER_FLAGS = {
    "uk": {
        "gov.dwp.ESA.eligibility.min_age": (False, True),
        "gov.hmrc.minimum_wage.apprentice": (False, False),
        "gov.hmrc.income_tax.rates.uk[0].rate": (True, True),
    },
    "us": {
        "gov.bls.cpi.cpi_u": (False, True),
        "gov.aca.slcsp.max_adult_age": (False, False),
        "gov.irs.income.bracket.rates.1": (True, True),
    },
}


def test_country_models_publish_pinned_parameter_flags(country_model):
    model = country_model.model_version
    published_flags = {
        name: (
            model.get_parameter(name).economy,
            model.get_parameter(name).household,
        )
        for name in PINNED_PARAMETER_FLAGS[country_model.country_id]
    }

    assert published_flags == PINNED_PARAMETER_FLAGS[country_model.country_id]
