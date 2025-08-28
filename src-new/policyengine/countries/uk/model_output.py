from typing import TYPE_CHECKING, List, Optional
if TYPE_CHECKING:
    from policyengine_uk import Simulation
from ..general import process_simulation
from ...data_models import SimulationDataModel
from pydantic import ConfigDict
import pandas as pd

class UKModelOutput(SimulationDataModel):
    """UK-specific model output that extends SimulationDataModel."""
    # UK has benefit_unit (benunit) instead of some US entities
    benefit_unit: Optional[pd.DataFrame] = None
    
    # UK doesn't have these US entities
    marital_unit: None = None
    family: None = None
    tax_unit: None = None
    spm_unit: None = None
    
    @property
    def table_names(self) -> List[str]:
        """Get UK-specific table names."""
        return ["person", "household", "benefit_unit"]
    
    @classmethod
    def from_tables(cls, data: dict) -> "UKModelOutput":
        """Create UKModelOutput from dictionary of DataFrames.
        
        Handle both 'benunit' and 'benefit_unit' naming conventions.
        """
        # Handle benunit vs benefit_unit naming
        if "benunit" in data and "benefit_unit" not in data:
            data["benefit_unit"] = data.pop("benunit")
        
        # Ensure required fields
        if "person" not in data:
            data["person"] = pd.DataFrame()
        if "household" not in data:
            data["household"] = pd.DataFrame()
            
        return cls(**data)

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
        benefit_unit=entity_tables.get("benunit"),  # Map benunit to benefit_unit
        household=entity_tables.get("household"),
    )
