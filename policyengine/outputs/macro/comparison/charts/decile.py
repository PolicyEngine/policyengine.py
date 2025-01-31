import plotly.express as px
import plotly.graph_objects as go
import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.charts import *
from typing import Literal


def create_decile_chart(
    simulation: "Simulation",
    decile_variable: Literal["income", "wealth"],
    relative: bool,
) -> go.Figure:
    """Create a budget comparison chart."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    economy = simulation.calculate_economy_comparison()

    if decile_variable == "income":
        data = economy.distributional.income.income_change
    else:
        data = economy.distributional.wealth.income_change

    if relative:
        data = data.relative
    else:
        data = data.average

    avg_change = sum(data.values()) / len(data)

    if relative:
        text = [f"{value:.1%}" for value in data.values()]
        avg_change = round(avg_change, 3)
    else:
        text = [f"${value:,.0f}" for value in data.values()]
        avg_change = round(avg_change)

    avg_change_str = (
        f"${abs(avg_change):,.0f}"
        if not relative
        else f"{abs(avg_change):.1%}"
    )

    if avg_change > 0:
        description = (
            f"increase the net income of households by {avg_change_str}"
        )
    elif avg_change < 0:
        description = (
            f"decrease the net income of households by {avg_change_str}"
        )
    else:
        description = "have no effect on household net income"

    chart = go.Figure(
        data=[
            go.Bar(
                x=list(data.keys()),
                y=list(data.values()),
                text=text,
                marker=dict(
                    color=[
                        BLUE if value > 0 else DARK_GRAY
                        for value in data.values()
                    ]
                ),
            )
        ]
    ).update_layout(
        title=f"{simulation.options.title} would {description}",
        yaxis_title=f"Average change to net income ({'%' if relative else '$'})",
        yaxis_tickformat="$,.0f" if not relative else ".0%",
        xaxis_title=(
            "Income decile" if decile_variable == "income" else "Wealth decile"
        ),
        uniformtext=dict(
            mode="hide",
            minsize=12,
        ),
        xaxis_tickvals=list(data.keys()),
    )

    return format_fig(
        chart, country=simulation.options.country, add_zero_line=True
    )
