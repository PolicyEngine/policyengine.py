import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation
from .demographics import calculate_demographics, SingleEconomyDemographics
from .finance import calculate_finance, SingleEconomyFinanceOutput
from .inequality import calculate_inequality, SingleEconomyInequality
from .labor_supply import calculate_labor_supply, SingleEconomyLaborSupply
from pydantic import BaseModel, Field


class SingleEconomyHouseholdSector(BaseModel):
    demographics: SingleEconomyDemographics = Field(
        ..., description="Demographics of the household sector"
    )
    finance: SingleEconomyFinanceOutput = Field(
        ..., description="Finance variables of the household sector"
    )
    inequality: SingleEconomyInequality = Field(
        ..., description="Inequality of the household sector"
    )
    labor_supply: SingleEconomyLaborSupply = Field(
        ..., description="Labor supply variables of the household sector"
    )


def calculate_single_economy_household_sector(
    simulation: "Simulation",
) -> SingleEconomyHouseholdSector:
    """
    Calculate and return household sector variables for a given simulation.

    Args:
        simulation (Simulation): The simulation object containing the selected simulation data.

    Returns:
        SingleEconomyHouseholdSector: An object containing demographic, finance, inequality, and labor supply variables for the household sector.
    """
    return SingleEconomyHouseholdSector(
        demographics=calculate_demographics(simulation),
        finance=calculate_finance(simulation),
        inequality=calculate_inequality(simulation),
        labor_supply=calculate_labor_supply(simulation),
    )
