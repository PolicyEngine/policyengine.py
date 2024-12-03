import pandas as pd
import plotly.express as px
from policyengine import Simulation
import pandas as pd
from policyengine.utils.huggingface import download
import plotly.express as px
from policyengine.utils.charts import *


def plot_hex_map(value_by_constituency_name: dict) -> dict:
    constituency_names_file_path = download(
        repo="policyengine/policyengine-uk-data",
        repo_filename="constituencies_2024.csv",
        local_folder=None,
        version=None,
    )
    constituency_names = pd.read_csv(constituency_names_file_path)

    x_range = constituency_names["x"].max() - constituency_names["x"].min()
    y_range = constituency_names["y"].max() - constituency_names["y"].min()
    # Expand x range to preserve aspect ratio
    expanded_lower_x_range = -(y_range - x_range) / 2
    expanded_upper_x_range = x_range - expanded_lower_x_range
    constituency_names.x = (
        constituency_names.x - (constituency_names.y % 2 == 0) * 0.5
    )
    constituency_names["Value"] = (
        pd.Series(
            list(value_by_constituency_name.values()),
            index=list(value_by_constituency_name.keys()),
        )
        .loc[constituency_names["name"]]
        .values
    )

    fig = px.scatter(
        constituency_names,
        x="x",
        y="y",
        color="Value",
        hover_name="name",
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

    if x_min < 0:
        colorscale = [
            [0, DARK_GRAY],
            [0.5, "lightgray"],
            [1, BLUE],
        ]
    else:
        colorscale = [
            [0, "lightgray"],
            [1, BLUE],
        ]

    fig.update_layout(
        coloraxis=dict(
            cmin=-max_abs if x_min < 0 else 0,
            cmax=max_abs,
            colorscale=colorscale,
        )
    )

    return fig
