from .policy import Policy
from .dataset import Dataset
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel
from policyengine_core.simulations import Simulation as CoreSimulation
from policyengine_core.experimental.memory_config import MemoryConfig
from policyengine_core.variables import Variable
import pandas as pd
import json
import importlib

class Simulation(BaseModel):
    country: str
    policy: Policy
    dataset: Dataset
    calculations: List[Tuple[str, str]]
    version: str = None
    trace: bool = False

    output: Dict[str, Dict[str, Dict[str, list]]] | None = None
    computation_tree: Any = None # Needs stricter typing
    simulation: Any = None # Needs stricter typing

    def __hash__(self):
        return hash((
            json.dumps(self.policy.parameter_changes),
            json.dumps(self.dataset.data),
            json.dumps(self.calculations),
        ))

    def compute(self):
        if self.country == "us":
            from policyengine_us import Simulation as CoreSimulation
        elif self.country == "uk":
            from policyengine_uk import Simulation as CoreSimulation
        sim = CoreSimulation(
            dataset=self.dataset.data,
            situation=self.dataset.situation,
            reform=self.policy.parameter_changes,
            trace=self.trace,
        )

        for calculation in self.calculations:
            variable, time_period = calculation
            sim.calculate(variable, time_period)

        data = {}

        variables: List[Variable] = sim.tax_benefit_system.variables.values()

        for variable in variables:
            time_periods = sim.get_holder(variable.name).get_known_periods()
            for time_period in time_periods:
                time_period = str(time_period)
                values = sim.get_holder(variable.name).get_array(time_period)
                if values is None:
                    continue

                if variable.entity.key not in data:
                    data[variable.entity.key] = {}
                
                if time_period not in data[variable.entity.key]:
                    data[variable.entity.key][time_period] = {}

                data[variable.entity.key][time_period][variable.name] = values
        
        self.output = data
        self.simulation = sim
        self.computation_tree = sim.tracer
    
    def dataframe(self, entity: str, time_period: str) -> pd.DataFrame:
        data = self.output[entity][time_period]
        return pd.DataFrame(data)
