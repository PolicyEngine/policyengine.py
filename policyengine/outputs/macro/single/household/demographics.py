import typing
from typing import List
from pydantic import BaseModel, Field
if typing.TYPE_CHECKING:
    from policyengine import Simulation
from microdf import MicroSeries

class SingleEconomyDemographics(BaseModel):
    household_count_people: List[int] = Field(..., description="Number of people in each household")
    person_weight: List[float] = Field(..., description="Weight of each person")
    household_weight: List[float] = Field(..., description="Weight of each household")
    total_households: int = Field(..., description="Total number of households")
    is_male: List[bool] = Field(..., description="Gender indicator for each person")
    age: List[int] = Field(..., description="Age of each person")
    race: typing.Optional[List[str]] = Field(None, description="Race of each person, if available")


def calculate_demographics(
    simulation: "Simulation",
) -> SingleEconomyDemographics:
    """
    Calculate and return demographic information for a given simulation.

    Args:
        simulation (Simulation): The simulation object containing the selected simulation data.

    Returns:
        SingleEconomyDemographics: An object containing demographic information.
    """
    sim = simulation.selected_sim
    household_count_people = (
        sim.calculate("household_count_people").astype(int).tolist()
    )
    person_weight = sim.calculate("person_weight").astype(float).tolist()
    household_weight = sim.calculate("household_weight").astype(float).tolist()
    is_male = sim.calculate("is_male").astype(bool).tolist()
    if "race" in sim.tax_benefit_system.variables:
        race = sim.calculate("race").astype(str).tolist()
    else:
        race = None
    age = sim.calculate("age").astype(int).tolist()
    total_households = int(sum(household_weight))
    return SingleEconomyDemographics(
        household_count_people=household_count_people,
        person_weight=person_weight,
        household_weight=household_weight,
        total_households=total_households,
        is_male=is_male,
        age=age,
        race=race,
    )
