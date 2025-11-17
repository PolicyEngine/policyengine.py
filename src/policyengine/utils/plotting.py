"""Plotting utilities for PolicyEngine visualisations."""

import plotly.graph_objects as go

# PolicyEngine brand colours
COLORS = {
    "primary": "#319795",  # Teal
    "primary_light": "#E6FFFA",
    "primary_dark": "#1D4044",
    "success": "#22C55E",  # Green (positive changes)
    "warning": "#FEC601",  # Yellow (cautions)
    "error": "#EF4444",  # Red (negative changes)
    "info": "#1890FF",  # Blue (neutral info)
    "gray_light": "#F2F4F7",
    "gray": "#667085",
    "gray_dark": "#101828",
    "blue_secondary": "#026AA2",
}

# Typography
FONT_FAMILY = (
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
)
FONT_SIZE_LABEL = 12
FONT_SIZE_DEFAULT = 14
FONT_SIZE_TITLE = 16


def format_fig(
    fig: go.Figure,
    title: str | None = None,
    xaxis_title: str | None = None,
    yaxis_title: str | None = None,
    show_legend: bool = True,
    height: int | None = None,
    width: int | None = None,
) -> go.Figure:
    """Apply PolicyEngine visual style to a plotly figure.

    Applies professional, clean styling following PolicyEngine design principles:
    - Data-driven clarity prioritising immediate understanding
    - Professional brand colours (teal primary, semantic colours)
    - Clean typography with Inter font family
    - Minimal visual clutter
    - Appropriate spacing and margins

    Args:
        fig: Plotly figure to format
        title: Optional title to set/override
        xaxis_title: Optional x-axis title to set/override
        yaxis_title: Optional y-axis title to set/override
        show_legend: Whether to show the legend (default: True)
        height: Optional height in pixels
        width: Optional width in pixels

    Returns:
        Formatted plotly figure (same object, modified in place)

    Example:
        >>> import plotly.graph_objects as go
        >>> from policyengine.utils import format_fig
        >>> fig = go.Figure(data=go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        >>> format_fig(fig, title="Example chart", xaxis_title="X", yaxis_title="Y")
    """
    # Build layout updates
    layout_updates = {
        "font": {
            "family": FONT_FAMILY,
            "size": FONT_SIZE_DEFAULT,
            "color": COLORS["gray_dark"],
        },
        "plot_bgcolor": "#FAFAFA",
        "paper_bgcolor": "white",
        "margin": {"l": 100, "r": 60, "t": 100, "b": 80},
        "showlegend": show_legend,
        "xaxis": {
            "title": {
                "font": {
                    "size": FONT_SIZE_DEFAULT,
                    "family": FONT_FAMILY,
                    "color": COLORS["gray_dark"],
                },
                "standoff": 20,
            },
            "tickfont": {
                "size": FONT_SIZE_LABEL,
                "family": FONT_FAMILY,
                "color": COLORS["gray"],
            },
            "showgrid": False,
            "showline": True,
            "linewidth": 2,
            "linecolor": COLORS["gray_light"],
            "zeroline": False,
            "ticks": "outside",
            "tickwidth": 1,
            "tickcolor": COLORS["gray_light"],
        },
        "yaxis": {
            "title": {
                "font": {
                    "size": FONT_SIZE_DEFAULT,
                    "family": FONT_FAMILY,
                    "color": COLORS["gray_dark"],
                },
                "standoff": 20,
            },
            "tickfont": {
                "size": FONT_SIZE_LABEL,
                "family": FONT_FAMILY,
                "color": COLORS["gray"],
            },
            "showgrid": True,
            "gridwidth": 1,
            "gridcolor": "#E5E7EB",
            "showline": False,
            "zeroline": False,
        },
        "legend": {
            "bgcolor": "white",
            "bordercolor": COLORS["gray_light"],
            "borderwidth": 1,
            "font": {"size": FONT_SIZE_LABEL, "family": FONT_FAMILY},
            "orientation": "v",
            "yanchor": "top",
            "y": 0.99,
            "xanchor": "right",
            "x": 0.99,
        },
    }

    # Add optional parameters
    if title is not None:
        layout_updates["title"] = {
            "text": title,
            "font": {
                "size": 18,
                "family": FONT_FAMILY,
                "color": COLORS["gray_dark"],
                "weight": 600,
            },
            "x": 0,
            "xanchor": "left",
            "y": 0.98,
            "yanchor": "top",
        }

    if xaxis_title is not None:
        layout_updates["xaxis"]["title"]["text"] = xaxis_title

    if yaxis_title is not None:
        layout_updates["yaxis"]["title"]["text"] = yaxis_title

    if height is not None:
        layout_updates["height"] = height

    if width is not None:
        layout_updates["width"] = width

    # Apply layout
    fig.update_layout(**layout_updates)

    # Update all traces to have cleaner styling
    fig.update_traces(
        marker=dict(size=8, line=dict(width=0)),
        line=dict(width=3),
        selector=dict(mode="markers+lines"),
    )
    fig.update_traces(
        marker=dict(size=8, line=dict(width=0)),
        selector=dict(mode="markers"),
    )
    fig.update_traces(
        line=dict(width=3),
        selector=dict(mode="lines"),
    )

    return fig
