from policyengine.core import *
from pydantic import BaseModel, Field, ConfigDict
import pandas as pd
from typing import Dict

class YearData(BaseModel):
    """Entity-level data for a single year."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: pd.DataFrame
    benunit: pd.DataFrame
    household: pd.DataFrame

class PolicyEngineUKDataset(Dataset):
    """UK dataset with multi-year entity-level data."""
    data: Dict[int, YearData] = Field(default_factory=dict)

    def save(self, filepath: str) -> None:
        """Save dataset to HDF5 file."""
        with pd.HDFStore(filepath, mode='w') as store:
            for year, year_data in self.data.items():
                store[f'{year}/person'] = year_data.person
                store[f'{year}/benunit'] = year_data.benunit
                store[f'{year}/household'] = year_data.household

    def load(self, filepath: str) -> None:
        """Load dataset from HDF5 file into this instance."""
        data = {}
        with pd.HDFStore(filepath, mode='r') as store:
            # Get all years from keys
            years = set()
            for key in store.keys():
                # Keys are like '/2025/person'
                year = int(key.split('/')[1])
                years.add(year)

            # Load data for each year
            for year in years:
                data[year] = YearData(
                    person=store[f'{year}/person'],
                    benunit=store[f'{year}/benunit'],
                    household=store[f'{year}/household']
                )

        self.data = data
        self.filepath = filepath

class PolicyEngineUK(TaxBenefitModel):
    id: str = "policyengine-uk"

    def run(self, simulation: "Simulation") -> "Simulation":
        from policyengine_uk import Microsimulation
        from policyengine_uk.data import UKSingleYearDataset, UKMultiYearDataset

        assert isinstance(simulation.dataset, PolicyEngineUKDataset)

        dataset = simulation.dataset
        dataset.load()
        year_data = dataset.data[next(iter(dataset.data))]
        input_data = UKSingleYearDataset(
            person=year_data.person,
            benunit=year_data.benunit,
            household=year_data.household,
            fiscal_year=next(iter(dataset.data))
        )
        microsim = Microsimulation(dataset=input_data)
        
        entity_variables = {
            "person": ["person_id", "benunit_id", "household_id", "age", "employment_income", "person_weight"],
            "benunit": ["benunit_id", "benunit_weight"],
            "household": ["household_id", "household_weight", "hbai_household_net_income", "equiv_hbai_household_net_income"],
        }

        data = {
            "person": pd.DataFrame(),
            "benunit": pd.DataFrame(),
            "household": pd.DataFrame(),
        }

        for entity, variables in entity_variables.items():
            for var in variables:
                data[entity][var] = microsim.calculate(var, period=simulation.year, map_to=entity).values
        
        output_dataset = PolicyEngineUKDataset(
            name=dataset.name,
            description=dataset.description,
            filepath=dataset.filepath,
            data={
                simulation.year: YearData(
                    person=data["person"],
                    benunit=data["benunit"],
                    household=data["household"]
                )
            }
        )

        output_dataset.save(dataset.filepath)


# Rebuild models to resolve forward references
PolicyEngineUKDataset.model_rebuild()
