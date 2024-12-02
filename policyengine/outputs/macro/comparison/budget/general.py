from policyengine import Simulation
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from policyengine.utils.charts import *


def general(simulation: Simulation, chart: bool = False):
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
    result = dict(
        budgetary_impact=budgetary_impact,
        tax_revenue_impact=tax_revenue_impact,
        state_tax_revenue_impact=state_tax_revenue_impact,
        benefit_spending_impact=benefit_spending_impact,
        households=households,
        baseline_net_income=baseline_net_income,
    )
    if chart:
        return budget_chart(simulation, result)
    else:
        return result


def budget_chart(simulation: Simulation, data: dict) -> go.Figure:
    if simulation.country == "uk":
        x = ["Tax revenues", "Benefit spending", "Budgetary impact"]
        y = [
            data["tax_revenue_impact"],
            -data["benefit_spending_impact"],
            data["budgetary_impact"],
        ]
    else:
        x = [
            "Federal tax revenues",
            "State tax revenues",
            "Benefit spending",
            "Budgetary impact",
        ]
        y = [
            data["tax_revenue_impact"] - data["state_tax_revenue_impact"],
            data["state_tax_revenue_impact"],
            -data["benefit_spending_impact"],
            data["budgetary_impact"],
        ]
    fig = go.Figure(
        data=[
            go.Waterfall(
                x=x,
                y=[i / 1e9 for i in y],
                orientation="v",
                measure=["relative"] * (len(x) - 1) + ["total"],
                text=[
                    (
                        "+" + str(round(val / 1e9, 1))
                        if val > 0
                        else str(round(val / 1e9, 1))
                    )
                    for val in y
                ],
                textposition="inside",
                increasing={"marker": {"color": BLUE}},
                decreasing={"marker": {"color": DARK_GRAY}},
                totals={"marker": {"color": BLUE if y[-1] > 0 else DARK_GRAY}},
                connector={
                    "line": {"color": DARK_GRAY, "width": 2, "dash": "dot"}
                },
            )
        ]
    )

    fig.update_layout(
        title="Budgetary impact by government revenue and spending",
        xaxis_title="",
        yaxis_title="Budgetary impact (£ billions)",
        yaxis_tickformat=",.0f",
    )

    return format_fig(fig)
