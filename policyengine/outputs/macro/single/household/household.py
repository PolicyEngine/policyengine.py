import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation
from .demographics import calculate_demographics
from .finance import calculate_finance
from .income_distribution import calculate_income_distribution
from .inequality import calculate_inequality
from .labor_supply import calculate_labor_supply


def calculate_household(
    simulation: "Simulation",
) -> dict:
    return {
        "demographics": calculate_demographics(simulation),
        "finance": calculate_finance(simulation),
        "income_distribution": calculate_income_distribution(simulation),
        "inequality": calculate_inequality(simulation),
        "labor_supply": calculate_labor_supply(simulation),
    }
