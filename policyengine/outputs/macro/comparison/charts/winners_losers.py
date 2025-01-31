import plotly.express as px
import plotly.graph_objects as go
import typing

if typing.TYPE_CHECKING:
    from policyengine import Simulation

from pydantic import BaseModel
from policyengine.utils.charts import *
from typing import Literal, Dict


COLOR_MAP = {
    "Gain more than 5%": BLUE,
    "Gain less than 5%": BLUE_95,
    "No change": LIGHT_GRAY,
    "Lose less than 5%": MEDIUM_LIGHT_GRAY,
    "Lose more than 5%": DARK_GRAY,
}

FORMATTED_KEYS = {
    "gain_more_than_5_percent_share": "Gain more than 5%",
    "gain_less_than_5_percent_share": "Gain less than 5%",
    "no_change_share": "No change",
    "lose_less_than_5_percent_share": "Lose less than 5%",
    "lose_more_than_5_percent_share": "Lose more than 5%",
}


def create_winners_losers_chart(
    simulation: "Simulation",
    decile_variable: Literal["income", "wealth"],
) -> go.Figure:
    """Create a budget comparison chart."""
    if not simulation.is_comparison:
        raise ValueError("Simulation must be a comparison simulation.")

    economy = simulation.calculate_economy_comparison()

    if decile_variable == "income":
        data = economy.distributional.income.winners_and_losers
    else:
        data = economy.distributional.wealth.winners_and_losers

    all_decile_data = {}
    for key in FORMATTED_KEYS.keys():
        all_decile_data[FORMATTED_KEYS[key]] = data.all.model_dump()[key]

    all_decile_chart = go.Bar(
        x=list(all_decile_data.values()),
        y=["All"] * len(all_decile_data),
        name="All deciles",
        orientation="h",
        yaxis="y",
        xaxis="x",
        showlegend=False,
        text=[f"{value:.1%}" for value in all_decile_data.values()],
        marker=dict(color=[COLOR_MAP[key] for key in all_decile_data.keys()]),
    )

    x_values = []
    y_values = []
    color_values = []
    text = []
    hover_text = []
    for outcome_type in FORMATTED_KEYS.keys():
        for decile in range(1, 11):
            value = data.deciles[decile].model_dump()[outcome_type]
            x_values.append(value)
            y_values.append(decile)
            color_values.append(COLOR_MAP[FORMATTED_KEYS[outcome_type]])
            text.append(f"{value:.1%}")
            hover_text.append(
                f"{FORMATTED_KEYS[outcome_type]}, {decile}: {value:.1%}"
            )

    decile_chart = go.Bar(
        x=x_values,
        y=y_values,
        name="Deciles",
        orientation="h",
        yaxis="y2",
        xaxis="x2",
        text=text,
        textposition="inside",
        marker=dict(
            color=color_values,
        ),
        customdata=hover_text,
        hovertemplate="%{customdata}<extra></extra>",
        # Need to sort out showlegend, currently fiddly.
    )

    fig = go.Figure(
        data=[
            all_decile_chart,
            decile_chart,
        ]
    )

    winner_share = round(
        economy.distributional.income.winners_and_losers.all.gain_share, 3
    )

    if winner_share > 0:
        description = f"raise the net income of {winner_share:.1%} of people"
    elif winner_share < 0:
        description = (
            f"decrease the net income of {-winner_share:.1%} of people"
        )
    else:
        description = "have no effect on household net income"

    fig.update_layout(
        barmode="stack",
        grid=dict(
            rows=2,
            columns=1,
        ),
        yaxis=dict(
            title="",
            tickvals=["All"],
            domain=[0.91, 1],
        ),
        xaxis=dict(
            title="",
            tickformat=".0%",
            anchor="y",
            matches="x2",
            showgrid=False,
            showticklabels=False,
            fixedrange=True,
        ),
        xaxis2=dict(
            title="Population share",
            tickformat=".0%",
            anchor="y2",
            fixedrange=True,
        ),
        yaxis2=dict(
            title="Population share",
            tickvals=list(range(1, 11)),
            anchor="x2",
            domain=[0, 0.85],
        ),
        title=f"{simulation.options.title} would {description}",
    )

    return format_fig(fig, country=simulation.options.country)
