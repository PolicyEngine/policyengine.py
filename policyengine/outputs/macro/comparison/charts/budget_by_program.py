import plotly.express as px
import plotly.graph_objects as go
import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.charts import *


def create_budget_program_comparison_chart(
    simulation: "Simulation",
) -> go.Figure:
    """Create a budget comparison chart."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    if not simulation.options.country == "uk":
        raise ValueError("This chart is only available for the UK.")

    economy = simulation.calculate_economy_comparison()

    change_programs = economy.fiscal.change.tax_benefit_programs

    change_programs = {
        program: change_programs[program]
        for program in change_programs
        if round(change_programs[program] / 1e9, 1) != 0
    }

    labels = [
        simulation.baseline_simulation.tax_benefit_system.variables.get(
            program
        ).label
        for program in change_programs
    ]

    x_values = labels
    y_values = [
        round(change_programs[program] / 1e9, 1) for program in change_programs
    ]

    total_from_programs = round(sum(y_values))
    total_overall = round(economy.fiscal.change.federal_balance / 1e9)

    if total_from_programs != total_overall:
        x_values.append("Other")
        y_values.append(total_overall - total_from_programs)

    x_values.append("Combined")
    y_values.append(total_overall)

    if total_overall > 0:
        description = f"raise ${total_overall}bn"
    elif total_overall < 0:
        description = f"cost ${-total_overall}bn"
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
                        color=BLUE if total_overall > 0 else DARK_GRAY,
                    )
                ),
            ),
        ]
    ).update_layout(
        title=f"{simulation.options.title} would {description}",
        yaxis_title="Budgetary impact (bn)",
        uniformtext=dict(
            mode="hide",
            minsize=12,
        ),
    )

    return format_fig(
        chart, country=simulation.options.country, add_zero_line=True
    )
