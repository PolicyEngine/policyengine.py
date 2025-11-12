"""Example: Calculate total employment income by income band.

This script demonstrates:
1. Creating a dataset with randomly sampled incomes (exponential distribution)
2. Using Aggregate to calculate statistics within income bands
3. Filtering with geq/leq constraints
4. Visualising results with Plotly

Run: python examples/income_bands.py
"""

import numpy as np
import pandas as pd
from microdf import MicroDataFrame
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from policyengine.core import Simulation
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest,
)
from policyengine.outputs.aggregate import Aggregate, AggregateType

# Create sample data with random incomes (simplified - no simulation needed)
np.random.seed(42)
n_people = 1000

person_df = MicroDataFrame(
    pd.DataFrame(
        {
            "person_id": range(1, n_people + 1),
            "benunit_id": range(1, n_people + 1),
            "household_id": range(1, n_people + 1),
            "age": np.random.randint(18, 70, n_people),
            "employment_income": np.random.exponential(35000, n_people),
            "person_weight": np.ones(n_people),
        }
    ),
    weights="person_weight",
)

benunit_df = MicroDataFrame(
    pd.DataFrame(
        {
            "benunit_id": range(1, n_people + 1),
            "benunit_weight": np.ones(n_people),
        }
    ),
    weights="benunit_weight",
)

household_df = MicroDataFrame(
    pd.DataFrame(
        {
            "household_id": range(1, n_people + 1),
            "household_weight": np.ones(n_people),
        }
    ),
    weights="household_weight",
)

# Create dataset (this serves as our output dataset)
dataset = PolicyEngineUKDataset(
    name="Sample Dataset",
    description="Random sample for testing",
    filepath="./sample_data.h5",
    year=2024,
    data=UKYearData(
        person=person_df, benunit=benunit_df, household=household_df
    ),
)

# Create simulation with dataset as output
simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
    output_dataset=dataset,
)

# Calculate total income by 10k bands
bands = []
totals = []
counts = []

for lower in range(0, 100000, 10000):
    upper = lower + 10000

    agg = Aggregate(
        simulation=simulation,
        variable="employment_income",
        aggregate_type=AggregateType.SUM,
        filter_variable="employment_income",
        filter_variable_geq=lower,
        filter_variable_leq=upper,
    )
    agg.run()

    count_agg = Aggregate(
        simulation=simulation,
        variable="employment_income",
        aggregate_type=AggregateType.COUNT,
        filter_variable="employment_income",
        filter_variable_geq=lower,
        filter_variable_leq=upper,
    )
    count_agg.run()

    bands.append(f"£{lower // 1000}k-£{upper // 1000}k")
    totals.append(agg.result)
    counts.append(count_agg.result)

# Calculate 100k+ band
agg = Aggregate(
    simulation=simulation,
    variable="employment_income",
    aggregate_type=AggregateType.SUM,
    filter_variable="employment_income",
    filter_variable_geq=100000,
)
agg.run()

count_agg = Aggregate(
    simulation=simulation,
    variable="employment_income",
    aggregate_type=AggregateType.COUNT,
    filter_variable="employment_income",
    filter_variable_geq=100000,
)
count_agg.run()

bands.append("£100k+")
totals.append(agg.result)
counts.append(count_agg.result)

# Create chart
fig = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=("Total income by band", "Population by band"),
    specs=[[{"type": "bar"}, {"type": "bar"}]],
)

fig.add_trace(
    go.Bar(x=bands, y=totals, name="Total income", marker_color="lightblue"),
    row=1,
    col=1,
)

fig.add_trace(
    go.Bar(x=bands, y=counts, name="Count", marker_color="lightgreen"),
    row=1,
    col=2,
)

fig.update_xaxes(title_text="Income band", row=1, col=1)
fig.update_xaxes(title_text="Income band", row=1, col=2)
fig.update_yaxes(title_text="Total income (£)", row=1, col=1)
fig.update_yaxes(title_text="Number of people", row=1, col=2)

fig.update_layout(
    title_text="Employment income distribution",
    showlegend=False,
    height=400,
)

fig.show()
