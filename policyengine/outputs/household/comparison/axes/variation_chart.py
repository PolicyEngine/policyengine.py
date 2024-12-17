from policyengine import Simulation
import plotly.graph_objects as go
from policyengine.utils.charts import *


def variation_chart(
    simulation: Simulation,
    target_variable: str = None,
    variable: str = "employment_income",
    variable_min: float = 0,
    variable_max: float = 200_000,
    variable_count: int = 1001,
    show_baseline: bool = False,
) -> go.Figure:
    if target_variable is None:
        return {}

    sim = Simulation(
        country=simulation.country,
        scope="household",
        baseline=simulation.baseline.reform,
        reform=simulation.reformed.reform,
        time_period=simulation.time_period,
        options=simulation.options,
        data={
            **simulation.data,
            "axes": [
                [
                    {
                        "name": variable,
                        "min": variable_min,
                        "max": variable_max,
                        "count": variable_count,
                        "period": simulation.time_period,
                    }
                ]
            ],
        },
    )

    baseline_values = sim.baseline.calculate(
        target_variable, map_to="household"
    )
    reform_values = sim.reformed.calculate(target_variable, map_to="household")
    axis_values = sim.baseline.calculate(variable, map_to="household")

    if show_baseline:
        fig = go.Figure()
        fig.add_trace(
            go.Line(
                x=axis_values,
                y=baseline_values,
                mode="lines",
                name="Baseline",
                line=dict(color=DARK_GRAY, dash="solid"),
            )
        )
        fig.add_trace(
            go.Line(
                x=axis_values,
                y=reform_values,
                mode="lines",
                name="Reform",
                line=dict(color=BLUE, dash="dash"),
            )
        )
        fig.update_layout(
            title="Impact by " + variable,
            xaxis_title=variable,
            yaxis_title=target_variable,
            xaxis_tickformat=",.0f",
            yaxis_tickformat=",.0f",
            showlegend=True,
        )
    else:
        fig = go.Figure(
            data=[
                go.Line(
                    x=axis_values,
                    y=reform_values - baseline_values,
                    mode="lines",
                    name="Reform",
                    line=dict(color=BLUE, dash="solid"),
                )
            ]
        )
        fig.update_layout(
            title="Impact by " + variable,
            xaxis_title=variable,
            yaxis_title=target_variable,
            xaxis_tickformat=",.0f",
            yaxis_tickformat=",.0f",
            showlegend=False,
        )

    return format_fig(fig, simulation.country)
