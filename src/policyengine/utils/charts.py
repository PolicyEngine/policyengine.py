"""Chart formatting utilities for PolicyEngine."""

import plotly.graph_objects as go
from IPython.display import HTML

COLOUR_SCHEMES = {
    "teal": {
        "primary": "#319795",
        "secondary": "#38B2AC",
        "tertiary": "#4FD1C5",
        "light": "#81E6D9",
        "lighter": "#B2F5EA",
        "lightest": "#E6FFFA",
        "dark": "#2C7A7B",
        "darker": "#285E61",
        "darkest": "#234E52",
    },
    "blue": {
        "primary": "#0EA5E9",
        "secondary": "#0284C7",
        "tertiary": "#38BDF8",
        "light": "#7DD3FC",
        "lighter": "#BAE6FD",
        "lightest": "#E0F2FE",
        "dark": "#026AA2",
        "darker": "#075985",
        "darkest": "#0C4A6E",
    },
    "gray": {
        "primary": "#6B7280",
        "secondary": "#9CA3AF",
        "tertiary": "#D1D5DB",
        "light": "#E2E8F0",
        "lighter": "#F2F4F7",
        "lightest": "#F9FAFB",
        "dark": "#4B5563",
        "darker": "#344054",
        "darkest": "#101828",
    },
}

DEFAULT_COLOURS = [
    COLOUR_SCHEMES["teal"]["primary"],
    COLOUR_SCHEMES["blue"]["primary"],
    COLOUR_SCHEMES["teal"]["secondary"],
    COLOUR_SCHEMES["blue"]["secondary"],
    COLOUR_SCHEMES["teal"]["tertiary"],
    COLOUR_SCHEMES["blue"]["tertiary"],
    COLOUR_SCHEMES["gray"]["dark"],
    COLOUR_SCHEMES["teal"]["dark"],
]


