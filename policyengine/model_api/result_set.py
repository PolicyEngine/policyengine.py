from .simulation import Simulation
from .output import Output
from .policy import Policy
from .dataset import Dataset
import pandas as pd
from pydantic import BaseModel
from typing import List
from tqdm import tqdm
import logging

class ResultSet(BaseModel):
    outputs: List[Output]

    def compute(self, verbose: bool = False):
        logger = logging.getLogger()
        if verbose:
            logger.setLevel(logging.INFO)
        # Identify unique required simulations
        simulations: List[Simulation] = []
        for output in self.outputs:
            output.link_simulations()
            simulations.extend(list(output.simulations.values()))
        
        logger.info(f"These {len(self.outputs)} outputs require {len(simulations)} simulations.")

        simulations = list(set(simulations))

        logger.info(f"Reduced to {len(simulations)} unique simulations.")

        for simulation in (tqdm if verbose else list)(simulations):
            simulation.compute()

        simulation_hashes = [hash(simulation) for simulation in simulations]

        for output in (tqdm if verbose else list)(self.outputs):
            for name, instance in output.simulations.items():
                instance_hash = hash(instance)
                if instance_hash in simulation_hashes:
                    output.simulations[name] = simulations[simulation_hashes.index(instance_hash)]
            output.compute()

    def dataframe(self, columns: List[str] | None = None, replacements: dict = {}) -> pd.DataFrame:
        # First, check if the outputs all have the same type (are from the same table)
        df = pd.DataFrame([vars(output) for output in self.outputs])

        if columns is None:
            columns = list(vars(self.outputs[0]))
        
        for column in columns:
            df[column] = df[column].replace(replacements)

        return df[columns]