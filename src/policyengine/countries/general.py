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
            start = time.time()
            result = simulation.calculate(variable.name, year)
            end = time.time()
            if end - start > 1.0:
                print(f"Time taken to calculate {variable.name} for {year}: {end - start} seconds")
        except Exception as e:
            print(f"Error calculating {variable.name} for {year}: {e}")
            continue

        entity_tables[variable.entity.key][variable.name] = result

    return entity_tables


def create_default_parameters(simulation: Simulation, country: str) -> List[ParameterMetadata]:
    """Create default parameters for the simulation."""
    parameter_tree = simulation.tax_benefit_system.parameters
    parameters = []

    for parameter in parameter_tree.get_descendants():
        parameter_meta = ParameterMetadata(
            name=parameter.name,
            country=country,
            #parent somehow link to the parameter.parent Parameter object
            # rest of relevant attributes, look at policyengine_core.parameters.Parameter
        )

        # add parameterchanges as well?