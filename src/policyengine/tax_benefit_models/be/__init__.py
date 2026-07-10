"""Belgium pilot: Axiom rules engine over populace entity tables.

The first non-policyengine-core country in policyengine.py. Statutes are
encoded as RuleSpec YAML (TheAxiomFoundation/rulespec-be), compiled and
executed by axiom-rules-engine, and driven over populace-be entity tables.
See ``examples/belgium_axiom_pilot.py`` for the end-to-end population run
and ``model.py`` for scope and source-install requirements.
"""

from .datasets import BEYearData, PopulaceBelgiumDataset
from .model import (
    EMPLOYEE_SSC,
    PIT_BEFORE_WITHHOLDING,
    REMUNERATION,
    AxiomBelgium,
    AxiomBelgiumPilot,
    be_model,
)

__all__ = [
    "AxiomBelgium",
    "AxiomBelgiumPilot",
    "BEYearData",
    "EMPLOYEE_SSC",
    "PIT_BEFORE_WITHHOLDING",
    "PopulaceBelgiumDataset",
    "REMUNERATION",
    "be_model",
]
