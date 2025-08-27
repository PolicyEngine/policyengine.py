from policyengine_core.simulations import Simulation
import pandas as pd
from typing import Dict, List
from pydantic import BaseModel, ConfigDict
import time
from ..database.models import ParameterMetadata, ParameterChangeMetadata
from policyengine_core.parameters import Parameter

class ModelOutput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    table_names: List[str] = []
    variable_whitelist: List[str] = []

    def get_tables(self) -> Dict[str, pd.DataFrame]:
        return {
            table_name: getattr(self, table_name)
            for table_name in self.table_names
        }
    
    def to_dict(self):
        tables = self.get_tables()
        return {name: {
            col: df[col].values
            for col in df.columns
        } for name, df in tables.items()}
    
    @classmethod
    def from_tables(cls, data: Dict) -> "ModelOutput":
        """Reconstruct ModelOutput from dictionary of DataFrames or dict data.
        
        Args:
            data: Dictionary mapping table names to DataFrames or dict representations
            
        Returns:
            Instance of the appropriate ModelOutput subclass
        """
        # Convert dict representations back to DataFrames if needed
        tables = {}
        for name, table_data in data.items():
            if isinstance(table_data, pd.DataFrame):
                tables[name] = table_data
            elif isinstance(table_data, dict):
                # Convert dict to DataFrame
                tables[name] = pd.DataFrame(table_data)
            else:
                tables[name] = table_data
        
        # Create instance with the dataframes as attributes
        return cls(**tables)

def process_simulation(simulation: Simulation, year: int, variable_whitelist: List[str] = []) -> Dict[str, pd.DataFrame]:
    variables = list(simulation.tax_benefit_system.variables.values())

    entity_tables = {}

    for variable in variable_whitelist:
        simulation.calculate(variable, year)

    known_variables = [
        variable for variable in variables
        if len(simulation.get_holder(variable.name).get_known_periods()) > 0
    ]

    for variable in known_variables:
        if variable.definition_period != "year":
            continue
        if variable.entity.key not in entity_tables:
            entity_tables[variable.entity.key] = pd.DataFrame()

        try:
            result = simulation.calculate(variable.name, year)
        except Exception as e:
            print(f"Error calculating {variable.name} for {year}: {e}")
            continue

        entity_tables[variable.entity.key][variable.name] = result

    return entity_tables
