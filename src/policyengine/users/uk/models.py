from policyengine.models import *
from policyengine_uk import Simulation as PolicyEngineUKSimulation
from policyengine_uk.model_api import Scenario as PolicyEngineUKScenario
from policyengine_uk.data.dataset_schema import (
    UKSingleYearDataset as PolicyEngineUKSingleYearDataset,
)
import pandas as pd


class UKSingleYearDataset(Dataset):
    person: Optional[Any] = None
    benunit: Optional[Any] = None
    household: Optional[Any] = None

    def load(self):  # can put helpers in the main bit to avoid this
        path = self.local_path

        # read tables from h5
        with pd.HDFStore(path, "r") as store:
            self.person = store["person"]
            self.benunit = store["benunit"]
            self.household = store["household"]

    def save(self):
        path = self.local_path

        # write tables to h5 using pandas
        with pd.HDFStore(path, "w") as store:
            store["person"] = self.person
            store["benunit"] = self.benunit
            store["household"] = self.household

    def copy(self):
        return UKSingleYearDataset(
            name=self.name,
            local_path=self.local_path,
            person=self.person.copy(),
            benunit=self.benunit.copy(),
            household=self.household.copy(),
        )


class UKSingleYearSimulation(Simulation):
    year: int
    data: UKSingleYearDataset
    _simulation: Optional[PolicyEngineUKSimulation] = None

    def run(self) -> UKSingleYearDataset:
        sim = PolicyEngineUKSimulation(
            dataset=PolicyEngineUKSingleYearDataset(
                person=self.data.person,
                benunit=self.data.benunit,
                household=self.data.household,
                fiscal_year=self.year,
            ),
            scenario=PolicyEngineUKScenario(
                parameter_changes=self.rules.parameter_changes,
                simulation_modifier=self.rules.simulation_modifier,
            )
            + PolicyEngineUKScenario(
                parameter_changes=self.dynamics.parameter_changes,
                simulation_modifier=self.dynamics.simulation_modifier,
            ),
        )
        self._simulation = sim

        output_dataset = self.data.copy()
        output_dataset.local_path = f"{self.data.name}_output_{self.year}_{self.rules.name}_{self.dynamics.name}.h5"
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
    name: str = "aggregate changes"
    baseline_dataset: UKSingleYearDataset
    reform_dataset: UKSingleYearDataset

    def run(self):
        # Calculate aggregate changes between baseline and reform datasets
        baseline_data = self.baseline_dataset
        reform_data = self.reform_dataset

        changes = []
        for variable in ["gov_tax", "gov_spending", "gov_balance"]:
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


efrs_2023_24 = UKSingleYearDataset(
    name="enhanced_frs_2023_24",
    local_path="/Users/nikhilwoodruff/policyengine/policyengine-uk-data/policyengine_uk_data/storage/enhanced_frs_2023_24.h5",
)

current_law = Rules(
    name="current law",
    description="Current tax and benefit system in the UK.",
)

default_dynamics = Dynamics(
    name="default dynamics",
    description="Default dynamics for the UK tax and benefit system.",
)
