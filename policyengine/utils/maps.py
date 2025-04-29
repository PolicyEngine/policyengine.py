import pandas as pd
import plotly.express as px
import pandas as pd
from policyengine.utils.data_download import download
import plotly.express as px
from policyengine.utils.charts import *


def get_location_options_table(location_type: str) -> pd.DataFrame:
    if location_type == "parliamentary_constituencies":
        area_names_file_path = download(
            repo="policyengine/policyengine-uk-data",
            filepath="constituencies_2024.csv",
        )
    elif location_type == "local_authorities":
        area_names_file_path = download(
            repo="policyengine/policyengine-uk-data",
            filepath="local_authorities_2021.csv",
        )
    df = pd.read_csv(area_names_file_path)
    return df


def plot_hex_map(value_by_area_name: dict, location_type: str) -> dict:
    if location_type == "parliamentary_constituencies":
        x_bounds = [30, 85]
        y_bounds = [-50, 2]
    elif location_type == "local_authorities":
        x_bounds = [-20, 25]
        y_bounds = [-10, 35]
    else:
        raise ValueError("Invalid location_type: " + location_type)

    area_names = get_location_options_table(location_type)

    x_range = area_names["x"].max() - area_names["x"].min()
    y_range = area_names["y"].max() - area_names["y"].min()
    # Expand x range to preserve aspect ratio
    expanded_lower_x_range = -(y_range - x_range) / 2
    expanded_upper_x_range = x_range - expanded_lower_x_range
    area_names.x = area_names.x - (area_names.y % 2 == 0) * 0.5
    area_names["Value"] = (
        pd.Series(
            list(value_by_area_name.values()),
            index=list(value_by_area_name.keys()),
        )
        .loc[area_names["name"]]
        .values
    )

    fig = px.scatter(
        area_names,
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
            area_names["y"].min(),
            area_names["y"].max(),
        ],
    ).update_traces(marker_size=10).update_layout(
        xaxis_range=x_bounds, yaxis_range=y_bounds
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
