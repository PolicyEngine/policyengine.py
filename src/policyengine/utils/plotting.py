"""Plotting utilities for PolicyEngine visualisations.

Requires plotly, which is installed via the ``[plotting]`` extra
(``pip install policyengine[plotting]``). Importing from this module
fails with a clear error when plotly is absent. Brand tokens
(``COLORS``, font constants) live in :mod:`policyengine.utils.design`
so they can be imported without plotly.
"""

from typing import TYPE_CHECKING, Optional

try:
    import plotly.graph_objects as go
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "policyengine.utils.plotting requires plotly. "
        "Install with: pip install policyengine[plotting]"
    ) from exc

if TYPE_CHECKING:
    import plotly.graph_objects as go  # noqa: F401

from .design import (
    COLORS,
    FONT_FAMILY,
    FONT_SIZE_DEFAULT,
    FONT_SIZE_LABEL,
    FONT_SIZE_TITLE,
)

__all__ = [
    "COLORS",
    "FONT_FAMILY",
    "FONT_SIZE_DEFAULT",
    "FONT_SIZE_LABEL",
    "FONT_SIZE_TITLE",
    "format_fig",
]


def format_fig(
    fig: go.Figure,
    title: Optional[str] = None,
    xaxis_title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    show_legend: bool = True,
    height: Optional[int] = None,
    width: Optional[int] = None,
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
