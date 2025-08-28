from policyengine.models import *
from policyengine_uk import Simulation as PolicyEngineUKSimulation
from policyengine_uk.model_api import Scenario as PolicyEngineUKScenario
from policyengine_uk.data.dataset_schema import UKSingleYearDataset as PolicyEngineUKSingleYearDataset
import h5py
import pandas as pd

class UKSingleYearDataset(Dataset):
    person: Optional[Any] = None
    benunit: Optional[Any] = None
    household: Optional[Any] = None

    def load(self): # can put helpers in the main bit to avoid this
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

class UKSingleYearSimulation(Simulation):
    year: int
    data: UKSingleYearDataset

    def run(self) -> UKSingleYearDataset:
        sim = PolicyEngineUKSimulation(
            dataset=PolicyEngineUKSingleYearDataset(
                person=self.data.person,
                benunit=self.data.benunit,
                household=self.data.household,
                fiscal_year=self.year
            ),
            scenario=PolicyEngineUKScenario(
                parameter_changes=self.rules._parameter_changes,
                simulation_modifier=self.rules._simulation_modifier,
            ) + PolicyEngineUKScenario(
                parameter_changes=self.dynamics._parameter_changes,
                simulation_modifier=self.dynamics._simulation_modifier,
            )
        )

        output_dataset = self.data.model_copy()
        output_dataset.local_path = f"{self.data.name}_output_{self.year}_{self.rules.name}_{self.dynamics.name}.h5"
        output_dataset.household["hbai_household_net_income"] = sim.calculate("hbai_household_net_income", self.year)

        return output_dataset
    
class AggregateChange(ReportElementDataItem):
    variable: str
    baseline: float
    reform: float
    difference: float

class AggregateChanges(ReportElement):
    name = "aggregate changes"


efrs_2023_24 = UKSingleYearDataset(
    name="enhanced_frs_2023_24",
    local_path="/Users/nikhilwoodruff/policyengine/policyengine-uk-data/policyengine_uk_data/storage/enhanced_frs_2023_24.h5",
)

current_law = Rules(
    name="current law",
    description="Current tax and benefit system in the UK.",
)