import typing
if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel

def calculate_economy_comparison(simulation: "Simulation"):
    