def add_fonts() -> HTML:
    """Return HTML to add Google Fonts for Roboto and Roboto Mono."""
    return HTML("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
    """)


def format_figure(
    fig: go.Figure,
    title: str | None = None,
    x_title: str | None = None,
    y_title: str | None = None,
    colour_scheme: str = "teal",
    show_grid: bool = True,
    show_legend: bool = True,
    height: int | None = None,
    width: int | None = None,
) -> go.Figure:
    """Apply consistent formatting to a Plotly figure.

    Args:
        fig: The Plotly figure to format
        title: Optional title for the chart
        x_title: Optional x-axis title
        y_title: Optional y-axis title
        colour_scheme: Colour scheme name (teal, blue, gray)
        show_grid: Whether to show gridlines
        show_legend: Whether to show the legend
        height: Optional figure height in pixels
        width: Optional figure width in pixels

    Returns:
        The formatted figure
    """

    colours = COLOUR_SCHEMES.get(colour_scheme, COLOUR_SCHEMES["teal"])

    # Update traces with colour scheme
    for i, trace in enumerate(fig.data):
        if hasattr(trace, "marker"):
            trace.marker.color = DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)]
        if hasattr(trace, "line"):
            trace.line.color = DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)]
            trace.line.width = 2

    # Base layout settings
    layout_updates = {
        "font": {
            "family": "Roboto, sans-serif",
            "size": 14,
            "color": COLOUR_SCHEMES["gray"]["darkest"],
        },
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "showlegend": show_legend,
        "hovermode": "x unified",
        "hoverlabel": {
            "bgcolor": "white",
            "font": {"family": "Roboto Mono, monospace", "size": 12},
            "bordercolor": colours["light"],
        },
    }

    # Add title if provided
    if title:
        layout_updates["title"] = {
            "text": title,
            "font": {
                "family": "Roboto, sans-serif",
                "size": 20,
                "color": COLOUR_SCHEMES["gray"]["darkest"],
                "weight": 500,
            },
        }

    # Configure axes
    axis_config = {
        "showgrid": show_grid,
        "gridcolor": COLOUR_SCHEMES["gray"]["light"],
        "gridwidth": 1,
        "zeroline": True,
        "zerolinecolor": COLOUR_SCHEMES["gray"]["lighter"],
        "zerolinewidth": 1,
        "tickfont": {
            "family": "Roboto Mono, monospace",
            "size": 11,
            "color": COLOUR_SCHEMES["gray"]["primary"],
        },
        "titlefont": {
            "family": "Roboto, sans-serif",
            "size": 14,
            "color": COLOUR_SCHEMES["gray"]["dark"],
        },
        "linecolor": COLOUR_SCHEMES["gray"]["light"],
        "linewidth": 1,
        "showline": True,
        "mirror": False,
    }

    layout_updates["xaxis"] = axis_config.copy()
    layout_updates["yaxis"] = axis_config.copy()

    if x_title:
        layout_updates["xaxis"]["title"] = x_title
    if y_title:
        layout_updates["yaxis"]["title"] = y_title

    layout_updates["showlegend"] = len(fig.data) > 1 and show_legend

    # Set dimensions if provided
    if height:
        layout_updates["height"] = height
    if width:
        layout_updates["width"] = width

    fig.update_layout(**layout_updates)

    fig.update_xaxes(title_font_color=COLOUR_SCHEMES["gray"]["primary"])
    fig.update_yaxes(title_font_color=COLOUR_SCHEMES["gray"]["primary"])

    # Add text annotations to bars in bar charts
    if any(isinstance(trace, go.Bar) for trace in fig.data):
        for trace in fig.data:
            if isinstance(trace, go.Bar):
                trace.texttemplate = "%{y:,.0f}"
                trace.textposition = "outside"
                trace.textfont = {
                    "family": "Roboto Mono, monospace",
                    "size": 11,
                    "color": COLOUR_SCHEMES["gray"]["primary"],
                }

    return fig


def create_bar_chart(
    data: dict[str, list],
    x: str,
    y: str,
    title: str | None = None,
    colour_scheme: str = "teal",
    **kwargs,
) -> go.Figure:
    """Create a formatted bar chart.

    Args:
        data: Dictionary with data for the chart
        x: Column name for x-axis
        y: Column name for y-axis
        title: Optional chart title
        colour_scheme: Colour scheme to use
        **kwargs: Additional arguments for format_figure

    Returns:
        Formatted bar chart figure
    """
    fig = go.Figure(
        data=[
            go.Bar(
                x=data[x],
                y=data[y],
                marker_color=COLOUR_SCHEMES[colour_scheme]["primary"],
                marker_line_color=COLOUR_SCHEMES[colour_scheme]["dark"],
                marker_line_width=1,
                hovertemplate=f"{x}: "
                + "%{x}<br>"
                + f"{y}: "
                + "%{y:,.0f}<extra></extra>",
            )
        ]
    )

    return format_figure(
        fig,
        title=title,
        x_title=x,
        y_title=y,
        colour_scheme=colour_scheme,
        **kwargs,
    )


def create_line_chart(
    data: dict[str, list],
    x: str,
    y: str | list[str],
    title: str | None = None,
    colour_scheme: str = "teal",
    **kwargs,
) -> go.Figure:
    """Create a formatted line chart.

    Args:
        data: Dictionary with data for the chart
        x: Column name for x-axis
        y: Column name(s) for y-axis (can be a list for multiple lines)
        title: Optional chart title
        colour_scheme: Colour scheme to use
        **kwargs: Additional arguments for format_figure

    Returns:
        Formatted line chart figure
    """
    traces = []
    y_columns = y if isinstance(y, list) else [y]

    for i, y_col in enumerate(y_columns):
        traces.append(
            go.Scatter(
                x=data[x],
                y=data[y_col],
                mode="lines+markers",
                name=y_col,
                line=dict(
                    color=DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)], width=2
                ),
                marker=dict(size=6),
                hovertemplate=f"{y_col}: " + "%{y:,.0f}<extra></extra>",
            )
        )

    fig = go.Figure(data=traces)

    return format_figure(
        fig,
        title=title,
        x_title=x,
        y_title=y_columns[0] if len(y_columns) == 1 else None,
        colour_scheme=colour_scheme,
        **kwargs,
    )
