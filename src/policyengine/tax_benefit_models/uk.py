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

    @classmethod
    def load(cls, filepath: str, **kwargs) -> 'PolicyEngineUKDataset':
        """Load dataset from HDF5 file."""
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

        # Create instance with data
        return cls(data=data, filepath=filepath, **kwargs)

class PolicyEngineUK(TaxBenefitModel):
    pass


# Rebuild models to resolve forward references
PolicyEngineUKDataset.model_rebuild()
