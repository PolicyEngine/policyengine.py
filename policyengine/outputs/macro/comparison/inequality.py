from policyengine import Simulation


def inequality(simulation: Simulation):
    """Calculate the impact of the reform on inequality.

    Args:
        simulation (Simulation): The simulation for which the impact is to be calculated.

    Returns:
        dict: A dictionary containing the inequality impact details with the following keys:
            - gini (dict): A dictionary with baseline and reform Gini coefficients.
            - top_10_pct_share (dict): A dictionary with baseline and reform top 10% income share.
            - top_1_pct_share (dict): A dictionary with baseline and reform top 1% income share.
    """
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
