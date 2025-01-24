from typing import TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from policyengine import Simulation

from .household import calculate_single_economy_household_sector, SingleEconomyHouseholdSector

class SingleEconomy(BaseModel):
    household: SingleEconomyHouseholdSector

def calculate_single_economy(sim: "Simulation") -> SingleEconomy:
    return SingleEconomy(
        household=calculate_single_economy_household_sector(sim),
    )