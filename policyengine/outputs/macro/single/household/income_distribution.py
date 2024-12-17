from policyengine import Simulation
import plotly.express as px
from policyengine.utils.charts import *
import plotly.graph_objects as go
import pandas as pd


def income_distribution(
    simulation: Simulation,
    chart: bool = False,
    variable: str = "household_net_income",
) -> dict:
    income = simulation.baseline_sim.calculate(variable)
    income_upper = income.quantile(0.9)
    BAND_SIZE = 5_000
    lower_income_bands = []
    counts = []
    for i in range(0, int(income_upper), BAND_SIZE):
        income_in_band = (income >= i) * (income < i + BAND_SIZE)
        lower_income_bands.append(i)
        counts.append(income_in_band.sum())

    data = pd.Series(counts, index=lower_income_bands)

    if chart:
        return income_distribution_chart(data)
    else:
        return data.to_dict()


def income_distribution_chart(data: pd.Series) -> go.Figure:

    fig = px.bar(
        x=data.index,
        y=data.values,
        labels={"x": "Income", "y": "Number of Households"},
        color_discrete_sequence=[BLUE],
    )
    fig.update_layout(
        title="Number of households by net income band",
        xaxis_title="Household net income",
        yaxis_title="Number of households",
    )

    # Add arrow pointing off the right and small note that 10% of households are excluded

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=1,
        y=0.8,
        text="Top 10% of households <br>not shown",
        showarrow=True,
        arrowhead=2,
        # arrow pointing left
        ax=-110,
        ay=0,
    )
    return format_fig(fig)
