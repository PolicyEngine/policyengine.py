import plotly.graph_objects as go
from IPython.core.display import HTML, display_html
import pkg_resources


def add_fonts():
    fonts = HTML(
        """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto+Serif:ital,opsz,wght@0,8..144,100..900;1,8..144,100..900&display=swap" rel="stylesheet">
    """
    )
    return display_html(fonts)


GREEN = "#29d40f"
LIGHT_GREEN = "#C5E1A5"
DARK_GREEN = "#558B2F"
BLUE_LIGHT = "#D8E6F3"
BLUE_PRIMARY = BLUE = "#2C6496"
BLUE_PRESSED = "#17354F"
BLUE_98 = "#F7FAFD"
TEAL_LIGHT = "#D7F4F2"
TEAL_ACCENT = "#39C6C0"
TEAL_PRESSED = "#227773"
DARKEST_BLUE = "#0C1A27"
DARK_GRAY = "#616161"
GRAY = "#808080"
LIGHT_GRAY = "#F2F2F2"
MEDIUM_DARK_GRAY = "#D2D2D2"
WHITE = "#FFFFFF"
TEAL_98 = "#F7FDFC"
BLACK = "#000000"
FOG_GRAY = "#F4F4F4"

BLUE_COLOR_SCALE = [
    BLUE_LIGHT,
    BLUE_PRIMARY,
    BLUE_PRESSED,
]


def get_version_number(package):
    return pkg_resources.get_distribution(package).version


def format_fig(
    fig: go.Figure, country: str = "uk", add_zero_line: bool = False
) -> go.Figure:
    """Format a plotly figure to match the PolicyEngine style guide.

    Args:
        fig (go.Figure): A plotly figure.
        country (str): The country for which the style guide should be applied.
        add_zero_line (bool): Whether to add a zero line to the plot.

    Returns:
        go.Figure: A plotly figure with the PolicyEngine style guide applied.
    """
    fig.update_layout(
        font=dict(
            family="Roboto Serif",
            color="black",
        )
    )

    # set template
    fig.update_layout(
        template="plotly_white",
        height=600,
        width=800,
        plot_bgcolor=FOG_GRAY,  # set background color to light gray
        paper_bgcolor=FOG_GRAY,  # set paper background color to white
        # No white grid marks
        xaxis=dict(gridcolor=FOG_GRAY, zerolinecolor=FOG_GRAY),
        yaxis=dict(
            gridcolor=FOG_GRAY,
            zerolinecolor=DARK_GRAY if add_zero_line else FOG_GRAY,
        ),
    )

    fig.add_layout_image(
        dict(
            source="https://raw.githubusercontent.com/PolicyEngine/policyengine-app/master/src/images/logos/policyengine/blue.png",
            xref="paper",
            yref="paper",
            x=1.1,
            y=-0.2,
            sizex=0.15,
            sizey=0.15,
            xanchor="right",
            yanchor="bottom",
        )
    )

    version = get_version_number(f"policyengine-{country}")

    # Add bottom left chart description opposite logo
    fig.add_annotation(
        text=f"Source: PolicyEngine {country.upper()} tax-benefit microsimulation model (version {version})",
        xref="paper",
        yref="paper",
        x=0,
        y=-0.2,
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
    )
    # don't show modebar
    fig.update_layout(
        modebar=dict(
            bgcolor=FOG_GRAY,
            color=FOG_GRAY,
            activecolor=FOG_GRAY,
        ),
        margin_b=120,
        margin_t=120,
        margin_l=120,
        margin_r=120,
    )
    return fig


def cardinal(n: int) -> int:
    """Convert an integer to a cardinal string."""
    ending_number = n % 10
    if ending_number == 1:
        return f"{n}st"
    elif ending_number == 2:
        return f"{n}nd"
    elif ending_number == 3:
        return f"{n}rd"
    else:
        return f"{n}th"
