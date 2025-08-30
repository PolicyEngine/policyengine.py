from policyengine.models import *
from policyengine_uk import Simulation as PolicyEngineUKSimulation
from policyengine_uk.model_api import Scenario as PolicyEngineUKScenario
from policyengine_uk.data.dataset_schema import (
    UKSingleYearDataset as PolicyEngineUKSingleYearDataset,
)
import pandas as pd
import numpy as np


class UKSingleYearDataset(Dataset):
    year: int
    person: Optional[Any] = None
    benunit: Optional[Any] = None
    household: Optional[Any] = None

    def copy(self):
        return UKSingleYearDataset(
            name=self.name,
            year=self.year,
            person=self.person.copy(),
            benunit=self.benunit.copy(),
            household=self.household.copy(),
        )


class UKSingleYearSimulation(Simulation):
    year: int
    data: UKSingleYearDataset

    def _get_simulation(self):
        return PolicyEngineUKSimulation(
            dataset=PolicyEngineUKSingleYearDataset(
                person=self.data.person,
                benunit=self.data.benunit,
                household=self.data.household,
                fiscal_year=self.year,
            ),
            scenario=PolicyEngineUKScenario(
                parameter_changes=self.policy.parameter_values,
                simulation_modifier=self.policy.simulation_modifier,
            )
            + PolicyEngineUKScenario(
                parameter_changes=self.dynamics.parameter_values,
                simulation_modifier=self.dynamics.simulation_modifier,
            ),
        )

    def run(self) -> UKSingleYearDataset:
        sim = self._get_simulation()

        output_dataset = self.data.copy()
        output_dataset.household["gov_tax"] = sim.calculate("gov_tax", self.year)
        output_dataset.household["gov_spending"] = sim.calculate(
            "gov_spending", self.year
        )
        output_dataset.household["gov_balance"] = sim.calculate(
            "gov_balance", self.year
        )

        self.output_dataset = output_dataset

        return output_dataset


class AggregateChange(ReportElementDataItem):
    variable: str
    baseline: float
    reform: float
    difference: float
    report_element: ReportElement


class AggregateChanges(ReportElement):
    baseline_dataset: UKSingleYearDataset
    reform_dataset: UKSingleYearDataset
    variables: List[str] = ["gov_tax", "gov_spending", "gov_balance"]

    def run(self):
        # Calculate aggregate changes between baseline and reform datasets
        baseline_data = self.baseline_dataset
        reform_data = self.reform_dataset

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

    return UKSingleYearDataset(
        name="example UK dataset",
        year=2023,
        person=person,
        benunit=benunit,
        household=household,
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
