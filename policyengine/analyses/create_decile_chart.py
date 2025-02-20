from policyengine.model_api import *
from policyengine.charts import *
import plotly.graph_objects as go
from policyengine.outputs import ImpactByDecile

def create_decile_chart(
    country: str,
    baseline: Policy,
    reform: Policy,
    dataset: Dataset,
    year: str = "2025",
    decile_variable: str = "household_net_income",
    impact_variable: str = "household_net_income",
) -> go.Figure:
    """Create a decile chart showing the impact of a reform on different deciles.

    Args:
        country (str): The country for which the chart should be created.
        baseline (Policy): The baseline policy.
        reform (Policy): The reform policy.
        dataset (Dataset): The dataset.
        year (str): The year for which to calculate the impact.
        decile_variable (str): The variable to use for decile ranking.
        impact_variable (str): The variable to use for the impact calculation.

    Returns:
        go.Figure: A plotly figure showing the impact of the reform on different deciles.
    """
    
    selection = []

    for i in range(1, 11):
        selection.append(ImpactByDecile(
            country=country,
            baseline=baseline,
            reform=reform,
            dataset=dataset,
            year=year,
            decile=i,
            decile_variable=decile_variable,
            impact_variable=impact_variable,
        ))
    
    results = ResultSet(outputs=selection)

    results.compute()

    df = results.dataframe()

    fig = BarChart(
        country=country,
        df=df,
        x="decile",
        y="output",
        title=f"Impact of reform on {impact_variable} by decile",
    ).create()

    return fig