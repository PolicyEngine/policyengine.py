"""Belgium pilot dataset: populace entity tables with calibrated weights.

The pilot layout has two entities (person, household), mirroring the
populace ``BE_SCHEMA``. Files are plain pandas HDF5 stores with ``person``
and ``household`` keys; weights live in ``person_weight`` /
``household_weight`` columns, as in the US/UK single-year layouts.
"""

from typing import Any, Optional

import pandas as pd
from microdf import MicroDataFrame
from pydantic import ConfigDict, Field

from policyengine.core.dataset import Dataset, YearData


class BEYearData(YearData):
    """Entity-level data for a single Belgian year."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    person: MicroDataFrame
    household: MicroDataFrame

    @property
    def entity_data(self) -> dict[str, MicroDataFrame]:
        return {"person": self.person, "household": self.household}


class PopulaceBelgiumDataset(Dataset):
    """Belgium pilot dataset loaded from a populace-be HDF5 artifact."""

    data: Optional[BEYearData] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def load(self) -> None:
        person = pd.read_hdf(self.filepath, key="person")
        household = pd.read_hdf(self.filepath, key="household")
        self.data = BEYearData(
            person=MicroDataFrame(person, weights="person_weight"),
            household=MicroDataFrame(household, weights="household_weight"),
        )

    def save(self) -> None:
        if self.data is None:
            raise ValueError("No data to save.")
        pd.DataFrame(self.data.person).to_hdf(self.filepath, key="person", mode="w")
        pd.DataFrame(self.data.household).to_hdf(self.filepath, key="household")
