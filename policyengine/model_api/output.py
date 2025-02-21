from .simulation import Simulation
from pydantic import BaseModel
from typing import Dict, Any

class Output(BaseModel):
    """A numerical estimate derived from at least one simulation."""

    simulations: Dict[str, Simulation] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def link_simulations(self):
        pass
    
    def compute(self):
        # Compute this single output.
        pass

    def link_simulation(
        self,
        name: str,
        **kwargs,
    ) -> Simulation:
        """Link a simulation to this output."""
        simulation = Simulation(**kwargs)
        self.simulations[name] = simulation
