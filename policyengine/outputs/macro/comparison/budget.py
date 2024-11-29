from policyengine import Simulation


def budget(simulation: Simulation):
    """Calculate the budgetary impact of the given simulation.

    Args:
        simulation (Simulation): The simulation for which the revenue impact is to be calculated.

    Returns:
        dict: A dictionary containing the budgetary impact details with the following keys:
            - budgetary_impact (float): The overall budgetary impact.
            - tax_revenue_impact (float): The impact on tax revenue.
            - state_tax_revenue_impact (float): The impact on state tax revenue.
            - benefit_spending_impact (float): The impact on benefit spending.
            - households (int): The number of households.
            - baseline_net_income (float): The total net income in the baseline scenario.
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
