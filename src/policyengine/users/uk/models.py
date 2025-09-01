from policyengine.models import (
    Policy,
    Dynamics,
    Simulation as GeneralSimulation,
    Dataset as GeneralDataset,
    ReportElementDataItem,
    ReportElement,
    Report,
    Variable,
    Parameter,
    ParameterValue,
)
from pydantic import BaseModel
from typing import Any, Optional, List
from policyengine_uk import Simulation as PolicyEngineUKSimulation
from policyengine_uk.model_api import Scenario as PolicyEngineUKScenario
from policyengine_uk.data.dataset_schema import (
    UKSingleYearDataset as PolicyEngineUKSingleYearDataset,
)
import pandas as pd
import numpy as np
from microdf import MicroDataFrame
from policyengine.utils.parametric_reforms import apply_parametric_reform


class UKSingleYearDataset(BaseModel):
    person: Any  # DataFrame
    benunit: Any
    household: Any

    def copy(self):
        return UKSingleYearDataset(
            person=self.person.copy(),
            benunit=self.benunit.copy(),
            household=self.household.copy(),
        )


class Dataset(GeneralDataset):
    year: int
    name: Optional[str] = None
    data: UKSingleYearDataset
    version: Optional[str] = None


class Simulation(GeneralSimulation):
    year: int
    dataset: Dataset
    policy: Policy
    dynamics: Dynamics
    version: Optional[str] = None
    output_data: Optional[Dataset] = None

    def _get_simulation(self):
        parametric_policy = apply_parametric_reform(self.policy.parameter_values or [])
        parametric_dynamics = apply_parametric_reform(
            self.dynamics.parameter_values or []
        )

        def modifier(sim):
            parametric_policy.simulation_modifier(sim)
            if self.policy.simulation_modifier:
                self.policy.simulation_modifier(sim)

            parametric_dynamics.simulation_modifier(sim)
            if self.dynamics.simulation_modifier:
                self.dynamics.simulation_modifier(sim)

        scenario = PolicyEngineUKScenario(simulation_modifier=modifier)
        return PolicyEngineUKSimulation(
            dataset=PolicyEngineUKSingleYearDataset(
                person=self.dataset.data.person,
                benunit=self.dataset.data.benunit,
                household=self.dataset.data.household,
                fiscal_year=self.year,
            ),
            scenario=scenario,
        )

    def run(self) -> UKSingleYearDataset:
        sim = self._get_simulation()

        output_dataset = Dataset(
            year=self.year,
            data=UKSingleYearDataset(
                person=self.dataset.data.person.copy(),
                benunit=self.dataset.data.benunit.copy(),
                household=self.dataset.data.household.copy(),
            ),
        )
        output_dataset.data.household["gov_tax"] = sim.calculate("gov_tax", self.year)
        output_dataset.data.household["gov_spending"] = sim.calculate(
            "gov_spending", self.year
        )
        output_dataset.data.household["gov_balance"] = sim.calculate(
            "gov_balance", self.year
        )

        self.output_data = output_dataset

        return output_dataset


class AggregateChange(ReportElementDataItem):
    variable: str
    baseline: float
    reform: float
    difference: float
    report_element: "AggregateChangeReportElement"


class AggregateChangeReportElement(ReportElement):
    baseline_simulation: Simulation
    reform_simulation: Simulation
    variables: List[str] = ["gov_balance"]

    def run(self):
        # Calculate aggregate changes between baseline and reform simulations
        baseline_data = self.baseline_simulation.output_data.data
        reform_data = self.reform_simulation.output_data.data

        changes = []
        for variable in self.variables:
            weights = baseline_data.household["household_weight"]
            baseline_value = (weights * baseline_data.household[variable]).sum()
            reform_value = (weights * reform_data.household[variable]).sum()
            changes.append(
                AggregateChange(
                    variable=variable,
                    baseline=baseline_value,
                    reform=reform_value,
                    difference=reform_value - baseline_value,
                    report_element=self,
                )
            )

        self.data_items = changes

        return changes


def create_example_uk_dataset() -> UKSingleYearDataset:
    person, benunit, household = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    person["person_id"] = np.arange(1, 100)
    person["person_benunit_id"] = np.arange(1, 100)
    person["person_household_id"] = np.arange(1, 100)
    benunit["benunit_id"] = np.arange(1, 100)
    household["household_id"] = np.arange(1, 100)

    # Earnings normally distributed around 30k
    person["employment_income"] = np.random.normal(30_000, 5_000)

    household["household_weight"] = 66e6 / 100
    household["region"] = "LONDON"
    household["council_tax"] = 1_000
    household["tenure_type"] = "OWNED_OUTRIGHT"
    household["rent"] = 12_000

    return Dataset(
        year=2023,
        name="example_uk_2023",
        data=UKSingleYearDataset(
            person=person,
            benunit=benunit,
            household=household,
        ),
    )


example_uk_dataset = create_example_uk_dataset()

current_law = Policy(
    name="current law",
    description="Current tax and benefit system in the UK.",
)

no_behavioural_responses = Dynamics(
    name="default dynamics",
    description="Default dynamics for the UK tax and benefit system.",
)
