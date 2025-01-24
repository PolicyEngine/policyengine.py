import pandas as pd


def budget_breakdown(
    subreforms: list,
    subreform_names: list,
    years: list,
    baseline: dict,
    options: dict,
    verbose: bool = False,
):
    """Create a table of per-provision budgetary impacts for a given reform.

    Args:
        subreforms (list): A list of reform dictionaries.
        subreform_names (list): A list of names for the provisions in the reform.
        years (list): A list of years to include in the breakdown.
        baseline (dict): The baseline reform.
        options (dict): The simulation options.
        verbose (bool, optional): Whether to print the budgetary impacts. Defaults to False.

    Returns:
        pd.DataFrame: A DataFrame containing the budgetary impact of the reform by provision.
    """
    from policyengine import Simulation

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
            if verbose:
                print(
                    f"Year: {year}, Provision: {key_focus}, Budgetary impact: {round(difference/1e9)}"
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
