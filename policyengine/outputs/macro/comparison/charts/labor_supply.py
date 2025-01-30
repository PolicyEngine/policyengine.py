import plotly.express as px
import plotly.graph_objects as go
import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation
    from policyengine.outputs.macro.comparison.calculate_economy_comparison import (
        LaborSupplyMetricImpact,
    )

from pydantic import BaseModel
from policyengine.utils.charts import *
from typing import Literal


def create_labor_supply_chart(
    simulation: "Simulation",
    decile: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "all"] | None,
    elasticity: Literal["income", "substitution", "all"] | None,
    unit: Literal["earnings", "hours"] | None,
    change_relative: bool = True,
    change_average: bool = False,
) -> go.Figure:
    """Create a budget comparison chart."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    economy = simulation.calculate_economy_comparison()

    def lsr_filter(comparison: "LaborSupplyMetricImpact"):
        if decile is not None:
            if comparison.decile != decile:
                return False
        if elasticity is not None:
            if comparison.elasticity != elasticity:
                return False
        if unit is not None:
            if comparison.unit != unit:
                return False
        return True

    overall_lsr_impact = list(
        filter(
            lambda comparison: comparison.decile == "all"
            and comparison.elasticity == "all"
            and comparison.unit == "earnings",
            economy.labor_supply,
        )
    )[0].relative_change

    overall_lsr_impact = round(overall_lsr_impact, 3)

    if overall_lsr_impact > 0:
        description = f"raise labor supply by {overall_lsr_impact:.1%}"
    elif overall_lsr_impact < 0:
        description = f"lower labor supply by {-overall_lsr_impact:.1%}"
    else:
        description = "have no effect on labor supply"

    lsr_impacts = list(
        filter(
            lsr_filter,
            economy.labor_supply,
        )
    )

    if decile is None:
        x_values = [lsr.decile for lsr in lsr_impacts]
        x_titles = list(range(1, 11))
    elif elasticity is None:
        x_values = [lsr.elasticity for lsr in lsr_impacts]
        x_titles = ["Income", "Substitution", "All"]
    elif unit is None:
        x_values = [lsr.unit for lsr in lsr_impacts]
        x_titles = ["Earnings", "Hours"]

    if change_relative:
        y_values = [lsr.relative_change for lsr in lsr_impacts]
    elif change_average:
        y_values = [lsr.average_change for lsr in lsr_impacts]
    else:
        y_values = [lsr.change / 1e9 for lsr in lsr_impacts]

    colors = [BLUE if value > 0 else DARK_GRAY for value in y_values]
    text = [
        (
            f"{value:.1%}"
            if change_relative
            else (
                f"{value:,.1%}"
                if change_relative
                else (
                    f"${value:.1f}bn"
                    if not change_average
                    else f"${value:,.0f}"
                )
            )
        )
        for value in y_values
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=x_values,
                y=y_values,
                marker=dict(color=colors),
                text=text,
            )
        ]
    ).update_layout(
        title=f"{simulation.options.title} would {description}",
        yaxis_title="Labor supply change"
        + (" ($bn)" if not change_average else ""),
        yaxis_tickformat=(".0%" if change_relative else ",.0f"),
        yaxis_ticksuffix=(
            " ($bn)" if not change_average and not change_relative else ""
        ),
        xaxis_title="Group",
        xaxis_tickvals=x_values,
        xaxis_ticktext=x_titles,
    )

    return format_fig(
        fig, country=simulation.options.country, add_zero_line=True
    )
