import plotly.express as px
import plotly.graph_objects as go
import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.charts import *


def create_budget_comparison_chart(
    simulation: "Simulation",
) -> go.Figure:
    """Create a budget comparison chart."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    economy = simulation.calculate_economy_comparison()

    if simulation.options.country == "uk":
        x_values = [
            "Tax revenues",
            "Government spending",
            "Public sector net worth",
        ]
        y_values = [
            economy.fiscal.change.federal_tax,
            economy.fiscal.change.government_spending,
            economy.fiscal.change.federal_balance,
        ]
    else:
        x_values = [
            "Federal tax revenues",
            "State tax revenues",
            "Federal government spending",
        ]
        y_values = [
            economy.fiscal.change.federal_tax,
            economy.fiscal.change.state_tax,
            economy.fiscal.change.government_spending,
        ]

    y_values = [value / 1e9 for value in y_values]

    net_change = round(economy.fiscal.change.federal_balance / 1e9, 1)

    if net_change > 0:
        description = f"raise ${net_change}bn"
    elif net_change < 0:
        description = f"cost ${-net_change}bn"
    else:
        description = "have no effect on government finances"

    chart = go.Figure(
        data=[
            go.Waterfall(
                x=x_values,
                y=y_values,
                measure=["relative"] * (len(x_values) - 1) + ["total"],
                textposition="inside",
                text=[f"${value:.1f}bn" for value in y_values],
                increasing=dict(
                    marker=dict(
                        color=BLUE,
                    )
                ),
                decreasing=dict(
                    marker=dict(
                        color=DARK_GRAY,
                    )
                ),
                totals=dict(
                    marker=dict(
                        color=BLUE if net_change > 0 else DARK_GRAY,
                    )
                ),
            ),
        ]
    ).update_layout(
        title=f"{simulation.options.title} would {description}",
        yaxis_title="Budgetary impact ($bn)",
        uniformtext=dict(
            mode="hide",
            minsize=12,
        ),
    )

    return format_fig(
        chart, country=simulation.options.country, add_zero_line=True
    )
