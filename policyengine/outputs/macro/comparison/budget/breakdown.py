from policyengine import Simulation
from typing import List
import pandas as pd


def breakdown(
    simulation: Simulation,
    provisions: List[dict] | None = None,
    provision_names: List[str] | None = None,
    count_years: int = 5,
    verbose: bool = False,
) -> pd.DataFrame:
    """Calculate the budgetary impact of the reform by provision.

    Args:
        simulation (Simulation): The simulation for which the impact is to be calculated.
        provisions (List[dict], optional): The provisions to include in the breakdown. Defaults to None.
        provision_names (List[str], optional): The names of the provisions to include in the breakdown. Defaults to None.
        count_years (int, optional): The number of years to include in the breakdown. Defaults to 5.
        verbose (bool, optional): Whether to print the budgetary impacts. Defaults to False.

    Returns:
        pd.DataFrame: A DataFrame (long) containing the budgetary impact of the reform by provision.
    """
    if provision_names is None:
        return {}
    years = list(
        range(simulation.time_period, simulation.time_period + count_years)
    )
    baseline = simulation.baseline.reform
    options = simulation.options
    subreform_items = []
    year_items = []
    budget_items = []
    for year in years:
        last_budgetary_impact = 0
        for i in range(len(provisions)):
            reform_subset = provisions[: i + 1]
            sim = Simulation(
                country="uk",
                scope="macro",
                baseline=baseline,
                reform=reform_subset,
                time_period=year,
                options=options,
                data=simulation.data,
            )
            budget = sim.calculate("macro/comparison/budget/general")[
                "budgetary_impact"
            ]
            key_focus = provision_names[i]
            difference = budget - last_budgetary_impact
            last_budgetary_impact = budget

            subreform_items.append(key_focus)
            year_items.append(year)
            budget_items.append(difference)

            if verbose:
                print(
                    f"Year: {year}, Provision: {key_focus}, Budgetary impact: {round(difference/1e9)}"
                )

    return pd.DataFrame(
        {
            "Provision": subreform_items,
            "Year": year_items,
            "Budgetary impact": budget_items,
        }
    )
