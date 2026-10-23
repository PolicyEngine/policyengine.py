"""Tests for public parameter-node projection from country models."""

from types import SimpleNamespace

import pytest
from policyengine_core.parameters import ParameterNode as CoreParameterNode

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
