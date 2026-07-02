"""Belgium pilot: Axiom engine over a tiny populace-style dataset.

Skips cleanly unless the source-only dependencies (populace-frame,
axiom-rules-engine) are importable and a rulespec-be checkout is available
via ``RULESPEC_BE_ROOT`` (or the default sibling path).
"""

import os
from importlib.util import find_spec
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RULESPEC_ROOT = Path(
    os.environ.get("RULESPEC_BE_ROOT", "~/TheAxiomFoundation/rulespec-be")
).expanduser()
PILOT_MODULE = (
    RULESPEC_ROOT
    / "be/statutes/income_tax/individual/pilot_worker_oracle_pipeline.yaml"
)

requires_axiom = pytest.mark.skipif(
    find_spec("populace") is None
    or find_spec("axiom_rules_engine") is None
    or not PILOT_MODULE.exists(),
    reason="needs populace-frame, axiom-rules-engine, and a rulespec-be checkout",
)

ORDINARY_WORKER_SSC_RATE = 0.1307  # arrete royal 28.11.1969, art. 19


@pytest.fixture
def pilot_dataset(tmp_path):
    from policyengine.tax_benefit_models.be import PopulaceBelgiumDataset

    person = pd.DataFrame(
        {
            "person_id": [1, 2, 3],
            "person_household_id": [1, 1, 2],
            "age": [40.0, 38.0, 30.0],
            "is_male": [True, False, False],
            "belgium_pit_article_23_worker_remuneration": [0.0, 30_000.0, 60_000.0],
            "person_weight": [1.0, 1.0, 1.0],
        }
    )
    household = pd.DataFrame({"household_id": [1, 2], "household_weight": [1.0, 1.0]})
    path = tmp_path / "populace_be_test.h5"
    person.to_hdf(path, key="person", mode="w")
    household.to_hdf(path, key="household")
    return PopulaceBelgiumDataset(
        name="populace-be-test",
        description="three-person fixture",
        filepath=str(path),
        year=2026,
    )


@requires_axiom
def test_pilot_run_computes_statutory_ssc_and_progressive_pit(pilot_dataset):
    from policyengine.core.simulation import Simulation
    from policyengine.tax_benefit_models.be import (
        EMPLOYEE_SSC,
        PIT_BEFORE_WITHHOLDING,
        REMUNERATION,
        AxiomBelgiumPilot,
    )

    version = AxiomBelgiumPilot(rulespec_root=str(RULESPEC_ROOT), period=2025)
    simulation = Simulation(dataset=pilot_dataset, tax_benefit_model_version=version)
    simulation.run()

    person = pd.DataFrame(simulation.output_dataset.data.person)
    gross = person[REMUNERATION].to_numpy()
    ssc = person[EMPLOYEE_SSC].to_numpy()
    pit = person[PIT_BEFORE_WITHHOLDING].to_numpy()

    np.testing.assert_allclose(ssc, gross * ORDINARY_WORKER_SSC_RATE, rtol=1e-9)
    assert pit[0] == 0.0
    assert 0.0 < pit[1] < pit[2]
    assert simulation.output_dataset.is_output_dataset


@requires_axiom
def test_pilot_weighted_aggregates_use_calibrated_weights(pilot_dataset):
    from policyengine.core.simulation import Simulation
    from policyengine.tax_benefit_models.be import EMPLOYEE_SSC, AxiomBelgiumPilot

    version = AxiomBelgiumPilot(rulespec_root=str(RULESPEC_ROOT), period=2025)
    simulation = Simulation(dataset=pilot_dataset, tax_benefit_model_version=version)
    simulation.run()

    person = simulation.output_dataset.data.person
    expected = 90_000.0 * ORDINARY_WORKER_SSC_RATE
    assert float(person[EMPLOYEE_SSC].sum()) == pytest.approx(expected, rel=1e-9)
