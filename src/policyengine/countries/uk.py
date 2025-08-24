from policyengine_uk import Simulation, Microsimulation
from .general import process_simulation, ModelOutput
from pydantic import BaseModel, ConfigDict
import pandas as pd
from typing import List
from ..database.models import ParameterMetadata, ParameterChangeMetadata

class UKModelOutput(ModelOutput):
    person: pd.DataFrame
    benunit: pd.DataFrame
    household: pd.DataFrame

    table_names: List[str] = ["person", "benunit", "household"]

    model_config = ConfigDict(arbitrary_types_allowed=True)

UK_VARIABLE_WHITELIST = [
    "household_net_income",
]

def process_uk_simulation(simulation: Simulation, year: int) -> UKModelOutput:
    entity_tables = process_simulation(simulation, year, variable_whitelist=UK_VARIABLE_WHITELIST)

    return UKModelOutput(
        person=entity_tables.get("person"),
        benunit=entity_tables.get("benunit"),
        household=entity_tables.get("household"),
    )
