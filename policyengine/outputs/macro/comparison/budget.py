from policyengine import Simulation


def budget(simulation: Simulation):
    """Calculate the budgetary impact of the given simulation.

    Args:
        simulation (Simulation): The simulation for which the revenue impact is to be calculated.

    Returns:
        float: The revenue impact of the simulation.
    """
    baseline = simulation.calculate("macro/baseline")
    reform = simulation.calculate("macro/reform")

    tax_revenue_impact = (
        reform["gov"]["balance"]["total_tax"]
        - baseline["gov"]["balance"]["total_tax"]
    )
    state_tax_revenue_impact = (
        reform["gov"]["balance"]["total_state_tax"]
        - baseline["gov"]["balance"]["total_state_tax"]
    )
    benefit_spending_impact = (
        reform["gov"]["balance"]["total_spending"]
        - baseline["gov"]["balance"]["total_spending"]
    )
    budgetary_impact = tax_revenue_impact - benefit_spending_impact
    households = sum(baseline["household"]["demographics"]["household_weight"])
    baseline_net_income = baseline["household"]["finance"]["total_net_income"]
    return dict(
        budgetary_impact=budgetary_impact,
        tax_revenue_impact=tax_revenue_impact,
        state_tax_revenue_impact=state_tax_revenue_impact,
        benefit_spending_impact=benefit_spending_impact,
        households=households,
        baseline_net_income=baseline_net_income,
    )
