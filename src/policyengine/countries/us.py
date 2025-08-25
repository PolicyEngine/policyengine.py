from .general import process_simulation, ModelOutput
from pydantic import BaseModel, ConfigDict
import pandas as pd
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from policyengine_us import Simulation

class USModelOutput(ModelOutput):
    person: pd.DataFrame
    marital_unit: pd.DataFrame
    family: pd.DataFrame
    tax_unit: pd.DataFrame
    spm_unit: pd.DataFrame
    household: pd.DataFrame

    table_names: List[str] = ["person", "marital_unit", "family", "tax_unit", "spm_unit", "household"]

    model_config = ConfigDict(arbitrary_types_allowed=True)

US_VARIABLE_WHITELIST = [
    "household_net_income",
]

def process_us_simulation(simulation: "Simulation", year: int) -> USModelOutput:
    entity_tables = process_simulation(simulation, year, variable_whitelist=US_VARIABLE_WHITELIST)

    return USModelOutput(
        person=entity_tables.get("person"),
        marital_unit=entity_tables.get("marital_unit"),
        family=entity_tables.get("family"),
        tax_unit=entity_tables.get("tax_unit"),
        spm_unit=entity_tables.get("spm_unit"),
        household=entity_tables.get("household"),
    )