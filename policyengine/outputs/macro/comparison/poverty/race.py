from policyengine import Simulation
from microdf import MicroSeries


def race(simulation: Simulation):
    """Calculate the impact of the reform on poverty by race.

    Args:
        simulation (Simulation): The simulation for which the impact is to be calculated.

    Returns:
        dict: A dictionary containing the poverty impact details with the following keys:
            - poverty (dict): A dictionary with keys representing races and values as dictionaries with baseline and reform poverty rates.
    """
    baseline = simulation.calculate("macro/baseline")["household"]["finance"]
    reform = simulation.calculate("macro/reform")["household"]["finance"]
    baseline_demographics = simulation.calculate("macro/baseline")[
        "household"
    ]["demographics"]

    if baseline_demographics["race"] is None:
        return {}
    baseline_poverty = MicroSeries(
        baseline["person_in_poverty"],
        weights=baseline_demographics["person_weight"],
    )
    reform_poverty = MicroSeries(
        reform["person_in_poverty"], weights=baseline_poverty.weights
    )
    race = MicroSeries(
        baseline_demographics["race"]
    )  # Can be WHITE, BLACK, HISPANIC, or OTHER.

    poverty = dict(
        white=dict(
            baseline=float(baseline_poverty[race == "WHITE"].mean()),
            reform=float(reform_poverty[race == "WHITE"].mean()),
        ),
        black=dict(
            baseline=float(baseline_poverty[race == "BLACK"].mean()),
            reform=float(reform_poverty[race == "BLACK"].mean()),
        ),
        hispanic=dict(
            baseline=float(baseline_poverty[race == "HISPANIC"].mean()),
            reform=float(reform_poverty[race == "HISPANIC"].mean()),
        ),
        other=dict(
            baseline=float(baseline_poverty[race == "OTHER"].mean()),
            reform=float(reform_poverty[race == "OTHER"].mean()),
        ),
    )

    return dict(
        poverty=poverty,
    )
