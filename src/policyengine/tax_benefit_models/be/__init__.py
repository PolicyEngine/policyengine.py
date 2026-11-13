"""Belgium pilot: Axiom rules engine over Microcosm entity tables.

The first non-policyengine-core country in policyengine.py. Statutes are
encoded as RuleSpec YAML (TheAxiomFoundation/rulespec-be), compiled and
executed by axiom-rules-engine, and driven over Microcosm-BE entity tables.
See ``examples/belgium_axiom_pilot.py`` for the end-to-end population run
and ``model.py`` for scope and source-install requirements.
"""

from .datasets import BEYearData, MicrocosmBelgiumDataset
from .model import (
    EMPLOYEE_SSC,
    PIT_BEFORE_WITHHOLDING,
    REMUNERATION,
    AxiomBelgium,
    AxiomBelgiumPilot,
    be_model,
)

PopulaceBelgiumDataset = (  # compat: populace alias, remove after 6.17.0
    MicrocosmBelgiumDataset
)

__all__ = [
    "AxiomBelgium",
    "AxiomBelgiumPilot",
    "BEYearData",
    "EMPLOYEE_SSC",
    "PIT_BEFORE_WITHHOLDING",
    "MicrocosmBelgiumDataset",
    "PopulaceBelgiumDataset",  # compat: populace alias, remove after 6.17.0
    "REMUNERATION",
    "be_model",
]
