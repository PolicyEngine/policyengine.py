from policyengine import Simulation
from microdf import MicroSeries


def age(simulation: Simulation):
    """Calculate the impact of the reform on poverty by age.

    Args:
        simulation (Simulation): The simulation for which the impact is to be calculated.

    Returns:
        dict: A dictionary containing the poverty and deep poverty impact details with the following keys:
            - poverty (dict): A dictionary with keys representing age groups and values as dictionaries with baseline and reform poverty rates.
            - deep_poverty (dict): A dictionary with keys representing age groups and values as dictionaries with baseline and reform deep poverty rates.
    """
    baseline = simulation.calculate("macro/baseline")["household"]["finance"]
    reform = simulation.calculate("macro/reform")["household"]["finance"]
    baseline_demographics = simulation.calculate("macro/baseline")[
        "household"
    ]["demographics"]

    baseline_poverty = MicroSeries(
        baseline["person_in_poverty"],
        weights=baseline_demographics["person_weight"],
    )
    baseline_deep_poverty = MicroSeries(
        baseline["person_in_deep_poverty"],
        weights=baseline_demographics["person_weight"],
    )
    reform_poverty = MicroSeries(
        reform["person_in_poverty"], weights=baseline_poverty.weights
    )
    reform_deep_poverty = MicroSeries(
        reform["person_in_deep_poverty"], weights=baseline_poverty.weights
    )
    age = MicroSeries(baseline_demographics["age"])

    poverty = dict(
        child=dict(
            baseline=float(baseline_poverty[age < 18].mean()),
            reform=float(reform_poverty[age < 18].mean()),
        ),
        adult=dict(
            baseline=float(baseline_poverty[(age >= 18) & (age < 65)].mean()),
            reform=float(reform_poverty[(age >= 18) & (age < 65)].mean()),
        ),
        senior=dict(
            baseline=float(baseline_poverty[age >= 65].mean()),
            reform=float(reform_poverty[age >= 65].mean()),
        ),
        all=dict(
            baseline=float(baseline_poverty.mean()),
            reform=float(reform_poverty.mean()),
        ),
    )

    deep_poverty = dict(
        child=dict(
            baseline=float(baseline_deep_poverty[age < 18].mean()),
            reform=float(reform_deep_poverty[age < 18].mean()),
        ),
        adult=dict(
            baseline=float(
                baseline_deep_poverty[(age >= 18) & (age < 65)].mean()
            ),
            reform=float(reform_deep_poverty[(age >= 18) & (age < 65)].mean()),
        ),
        senior=dict(
            baseline=float(baseline_deep_poverty[age >= 65].mean()),
            reform=float(reform_deep_poverty[age >= 65].mean()),
        ),
        all=dict(
            baseline=float(baseline_deep_poverty.mean()),
            reform=float(reform_deep_poverty.mean()),
        ),
    )

    return dict(
        poverty=poverty,
        deep_poverty=deep_poverty,
    )
