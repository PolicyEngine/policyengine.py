from typing import TypedDict, Literal
from policyengine import Simulation


class BalanceOutput(TypedDict):
    total_tax: float
    total_spending: float
    total_state_tax: float


def balance(simulation: Simulation) -> BalanceOutput:
    """Calculate the total tax and spending for the selected simulation.

    Args:
        simulation (Simulation): The selected simulation.
            Must have attributes:
            - country: Either "uk" or "us"
            - selected_sim: Simulation object with calculate() method

    Returns:
        BalanceOutput: A dictionary containing:
            - total_tax (float): Total tax collected
            - total_spending (float): Total government spending
            - total_state_tax (float): Total state-level tax (US only, 0 for UK)

    Raises:
        AttributeError: If simulation lacks required attributes
        ValueError: If country is neither "uk" nor "us"
    """
    sim = simulation.baseline_sim
    if simulation.country == "uk":
        total_tax = sim.calculate("gov_tax").sum()
        total_spending = sim.calculate("gov_spending").sum()
        total_state_tax = 0
    elif simulation.country == "us":
        total_tax = sim.calculate("household_tax").sum()
        total_spending = sim.calculate("household_benefits").sum()
        total_state_tax = sim.calculate("household_state_income_tax").sum()
    return {
        "total_tax": total_tax,
        "total_spending": total_spending,
        "total_state_tax": total_state_tax,
    }
