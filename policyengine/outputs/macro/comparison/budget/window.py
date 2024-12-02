from policyengine import Simulation
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from policyengine.utils.charts import *


def window(
    simulation: Simulation,
    chart: bool = False,
    federal_only: bool = False,
    count_years: int = 1,
):
    if count_years == 1:
        kwargs = {}
    else:
        kwargs = {"count_years": count_years}
    baseline = simulation.calculate(
        "macro/baseline/gov/budget_window", **kwargs
    )
    reform = simulation.calculate("macro/reform/gov/budget_window", **kwargs)
    total_budget_effect = [
        (y - x) / 1e9
        for x, y in zip(baseline["total_budget"], reform["total_budget"])
    ]
    federal_budget_effect = [
        (y - x) / 1e9
        for x, y in zip(
            baseline["total_federal_budget"], reform["total_federal_budget"]
        )
    ]

    result = dict(
        total_budget=total_budget_effect,
        federal_budget=federal_budget_effect,
    )

    if chart:
        return budget_window_chart(
            result["federal_budget"]
            if federal_only
            else result["total_budget"]
        )
    else:
        return result


def budget_window_chart(budget_effect) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Bar(
                y=budget_effect,
                x=list(map(str, range(2025, 2025 + 10))),
                marker=dict(
                    color=[BLUE if y > 0 else DARK_GRAY for y in budget_effect]
                ),
                text=[
                    f"{'+' if y >= 0 else ''}{y:.1f}" for y in budget_effect
                ],
            )
        ]
    ).update_layout(
        title="Budgetary impact by year",
        xaxis_title="Year",
        yaxis_title="Budgetary impact (£ billions)",
    )

    return format_fig(fig)
