from policyengine.model_api import *
from policyengine.charts import *
import plotly.graph_objects as go
from policyengine.outputs import ChangeByQuantileGroup
from typing import Literal
from enum import Enum

class ComparisonType(Enum):
    total_change = "total_change"
    relative_change = "relative_change"
    average_change_per_household = "average_change_per_household"

def create_quantile_group_chart(
    country: str,
    dataset: Dataset,
    reform: Policy,
    baseline: Policy = current_law,
    year: str = "2025",
    quantile_groups: int = 10,
    decile_variable: str = "household_net_income",
    change_variable: str = "household_net_income",
    comparison: ComparisonType = ComparisonType.average_change_per_household,
) -> go.Figure:
    """Create a decile chart showing the impact of a reform on different deciles.

    Args:
        country (str): The country for which the chart should be created.
        baseline (Policy): The baseline policy.
        reform (Policy): The reform policy.
        dataset (Dataset): The dataset.
        year (str): The year for which to calculate the impact.
        decile_variable (str): The variable to use for decile ranking.
        change_variable (str): The variable to use for the impact calculation.

    Returns:
        go.Figure: A plotly figure showing the impact of the reform on different deciles.
    """
    
    selection = []

    for i in range(1, quantile_groups + 1):
        selection.append(ChangeByQuantileGroup(
            country=country,
            baseline=baseline,
            reform=reform,
            dataset=dataset,
            year=year,
            quantile_group=i,
            quantile_groups=quantile_groups,
            decile_variable=decile_variable,
            change_variable=change_variable,
        ))
    
    results = ResultSet(outputs=selection)

    results.compute(verbose=True)

    df = results.dataframe()

    fig = BarChart(
        country=country,
        df=df,
        x="quantile_group",
        y=comparison,
        title=f"Impact of reform on {change_variable} by quantile group",
    ).create()

    return fig