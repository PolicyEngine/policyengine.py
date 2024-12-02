from policyengine import Simulation
import pandas as pd
from policyengine.utils.huggingface import download
import plotly.express as px
from policyengine.utils.charts import *


def parliamentary_constituencies(
    simulation: Simulation,
    chart: bool = False,
    variable: str = None,
    aggregator: str = None,
    relative: bool = None,
) -> dict:
    if not simulation.options.get("include_constituencies"):
        return {}

    if chart:
        return heatmap(
            simulation=simulation,
            variable=variable,
            aggregator=aggregator,
            relative=relative,
        )

    constituency_baseline = simulation.calculate(
        "macro/baseline/gov/local_areas/parliamentary_constituencies"
    )
    constituency_reform = simulation.calculate(
        "macro/reform/gov/local_areas/parliamentary_constituencies"
    )

    result = {}

    for constituency in constituency_baseline:
        result[constituency] = {}
        for key in constituency_baseline[constituency]:
            result[constituency][key] = {
                "change": constituency_reform[constituency][key]
                - constituency_baseline[constituency][key],
                "baseline": constituency_baseline[constituency][key],
                "reform": constituency_reform[constituency][key],
            }

    return result


def heatmap(
    simulation: Simulation,
    variable: str = None,
    aggregator: str = None,
    relative: bool = None,
) -> dict:
    if not simulation.options.get("include_constituencies"):
        return {}

    options = {}

    if variable is not None:
        options["variables"] = [variable]
    if aggregator is not None:
        options["aggregator"] = aggregator

    constituency_baseline = simulation.calculate(
        "macro/baseline/gov/local_areas/parliamentary_constituencies",
        **options,
    )
    constituency_reform = simulation.calculate(
        "macro/reform/gov/local_areas/parliamentary_constituencies", **options
    )

    result = {}

    constituency_names_file_path = download(
        repo="policyengine/policyengine-uk-data",
        repo_filename="constituencies_2024.csv",
        local_folder=None,
        version=None,
    )
    constituency_names = pd.read_csv(constituency_names_file_path)

    if variable is None:
        variable = "household_net_income"
    if relative is None:
        relative = True

    for constituency in constituency_baseline:
        if relative:
            result[constituency] = (
                constituency_reform[constituency][variable]
                / constituency_baseline[constituency][variable]
                - 1
            )
        else:
            result[constituency] = (
                constituency_reform[constituency][variable]
                - constituency_baseline[constituency][variable]
            )

    x_range = constituency_names["x"].max() - constituency_names["x"].min()
    y_range = constituency_names["y"].max() - constituency_names["y"].min()
    # Expand x range to preserve aspect ratio
    expanded_lower_x_range = -(y_range - x_range) / 2
    expanded_upper_x_range = x_range - expanded_lower_x_range
    constituency_names.x = (
        constituency_names.x - (constituency_names.y % 2 == 0) * 0.5
    )
    constituency_names["Relative change"] = (
        pd.Series(list(result.values()), index=list(result.keys()))
        .loc[constituency_names["name"]]
        .values
    )

    label = simulation.baseline.tax_benefit_system.variables[variable].label

    fig = px.scatter(
        constituency_names,
        x="x",
        y="y",
        color="Relative change",
        hover_name="name",
        title=f"{'Relative change' if relative else 'Change'} in {label} by parliamentary constituency",
    )

    format_fig(fig)

    # Show hexagons on scatter points

    fig.update_traces(
        marker=dict(
            symbol="hexagon", line=dict(width=0, color="lightgray"), size=15
        )
    )
    fig.update_layout(
        xaxis_tickvals=[],
        xaxis_title="",
        yaxis_tickvals=[],
        yaxis_title="",
        xaxis_range=[expanded_lower_x_range, expanded_upper_x_range],
        yaxis_range=[
            constituency_names["y"].min(),
            constituency_names["y"].max(),
        ],
    ).update_traces(marker_size=10).update_layout(
        xaxis_range=[30, 85], yaxis_range=[-50, 2]
    )

    x_min = fig.data[0]["marker"]["color"].min()
    x_max = fig.data[0]["marker"]["color"].max()
    max_abs = max(abs(x_min), abs(x_max))

    fig.update_layout(
        coloraxis=dict(
            cmin=-max_abs,
            cmax=max_abs,
            colorscale=[
                [0, DARK_GRAY],
                [0.5, "lightgray"],
                [1, BLUE],
            ],
            colorbar=dict(
                tickformat=".0%" if relative else ",.0f",
            ),
        )
    )

    return fig
