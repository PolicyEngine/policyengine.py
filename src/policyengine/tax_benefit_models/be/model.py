"""Axiom-backed Belgium pilot model version.

Unlike the US and UK model versions, Belgium runs on the Axiom rules
engine: statutes encoded as RuleSpec YAML in TheAxiomFoundation/rulespec-be,
compiled and executed by ``axiom-rules-engine``, and driven over populace
entity tables through the ``populace-frame`` Axiom adapter. There is no
policyengine-core country package and no certified release manifest, so this
version subclasses ``TaxBenefitModelVersion`` directly and stays outside the
managed-release machinery.

Requirements (neither is on PyPI yet):

- ``populace-frame`` from PolicyEngine/populace (``packages/populace-frame``)
- ``axiom-rules-engine`` from TheAxiomFoundation/axiom-rules-engine (PyO3
  dense extension)
- a checkout of TheAxiomFoundation/rulespec-be, passed as ``rulespec_root``

Scope: the composed worker pipeline only — employee social security
contributions (13.07 percent ordinary worker contribution) and personal
income tax before withholding for wage earners under individual assessment.
Dependants, joint assessment, other income categories, and employment tax
reductions are not yet encoded (TheAxiomFoundation/rulespec-be#1).
"""

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Optional, Union

import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import TaxBenefitModel
from policyengine.core.tax_benefit_model_version import TaxBenefitModelVersion

from .datasets import BEYearData, PopulaceBelgiumDataset

if TYPE_CHECKING:
    from policyengine.core.simulation import Simulation

PILOT_MODULE = "be/statutes/income_tax/individual/pilot_worker_oracle_pipeline.yaml"
REMUNERATION = "belgium_pit_article_23_worker_remuneration"
EMPLOYEE_SSC = "belgium_employee_social_security_ordinary_worker_contribution"
PIT_BEFORE_WITHHOLDING = "belgium_pit_pilot_federal_and_local_tax_before_withholding"

#: Pipeline inputs the pilot supplies as scalars when the dataset does not
#: carry them (rulespec stage boundaries are supplied inputs by convention).
#: The work-bonus reference wage bridges 0 -> worker remuneration inside the
#: pipeline, so the scalar default keeps the statutory low-wage bonus active.
SUPPLIED_DEFAULTS: dict[str, Union[float, bool]] = {
    "belgium_pit_article_466_tax_share_on_nonprofessional_movable_income": 0.0,
    "belgium_pit_article_466bis_hypothetical_total_tax_if_treaty_exempt_foreign_professional_income_were_belgian": 0.0,
    "belgium_pit_article_466bis_treaty_exempt_foreign_professional_income_base_applies": False,
    "belgium_worker_work_bonus_supplied_reference_annual_remuneration": 0.0,
    "belgium_pit_communal_additional_tax_rate": 0.0,
    "belgium_pit_agglomeration_additional_tax_rate": 0.0,
}


class AxiomBelgium(TaxBenefitModel):
    id: str = "axiom-rulespec-be"
    description: str = (
        "Belgium tax rules encoded as RuleSpec (TheAxiomFoundation/rulespec-be), "
        "executed by the Axiom rules engine over populace entity tables."
    )


be_model = AxiomBelgium()


class AxiomBelgiumPilot(TaxBenefitModelVersion):
    """Pilot Belgium model version: worker SSC and PIT via Axiom."""

    country_code: ClassVar[str] = "be"

    rulespec_root: str
    period: Optional[int] = None
    output_variables: list[str] = [EMPLOYEE_SSC, PIT_BEFORE_WITHHOLDING]
    communal_additional_tax_rate: float = 0.0

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("model", be_model)
        kwargs.setdefault("version", "0.1.0-pilot")
        super().__init__(**kwargs)

    def run(self, simulation: "Simulation") -> "Simulation":
        try:
            from populace.frame import Frame, WeightKind, Weights
            from populace.frame.adapters.axiom import BE_SCHEMA, AxiomEngine
        except ImportError as error:
            raise ImportError(
                "The Belgium pilot needs populace-frame (PolicyEngine/populace, "
                "packages/populace-frame) and axiom-rules-engine "
                "(TheAxiomFoundation/axiom-rules-engine); neither is on PyPI "
                "yet, install both from source."
            ) from error

        module = Path(self.rulespec_root).expanduser() / PILOT_MODULE
        if not module.exists():
            raise FileNotFoundError(
                f"rulespec-be pilot module not found at {module}; pass a "
                "checkout of TheAxiomFoundation/rulespec-be as rulespec_root."
            )

        dataset = simulation.dataset
        assert isinstance(dataset, PopulaceBelgiumDataset)
        if dataset.data is None:
            dataset.load()
        assert dataset.data is not None

        person = pd.DataFrame(dataset.data.person).copy()
        household = pd.DataFrame(dataset.data.household).copy()
        for name, value in SUPPLIED_DEFAULTS.items():
            if name not in person.columns:
                person[name] = value
        person["belgium_pit_communal_additional_tax_rate"] = (
            self.communal_additional_tax_rate
        )

        weights = {
            "household": Weights(
                values=household["household_weight"].to_numpy(),
                kind=WeightKind.CALIBRATED,
            )
        }
        # The frame kernel owns weight columns (typed Weights vectors);
        # they stay on the pe.py-side MicroDataFrames only.
        frame = Frame(
            {
                "person": person.drop(columns=["person_weight"]),
                "household": household.drop(columns=["household_weight"]),
            },
            BE_SCHEMA,
            weights,
        )
        engine = AxiomEngine(str(module))
        outputs = engine.materialize(
            frame, self.output_variables, self.period or dataset.year
        )
        for name, values in outputs.items():
            person[name] = values

        simulation.output_dataset = PopulaceBelgiumDataset(
            id=simulation.id,
            name=dataset.name,
            description=dataset.description,
            filepath=dataset.filepath,
            year=dataset.year,
            is_output_dataset=True,
            data=BEYearData(
                person=MicroDataFrame(person, weights="person_weight"),
                household=MicroDataFrame(household, weights="household_weight"),
            ),
        )
        return simulation

    def save(self, simulation: "Simulation") -> None:
        """Pilot simulations are recomputed, not persisted."""

    def load(self, simulation: "Simulation") -> None:
        raise FileNotFoundError("Pilot simulations are recomputed, not persisted.")
