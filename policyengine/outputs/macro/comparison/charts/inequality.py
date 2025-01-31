import plotly.express as px
import plotly.graph_objects as go
import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.charts import *


def create_inequality_chart(
    simulation: "Simulation",
    relative: bool,
) -> go.Figure:
    """Create a budget comparison chart."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    economy = simulation.calculate_economy_comparison()

    x_values = [
        "Gini index",
        "Top 10% share",
        "Top 1% share",
    ]

    if relative:
        data = economy.inequality.relative_change
    else:
        data = economy.inequality.change

    y_values = [
        data.gini,
        data.top_10_share,
        data.top_1_share,
    ]

    if all(value < 0 for value in y_values):
        description = f"lower inequality"
    elif all(value > 0 for value in y_values):
        description = f"raise inequality"
    else:
        description = "have an ambiguous effect on inequality"

    if not relative:
        y_values = [value * 100 for value in y_values]

    chart = go.Figure(
        data=[
            go.Bar(
                x=x_values,
                y=y_values,
                text=[
                    f"{value:.1%}" if relative else f"{value:.1f}pp"
                    for value in y_values
                ],
                marker=dict(
                    color=[
                        BLUE if value < 0 else DARK_GRAY for value in y_values
                    ]
                ),
            ),
        ]
    ).update_layout(
        title=f"{simulation.options.title} would {description}",
        yaxis_title="Change" + (" (%)" if relative else ""),
        yaxis_ticksuffix="pp" if not relative else "",
        yaxis_tickformat=".0%" if relative else ".1f",
        uniformtext=dict(
            mode="hide",
            minsize=12,
        ),
    )

    return format_fig(
        chart, country=simulation.options.country, add_zero_line=True
    )
