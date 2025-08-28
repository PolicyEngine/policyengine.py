from policyengine_core.simulations import Simulation
import pandas as pd
from typing import Dict, List
import time
from ..database.models import ParameterMetadata, ParameterChangeMetadata
from policyengine_core.parameters import Parameter
from ..data_models import SimulationDataModel

# Backward compatibility alias
ModelOutput = SimulationDataModel

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
