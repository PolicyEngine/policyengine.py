import pandas as pd
from policyengine import Simulation


def budget_breakdown(
    subreforms: list,
    subreform_names: list,
    years: list,
    baseline: dict,
    options: dict,
):
    """Create a table of per-provision budgetary impacts for a given reform."""
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

    df = pd.DataFrame(
        {
            "Provision": subreform_items,
            "Year": year_items,
            "Budgetary impact": budget_items,
        }
    )

    table = pd.pivot_table(
        df,
        values="Budgetary impact",
        columns="Year",
        index="Provision",
        aggfunc="first",
    )
    return table
