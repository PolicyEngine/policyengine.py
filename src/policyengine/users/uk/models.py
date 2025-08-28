from policyengine.models import *
from policyengine_uk import Simulation as PolicyEngineUKSimulation
from policyengine_uk.model_api import Scenario as PolicyEngineUKScenario
from policyengine_uk.data.dataset_schema import UKSingleYearDataset as PolicyEngineUKSingleYearDataset
import h5py
import pandas as pd

class UKSingleYearDataset(Dataset):
    person_df: Optional[Any] = None
    benunit_df: Optional[Any] = None
    household_df: Optional[Any] = None

    def load_from_local_path(self): # can put helpers in the main bit to avoid this
        path = self.local_path

        # read tables from h5
        with pd.HDFStore(path, "r") as store:
            self.person_df = store["person"]
            self.benunit_df = store["benunit"]
            self.household_df = store["household"]

    def save(self):
        path = self.local_path

        # write tables to h5 using pandas
        with pd.HDFStore(path, "w") as store:
            store["person"] = self.person_df
            store["benunit"] = self.benunit_df
            store["household"] = self.household_df

class UKSingleYearSimulation(Simulation):
    year: int
    input_dataset: UKSingleYearDataset
    scenario: Scenario

    def run(self) -> UKSingleYearDataset:
        self.input_dataset.load_from_local_path()
        sim = PolicyEngineUKSimulation(
            dataset=PolicyEngineUKSingleYearDataset(
                person=self.input_dataset.person_df,
                benunit=self.input_dataset.benunit_df,
                household=self.input_dataset.household_df,
                fiscal_year=self.year
            ),
            scenario=PolicyEngineUKScenario(
                parameter_changes=self.scenario._parameter_changes,
                simulation_modifier=self.scenario._simulation_modifier,
            )
        )

        output_dataset = self.input_dataset.model_copy()
        output_dataset.local_path = f"{self.input_dataset.name}_output_{self.year}_{self.scenario.name}.h5"
        output_dataset.household_df["hbai_household_net_income"] = sim.calculate("hbai_household_net_income", self.year)

        return output_dataset
    
class UKNationalEconomicComparisonOutput(Dataset):
    baseline_household_net_income: float
    reform_household_net_income: float
    difference: float
    
class UKNationalEconomicComparison(Simulation):
    baseline: UKSingleYearDataset
    counterfactual: UKSingleYearDataset

    def run(self) -> UKNationalEconomicComparisonOutput:
        total_baseline = self.baseline.household_df["hbai_household_net_income"].sum()
        total_counterfactual = self.counterfactual.household_df["hbai_household_net_income"].sum()

        return UKNationalEconomicComparisonOutput(
            name=f"comparison_{self.baseline.name}_vs_{self.counterfactual.name}",
            baseline_household_net_income=total_baseline,
            reform_household_net_income=total_counterfactual,
            difference=total_counterfactual - total_baseline
        )

efrs_2023_24 = UKSingleYearDataset(
    name="enhanced_frs_2023_24",
    local_path="/Users/nikhilwoodruff/policyengine/policyengine-uk-data/policyengine_uk_data/storage/enhanced_frs_2023_24.h5",
)

current_law = Scenario(
    name="current law",
    description="Current tax and benefit system in the UK.",
)