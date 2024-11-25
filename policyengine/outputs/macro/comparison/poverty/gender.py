from policyengine import Simulation
from microdf import MicroSeries


def gender(simulation: Simulation):
    baseline = simulation.calculate("macro/baseline")["household"]["finance"]
    reform = simulation.calculate("macro/reform")["household"]["finance"]
    baseline_demographics = simulation.calculate("macro/baseline")[
        "household"
    ]["demographics"]

    if baseline_demographics["is_male"] is None:
        return {}
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
    is_male = MicroSeries(baseline_demographics["is_male"])

    poverty = dict(
        male=dict(
            baseline=float(baseline_poverty[is_male].mean()),
            reform=float(reform_poverty[is_male].mean()),
        ),
        female=dict(
            baseline=float(baseline_poverty[~is_male].mean()),
            reform=float(reform_poverty[~is_male].mean()),
        ),
    )

    deep_poverty = dict(
        male=dict(
            baseline=float(baseline_deep_poverty[is_male].mean()),
            reform=float(reform_deep_poverty[is_male].mean()),
        ),
        female=dict(
            baseline=float(baseline_deep_poverty[~is_male].mean()),
            reform=float(reform_deep_poverty[~is_male].mean()),
        ),
    )

    return dict(
        poverty=poverty,
        deep_poverty=deep_poverty,
    )
