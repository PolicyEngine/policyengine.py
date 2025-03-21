import pandas as pd
from policyengine import Simulation
from policyengine_core.simulations import Microsimulation

from policyengine.outputs.macro.single.budget import (
    _calculate_government_balance,
)


def calculate_budget_window_comparison(
    simulation: Simulation, count_years: int = 10
) -> pd.DataFrame:
    """Calculate how a reform affects the budget over a specified window.

    Args:
        simulation (Simulation): The simulation object containing baseline and reform simulations.
        count_years (int, optional): The number of years over which to calculate the budget impact. Defaults to 10.

    Returns:
        pd.DataFrame: A DataFrame containing the years, federal budget impacts, and state budget impacts.
    """

    start_year = simulation.options.time_period
    end_year = start_year + count_years

    years = []
    federal_budget_impacts = []
    state_budget_impacts = []

    for year in range(start_year, end_year):
        baseline_f, baseline_s = _get_balance_for_year(
            simulation.baseline_simulation, year, simulation.options.country
        )
        reform_f, reform_s = _get_balance_for_year(
            simulation.reform_simulation, year, simulation.options.country
        )
        years.append(year)
        federal_budget_impacts.append(reform_f - baseline_f)
        state_budget_impacts.append(reform_s - baseline_s)

    return pd.DataFrame(
        {
            "year": years,
            "federal_budget_impact": federal_budget_impacts,
            "state_budget_impact": state_budget_impacts,
        }
    )


def _get_balance_for_year(
    sim: Microsimulation,
    year: int,
    country: str,
):
    if country == "uk":
        total_tax = sim.calculate("gov_tax", period=year).sum()
        total_spending = sim.calculate("gov_spending", period=year).sum()
        total_state_tax = 0
    else:
        total_tax = sim.calculate("household_tax", period=year).sum()
        total_spending = sim.calculate("household_benefits", period=year).sum()
        total_state_tax = sim.calculate(
            "household_state_income_tax", period=year
        ).sum()

    national_tax = total_tax - total_state_tax

    national_balance = national_tax - total_spending
    state_balance = total_state_tax
    return national_balance, state_balance
