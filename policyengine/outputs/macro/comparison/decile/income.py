import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation
from microdf import MicroSeries
from ...single import calculate_single_macro_scenario


def calculate_income_decile_comparison(simulation: "Simulation"):
    """Calculate the impact of the reform on income deciles.

    Args:
        simulation (Simulation): The simulation for which the impact is to be calculated.

    Returns:
        dict: A dictionary containing the impact details with the following keys:
            - relative (dict): A dictionary with keys representing deciles and values as relative income changes.
            - average (dict): A dictionary with keys representing deciles and values as average income changes.
    """
    simulation.selected_sim = simulation.baseline_sim
    baseline = calculate_single_macro_scenario(simulation)
    simulation.selected_sim = simulation.reformed_sim
    reform = calculate_single_macro_scenario(simulation)
    baseline["household"]["finance"] = simulation.calculate(
        "macro/baseline/household/finance", include_arrays=True
    )
    baseline["household"]["demographics"] = simulation.calculate(
        "macro/baseline/household/demographics", include_arrays=True
    )
    reform["household"]["finance"] = simulation.calculate(
        "macro/reform/household/finance", include_arrays=True
    )
    reform["household"]["demographics"] = simulation.calculate(
        "macro/reform/household/demographics", include_arrays=True
    )

    baseline_income = MicroSeries(
        baseline["household"]["finance"]["household_net_income"],
        weights=baseline["household"]["demographics"]["household_weight"],
    )
    reform_income = MicroSeries(
        reform["household"]["finance"]["household_net_income"],
        weights=baseline_income.weights,
    )

    # Filter out negative decile values
    decile = MicroSeries(
        baseline["household"]["finance"]["household_income_decile"]
    )
    baseline_income_filtered = baseline_income[decile >= 0]
    reform_income_filtered = reform_income[decile >= 0]

    income_change = reform_income_filtered - baseline_income_filtered
    rel_income_change_by_decile = (
        income_change.groupby(decile).sum()
        / baseline_income_filtered.groupby(decile).sum()
    )

    avg_income_change_by_decile = (
        income_change.groupby(decile).sum()
        / baseline_income_filtered.groupby(decile).count()
    )
    rel_decile_dict = rel_income_change_by_decile.to_dict()
    avg_decile_dict = avg_income_change_by_decile.to_dict()
    result = dict(
        relative={int(k): v for k, v in rel_decile_dict.items()},
        average={int(k): v for k, v in avg_decile_dict.items()},
    )
    return result
