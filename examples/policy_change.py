"""Example: Analyze policy change impacts using ChangeAggregate.

This script demonstrates:
1. Creating baseline and reform datasets with different income distributions
2. Using ChangeAggregate to analyze winners, losers, and impact sizes
3. Filtering by absolute and relative change thresholds
4. Visualising results with Plotly

Run: python examples/policy_change.py
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
from policyengine.outputs.change_aggregate import ChangeAggregate, ChangeAggregateType

# Create baseline dataset with random incomes
np.random.seed(42)
n_people = 1000

baseline_person_df = MicroDataFrame(
    pd.DataFrame({
        "person_id": range(1, n_people + 1),
        "benunit_id": range(1, n_people + 1),
        "household_id": range(1, n_people + 1),
        "age": np.random.randint(18, 70, n_people),
        "employment_income": np.random.exponential(35000, n_people),
        "person_weight": np.ones(n_people),
    }),
    weights="person_weight"
)

benunit_df = MicroDataFrame(
    pd.DataFrame({
        "benunit_id": range(1, n_people + 1),
        "benunit_weight": np.ones(n_people),
    }),
    weights="benunit_weight"
)

household_df = MicroDataFrame(
    pd.DataFrame({
        "household_id": range(1, n_people + 1),
        "household_weight": np.ones(n_people),
    }),
    weights="household_weight"
)

# Create baseline dataset
baseline_dataset = PolicyEngineUKDataset(
    name="Baseline",
    description="Baseline scenario",
    filepath="./baseline_data.h5",
    year=2024,
    data=UKYearData(person=baseline_person_df, benunit=benunit_df, household=household_df),
)

# Create reform dataset - progressive income boost
# Low earners get 10% boost, high earners get 5% boost, middle gets 7.5%
baseline_incomes = baseline_person_df["employment_income"].values
reform_incomes = []
for income in baseline_incomes:
    if income < 25000:
        boost = 0.10  # 10% for low earners
    elif income < 50000:
        boost = 0.075  # 7.5% for middle earners
    else:
        boost = 0.05  # 5% for high earners
    reform_incomes.append(income * (1 + boost))

reform_person_df = MicroDataFrame(
    pd.DataFrame({
        "person_id": range(1, n_people + 1),
        "benunit_id": range(1, n_people + 1),
        "household_id": range(1, n_people + 1),
        "age": baseline_person_df["age"].values,
        "employment_income": reform_incomes,
        "person_weight": np.ones(n_people),
    }),
    weights="person_weight"
)

reform_dataset = PolicyEngineUKDataset(
    name="Reform",
    description="Progressive income boost",
    filepath="./reform_data.h5",
    year=2024,
    data=UKYearData(person=reform_person_df, benunit=benunit_df, household=household_df),
)

# Create simulations
baseline_sim = Simulation(
    dataset=baseline_dataset,
    tax_benefit_model_version=uk_latest,
    output_dataset=baseline_dataset,
)

reform_sim = Simulation(
    dataset=reform_dataset,
    tax_benefit_model_version=uk_latest,
    output_dataset=reform_dataset,
)

# Analysis 1: Overall winners/losers
winners = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="employment_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_geq=1,
)
winners.run()

losers = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="employment_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_leq=-1,
)
losers.run()

no_change = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="employment_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_eq=0,
)
no_change.run()

# Analysis 2: Total gains and losses
total_gain = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="employment_income",
    aggregate_type=ChangeAggregateType.SUM,
    change_geq=0,
)
total_gain.run()

total_loss = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="employment_income",
    aggregate_type=ChangeAggregateType.SUM,
    change_leq=0,
)
total_loss.run()

# Analysis 3: Distribution of gains by size
gain_bands = [
    ("£0-500", 0, 500),
    ("£500-1k", 500, 1000),
    ("£1k-2k", 1000, 2000),
    ("£2k-3k", 2000, 3000),
    ("£3k-5k", 3000, 5000),
    ("£5k+", 5000, None),
]

gain_counts = []
for label, lower, upper in gain_bands:
    agg = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="employment_income",
        aggregate_type=ChangeAggregateType.COUNT,
        change_geq=lower,
        change_leq=upper,
    )
    agg.run()
    gain_counts.append(agg.result)

# Analysis 4: Impact by age group
age_groups = [
    ("18-30", 18, 30),
    ("31-45", 31, 45),
    ("46-60", 46, 60),
    ("61+", 61, 150),
]

age_group_labels = []
age_group_winners = []
age_group_avg_gain = []

for label, min_age, max_age in age_groups:
    # Count winners in age group
    count_agg = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="employment_income",
        aggregate_type=ChangeAggregateType.COUNT,
        change_geq=1,
        filter_variable="age",
        filter_variable_geq=min_age,
        filter_variable_leq=max_age,
    )
    count_agg.run()

    # Average gain in age group
    mean_agg = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="employment_income",
        aggregate_type=ChangeAggregateType.MEAN,
        filter_variable="age",
        filter_variable_geq=min_age,
        filter_variable_leq=max_age,
    )
    mean_agg.run()

    age_group_labels.append(label)
    age_group_winners.append(count_agg.result)
    age_group_avg_gain.append(mean_agg.result)

# Analysis 5: Large winners (gaining more than 10%)
large_winners = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="employment_income",
    aggregate_type=ChangeAggregateType.COUNT,
    relative_change_geq=0.10,
)
large_winners.run()

# Create visualisations
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=(
        "Winners vs losers",
        "Distribution of gains",
        "Winners by age group",
        "Average gain by age group"
    ),
    specs=[[{"type": "bar"}, {"type": "bar"}],
           [{"type": "bar"}, {"type": "bar"}]]
)

fig.add_trace(
    go.Bar(
        x=["Winners", "No change", "Losers"],
        y=[winners.result, no_change.result, losers.result],
        marker_color=["green", "gray", "red"]
    ),
    row=1, col=1
)

fig.add_trace(
    go.Bar(
        x=[label for label, _, _ in gain_bands],
        y=gain_counts,
        marker_color="lightblue"
    ),
    row=1, col=2
)

fig.add_trace(
    go.Bar(
        x=age_group_labels,
        y=age_group_winners,
        marker_color="lightgreen"
    ),
    row=2, col=1
)

fig.add_trace(
    go.Bar(
        x=age_group_labels,
        y=age_group_avg_gain,
        marker_color="orange"
    ),
    row=2, col=2
)

fig.update_xaxes(title_text="Category", row=1, col=1)
fig.update_xaxes(title_text="Gain amount", row=1, col=2)
fig.update_xaxes(title_text="Age group", row=2, col=1)
fig.update_xaxes(title_text="Age group", row=2, col=2)

fig.update_yaxes(title_text="Number of people", row=1, col=1)
fig.update_yaxes(title_text="Number of people", row=1, col=2)
fig.update_yaxes(title_text="Number of winners", row=2, col=1)
fig.update_yaxes(title_text="Average gain (£)", row=2, col=2)

fig.update_layout(
    title_text="Policy change impact analysis",
    showlegend=False,
    height=800,
)

# Print summary statistics
print("=" * 60)
print("Policy change impact summary")
print("=" * 60)
print(f"\nOverall impact:")
print(f"  Winners: {winners.result:,.0f} people")
print(f"  Losers: {losers.result:,.0f} people")
print(f"  No change: {no_change.result:,.0f} people")
print(f"\nFinancial impact:")
print(f"  Total gains: £{total_gain.result:,.0f}")
print(f"  Total losses: £{total_loss.result:,.0f}")
print(f"  Net change: £{total_gain.result + total_loss.result:,.0f}")
print(f"\nLarge winners (>10% gain): {large_winners.result:,.0f} people")
print("=" * 60)

fig.show()
