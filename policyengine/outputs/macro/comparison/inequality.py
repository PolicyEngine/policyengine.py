from policyengine import Simulation


def inequality(simulation: Simulation):
    baseline = simulation.calculate("macro/baseline")["household"][
        "inequality"
    ]
    reform = simulation.calculate("macro/reform")["household"]["inequality"]

    return dict(
        gini=dict(
            baseline=baseline["gini"],
            reform=reform["gini"],
        ),
        top_10_pct_share=dict(
            baseline=baseline["top_10_percent_share"],
            reform=reform["top_10_percent_share"],
        ),
        top_1_pct_share=dict(
            baseline=baseline["top_1_percent_share"],
            reform=reform["top_1_percent_share"],
        ),
    )
