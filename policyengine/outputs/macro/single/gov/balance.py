import typing
if typing.TYPE_CHECKING:
    from policyengine import Simulation


def calculate_balance(simulation: "Simulation") -> dict:
    sim = simulation.selected_sim
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
