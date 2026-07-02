"""Belgium population microsimulation through the Axiom rules engine.

Runs the calibrated populace-be pilot dataset (populace-us support records
reweighted to Statbel/SPF/ONSS/ONEM targets from PolicyEngine/ledger)
through the rulespec-be composed worker pipeline, and scores the aggregates
against Belgian administrative facts.

This is a demonstration of the engine channel, not a certified Belgian
model: the support records are American, and only worker SSC and individual
PIT are encoded so far.

Usage::

    POPULACE_BE_DATASET=.../populace_be_pilot_2026.h5 \\
    RULESPEC_BE_ROOT=.../rulespec-be \\
    uv run python examples/belgium_axiom_pilot.py
"""

import os

from policyengine.core.simulation import Simulation
from policyengine.tax_benefit_models.be import (
    EMPLOYEE_SSC,
    PIT_BEFORE_WITHHOLDING,
    AxiomBelgiumPilot,
    PopulaceBelgiumDataset,
)

DATASET = os.environ["POPULACE_BE_DATASET"]
RULESPEC = os.environ.get("RULESPEC_BE_ROOT", "~/TheAxiomFoundation/rulespec-be")

# Ledger facts (PolicyEngine/ledger, Belgian publisher packages)
ONSS_WORKER_CONTRIBUTIONS_2024 = 20_836_582_673
SPF_PIT_BEFORE_WITHHOLDING_2023 = 62_840_116_134

dataset = PopulaceBelgiumDataset(
    name="populace-be-pilot",
    description="populace-us support reweighted to Belgian ledger targets",
    filepath=DATASET,
    year=2026,
)
model_version = AxiomBelgiumPilot(rulespec_root=RULESPEC, period=2025)

simulation = Simulation(dataset=dataset, tax_benefit_model_version=model_version)
simulation.run()

person = simulation.output_dataset.data.person
ssc = person[EMPLOYEE_SSC].sum()
pit = person[PIT_BEFORE_WITHHOLDING].sum()

print("Belgium pilot (Axiom engine over populace-be, worker slice)")
print(f"  employee SSC          EUR {ssc / 1e9:6.2f}B  (ONSS 2024: EUR 20.84B)")
print(
    f"  PIT before withholding EUR {pit / 1e9:6.2f}B  (SPF 2023, all PIT: EUR 62.84B)"
)
print(f"  SSC vs ONSS ratio     {ssc / ONSS_WORKER_CONTRIBUTIONS_2024:.3f}")
print(
    f"  PIT vs SPF ratio      {pit / SPF_PIT_BEFORE_WITHHOLDING_2023:.3f} (worker slice only)"
)
