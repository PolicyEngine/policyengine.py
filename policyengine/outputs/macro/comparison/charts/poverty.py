import plotly.express as px
import plotly.graph_objects as go
import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation
    from policyengine.outputs.macro.comparison.calculate_economy_comparison import (
        PovertyRateMetricComparison,
    )

from pydantic import BaseModel
from policyengine.utils.charts import *
from typing import Literal


def create_poverty_chart(
    simulation: "Simulation",
    age_group: str,
    gender: str,
    racial_group: str,
    poverty_rate: str,
    rate_relative: bool,
    change_relative: bool = True,
) -> go.Figure:
    """Create a budget comparison chart."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    economy = simulation.calculate_economy_comparison()

    def poverty_filter(comparison: "PovertyRateMetricComparison"):
        if age_group is not None:
            if comparison.age_group != age_group:
                return False
        if racial_group is not None:
            if comparison.racial_group != racial_group:
                return False
        if gender is not None:
            if comparison.gender != gender:
                return False
        if poverty_rate is not None:
            if comparison.poverty_rate != poverty_rate:
                return False
        if rate_relative is not None:
            if comparison.relative != rate_relative:
                return False
        return True

    poverty_rates = list(
        filter(
            poverty_filter,
            economy.poverty,
        )
    )

    if len(poverty_rates) == 0:
        raise ValueError("No data found for the selected filters.")

    overall_poverty_rate = list(
        filter(
            lambda comparison: comparison.age_group == "all"
            and comparison.racial_group == "all"
            and comparison.gender == "all"
            and comparison.poverty_rate == (poverty_rate or "regular"),
            economy.poverty,
        )
    )[0].relative_change

    overall_poverty_rate = round(overall_poverty_rate, 3)

    if overall_poverty_rate > 0:
        description = f"raise the {'deep ' if poverty_rate == 'deep' else ''}poverty rate by {overall_poverty_rate:.1%}"
    elif overall_poverty_rate < 0:
        description = f"lower the {'deep ' if poverty_rate == 'deep' else ''}poverty rate by {-overall_poverty_rate:.1%}"
    else:
        description = "have no effect on the poverty rate"

    if age_group is None:
        x_values = [poverty.age_group for poverty in poverty_rates]
        x_titles = ["Child", "Working-age", "Senior", "All"]
    elif gender is None:
        x_values = [poverty.gender for poverty in poverty_rates]
        x_titles = ["Male", "Female", "All"]
    elif racial_group is None:
        x_values = [poverty.racial_group for poverty in poverty_rates]
        x_titles = ["White", "Black", "Hispanic", "Other", "All"]
    elif poverty_rate is None:
        x_values = [poverty.poverty_rate for poverty in poverty_rates]
        x_titles = ["Regular", "Deep", "All"]
    elif rate_relative is None:
        x_values = [poverty.relative for poverty in poverty_rates]
        x_titles = ["Relative", "Headcount", "All"]

    if change_relative:
        y_values = [poverty.relative_change for poverty in poverty_rates]
    elif not rate_relative:
        y_values = [poverty.change for poverty in poverty_rates]
    else:
        y_values = [poverty.change * 100 for poverty in poverty_rates]

    colors = [BLUE if value > 0 else DARK_GRAY for value in y_values]
    text = [
        (
            f"{value:.1%}"
            if change_relative
            else (f"{value:,.0f}" if not rate_relative else f"{value:.1f}pp")
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
        yaxis_title="Poverty rate change"
        + (" (%)" if rate_relative and not change_relative else ""),
        yaxis_tickformat=(
            ".0%"
            if change_relative
            else (",.0f" if not rate_relative else ".1f")
        ),
        yaxis_ticksuffix=(
            "pp" if (rate_relative and not change_relative) else ""
        ),
        xaxis_title="Group",
        xaxis_tickvals=x_values,
        xaxis_ticktext=x_titles,
    )

    return format_fig(
        fig, country=simulation.options.country, add_zero_line=True
    )
