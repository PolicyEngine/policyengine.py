from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from policyengine_uk import Simulation
from ..general import process_simulation, ModelOutput
from pydantic import BaseModel, ConfigDict
import pandas as pd
from typing import List
from ...database.models import ParameterMetadata, ParameterChangeMetadata

class UKModelOutput(ModelOutput):
    person: pd.DataFrame
    benunit: pd.DataFrame
    household: pd.DataFrame

    table_names: List[str] = ["person", "benunit", "household"]

    model_config = ConfigDict(arbitrary_types_allowed=True)

UK_VARIABLE_WHITELIST = [
    # ID columns for linking entities
    "person_id",
    "person_household_id",
    "person_benunit_id",
    "benunit_id",
    "household_id",
    
    # Income and wealth
    "household_net_income",
    # The following may not exist in all datasets, so we'll check them later
    "equiv_household_net_income",
    "household_market_income",
    "household_income_decile",
    "household_wealth_decile",
    "total_wealth",
    "employment_income",
    "self_employment_income",
    "hbai_household_net_income",
    "equiv_hbai_household_net_income",
    "consumption",
    
    # Weights
    "household_weight",
    "person_weight",
    "household_count_people",
    
    # Demographics
    "age",
    "is_male",
    
    # Government budget
    "gov_balance",
    "gov_tax",
    "gov_spending",
    
    # Tax and benefits
    "household_tax",
    "household_benefits",
    
    # UK-specific programs - taxes
    "income_tax",
    "national_insurance",
    "vat",
    "council_tax",
    "fuel_duty",
    "ni_employer",
    "capital_gains_tax",
    
    # UK-specific programs - benefits
    "universal_credit",
    "child_benefit",
    "income_support",
    "housing_benefit",
    "pension_credit",
    "state_pension",
    "child_tax_credit",
    "working_tax_credit",
    "tax_credits",
    "pip",
    "dla",
    
    # Poverty variables
    "in_poverty",
    "in_relative_poverty_bhc",
    "in_poverty_ahc",
    "in_relative_poverty_ahc",
]

def process_uk_simulation(simulation: "Simulation", year: int) -> UKModelOutput:
    entity_tables = process_simulation(simulation, year, variable_whitelist=UK_VARIABLE_WHITELIST)

    return UKModelOutput(
        person=entity_tables.get("person"),
        benunit=entity_tables.get("benunit"),
        household=entity_tables.get("household"),
    )
