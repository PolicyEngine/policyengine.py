"""Public Microcosm names retain their previous import aliases."""

import runpy
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from policyengine.provenance.certification import (
    MicrocosmDataProducerCertificationStrategy,
    certification_strategy,
)


@pytest.mark.parametrize(
    "module_name,current_name,legacy_name",
    [
        (
            "policyengine.tax_benefit_models.be",
            "MicrocosmBelgiumDataset",
            "PopulaceBelgiumDataset",  # compat: populace alias, remove after 6.17.0
        ),
        (
            "policyengine.tax_benefit_models.be.datasets",
            "MicrocosmBelgiumDataset",
            "PopulaceBelgiumDataset",  # compat: populace alias, remove after 6.17.0
        ),
        (
            "policyengine.tax_benefit_models.be.model",
            "MicrocosmBelgiumDataset",
            "PopulaceBelgiumDataset",  # compat: populace alias, remove after 6.17.0
        ),
        (
            "policyengine.provenance.certification",
            "MicrocosmDataProducerCertificationStrategy",
            "PopulaceDataProducerCertificationStrategy",  # compat: populace alias, remove after 6.17.0
        ),
        (
            "policyengine.provenance.certification",
            "MICROCOSM_US_SOURCE_COVERAGE_FILE",
            "POPULACE_US_SOURCE_COVERAGE_FILE",  # compat: populace alias, remove after 6.17.0
        ),
        (
            "policyengine.provenance.certification",
            "MICROCOSM_DATA_PACKAGES",
            "POPULACE_DATA_PACKAGES",  # compat: populace alias, remove after 6.17.0
        ),
        (
            "policyengine.provenance.certification",
            "MICROCOSM_RELEASE_REPOS",
            "POPULACE_RELEASE_REPOS",  # compat: populace alias, remove after 6.17.0
        ),
        (
            "policyengine.tax_benefit_models.us.legacy_spm.registry",
            "MICROCOSM_US_2024_ACS_LOCAL_BUILD_O",
            "POPULACE_US_2024_ACS_LOCAL_BUILD_O",  # compat: populace alias, remove after 6.17.0
        ),
        (
            "policyengine.tax_benefit_models.us.legacy_spm.registry",
            "MICROCOSM_US_2024_ACS_LOCAL_MICROCOSM_1263",
            "POPULACE_US_2024_ACS_LOCAL_MICROCOSM_1263",  # compat: populace alias, remove after 6.17.0
        ),
    ],
)
def test_previous_public_names_resolve_to_current_objects(
    module_name, current_name, legacy_name
):
    module = import_module(module_name)

    assert getattr(module, legacy_name) is getattr(module, current_name)


@pytest.mark.parametrize(
    "country,data_producer",
    [("uk", None), ("uk", "populace"), ("us", "populace")],
)
def test_current_certification_strategy_preserves_the_published_producer(
    country, data_producer
):
    strategy = certification_strategy(country, data_producer)

    assert type(strategy) is MicrocosmDataProducerCertificationStrategy
    assert strategy.data_producer == "populace"


@pytest.mark.parametrize(
    "current_path,legacy_path,expected_path",
    [
        ("current.h5", None, "current.h5"),
        (None, "legacy.h5", "legacy.h5"),
        ("current.h5", "legacy.h5", "current.h5"),
    ],
)
def test_belgium_example_accepts_both_dataset_environment_names(
    monkeypatch, current_path, legacy_path, expected_path
):
    be = import_module("policyengine.tax_benefit_models.be")
    simulation_module = import_module("policyengine.core.simulation")
    legacy_env_name = (
        "POPULACE_BE_DATASET"  # compat: populace alias, remove after 6.17.0
    )
    for name, value in (
        ("MICROCOSM_BE_DATASET", current_path),
        (legacy_env_name, legacy_path),
    ):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    monkeypatch.setenv("RULESPEC_BE_ROOT", "test-rules")
    dataset_type = Mock()
    model_type = Mock(return_value=SimpleNamespace(version="test-model"))
    output = SimpleNamespace(
        year=2026,
        policy_period=2025,
        data=SimpleNamespace(
            person={
                be.EMPLOYEE_SSC: np.asarray([0.0]),
                be.PIT_BEFORE_WITHHOLDING: np.asarray([0.0]),
            }
        ),
    )
    simulation = Mock(output_dataset=output)
    monkeypatch.setattr(be, "MicrocosmBelgiumDataset", dataset_type)
    monkeypatch.setattr(be, "AxiomBelgiumPilot", model_type)
    monkeypatch.setattr(simulation_module, "Simulation", Mock(return_value=simulation))

    runpy.run_path(
        Path(__file__).resolve().parents[1] / "examples/belgium_axiom_pilot.py"
    )

    assert dataset_type.call_args.kwargs["filepath"] == expected_path
    simulation.run.assert_called_once_with()
