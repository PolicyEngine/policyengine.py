"""Country model versions for metadata tests, skipped when a package is missing.

``policyengine.tax_benefit_models.uk`` and ``.us`` define ``uk_latest`` and
``us_latest`` only when the country package is installed, so these fixtures
check for the package first and import the model version afterwards.
"""

import importlib
from types import SimpleNamespace

import pytest

from policyengine.core import TaxBenefitModel, TaxBenefitModelVersion


def make_empty_model_version() -> TaxBenefitModelVersion:
    """A model version with no country package, for populating from stubs."""
    return TaxBenefitModelVersion(
        id="test@1",
        model=TaxBenefitModel(id="test", name="Test"),
        version="1",
    )


def load_country_model(country_id: str) -> SimpleNamespace:
    """Return a country's published model version and its core system.

    The result has ``country_id``, ``model_version`` (``uk_latest`` or
    ``us_latest``) and ``core_system`` (the country package's tax-benefit
    system). Skips the calling test when the country package is not installed.
    """
    core_system = pytest.importorskip(f"policyengine_{country_id}.system").system
    country_module = importlib.import_module(
        f"policyengine.tax_benefit_models.{country_id}"
    )
    return SimpleNamespace(
        country_id=country_id,
        model_version=getattr(country_module, f"{country_id}_latest"),
        core_system=core_system,
    )


@pytest.fixture(params=["uk", "us"])
def country_model(request) -> SimpleNamespace:
    """Each country's model version and core system, from load_country_model."""
    return load_country_model(request.param)


@pytest.fixture
def uk_country_model() -> SimpleNamespace:
    return load_country_model("uk")


@pytest.fixture
def us_country_model() -> SimpleNamespace:
    return load_country_model("us")
