from policyengine import Simulation
from typing import List
import pandas as pd


def breakdown(
    simulation: Simulation,
    provisions: List[dict] = None,
    provision_names: List[str] = None,
    count_years: int = 5,
) -> pd.DataFrame:
    """Calculate the budgetary impact of the reform by provision.

    Args:
        simulation (Simulation): The simulation for which the impact is to be calculated.
        provisions (List[dict], optional): The provisions to include in the breakdown. Defaults to None.
        provision_names (List[str], optional): The names of the provisions to include in the breakdown. Defaults to None.
        count_years (int, optional): The number of years to include in the breakdown. Defaults to 5.

    Returns:
        pd.DataFrame: A DataFrame (long) containing the budgetary impact of the reform by provision.
    """
    if provision_names is None:
        return {}

    subreforms = provisions
    years = list(
        range(simulation.time_period, simulation.time_period + count_years)
    )
    baseline = simulation.baseline.reform
    options = simulation.options
    subreform_names = provision_names
    subreform_items = []
    year_items = []
    budget_items = []
    for year in years:
        last_budgetary_impact = 0
        for i in range(len(subreforms)):
            reform_subset = subreforms[: i + 1]
            sim = Simulation(
                country="uk",
                scope="macro",
                baseline=baseline,
                reform=reform_subset,
                time_period=year,
                options=options,
            )
            budget = sim.calculate("macro/comparison/budget/general")[
                "budgetary_impact"
            ]
            key_focus = subreform_names[i]
            difference = budget - last_budgetary_impact
            last_budgetary_impact = budget

            subreform_items.append(key_focus)
            year_items.append(year)
            budget_items.append(difference)

            print(
                f"Year: {year}, Provision: {key_focus}, Budgetary impact: {round(difference/1e6)}"
            )

    return pd.DataFrame(
        {
            "Provision": subreform_items,
            "Year": year_items,
            "Budgetary impact": budget_items,
        }
    )
