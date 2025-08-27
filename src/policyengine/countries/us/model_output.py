from ..general import process_simulation, ModelOutput
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
    # ID columns for linking entities
    "person_id",
    "person_household_id",
    "person_tax_unit_id",
    "person_spm_unit_id",
    "person_family_id",
    "person_marital_unit_id",
    "tax_unit_id",
    "spm_unit_id",
    "family_id",
    "marital_unit_id",
    "household_id",
    
    # Income
    "household_net_income",
    "household_net_income_including_health_benefits",
    "equiv_household_net_income",
    "household_market_income",
    "household_income_decile",
    "employment_income",
    "self_employment_income",
    
    # Weights
    "household_weight",
    "person_weight",
    "tax_unit_weight",
    "spm_unit_weight",
    "family_weight",
    "household_count_people",
    
    # Demographics
    "age",
    "is_male",
    
    # Poverty (SPM-based)
    "in_poverty",
    "in_deep_poverty",
    "poverty_gap",
    "deep_poverty_gap",
    
    # Federal taxes and benefits
    "household_tax",
    "household_benefits",
    "household_state_tax_before_refundable_credits",
    "household_state_benefits",
    "household_refundable_tax_credits",
    "household_refundable_state_tax_credits",
    
    # Specific federal programs
    "snap",
    "tanf",
    "ssi",
    "social_security",
    "eitc",
    "ctc",
    "wic",
    "unemployment_compensation",
    "medicaid",
    
    # State programs (if available)
    "state_eitc",
    "state_ctc",
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