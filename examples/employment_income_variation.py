"""Example: Vary employment income and plot HBAI household net income.

This script demonstrates:
1. Creating a custom dataset with a single household template
2. Varying employment income from £0 to £100k
3. Running a single simulation for all variations
4. Using Aggregate with filters to extract results by employment income
5. Visualising the relationship between employment income and net income

Run: python examples/employment_income_variation.py
"""

import pandas as pd
import tempfile
from pathlib import Path
import plotly.graph_objects as go
from microdf import MicroDataFrame
from policyengine.core import Simulation
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest,
)
from policyengine.outputs.aggregate import Aggregate, AggregateType


def create_dataset_with_varied_employment_income(
    employment_incomes: list[float], year: int = 2026
) -> PolicyEngineUKDataset:
    """Create a dataset with one household template, varied by employment income.

    Each household is a single adult with varying employment income.
    Everything else about the household is kept constant.
    """
    n_households = len(employment_incomes)

    # Create person data - one adult per household with varying employment income
    person_data = {
        "person_id": list(range(n_households)),
        "person_benunit_id": list(range(n_households)),  # Link to benunit
        "person_household_id": list(range(n_households)),  # Link to household
        "age": [35] * n_households,  # Single adult, age 35
        "employment_income": employment_incomes,
        "person_weight": [1.0] * n_households,
    }

    # Create benunit data - one per household
    benunit_data = {
        "benunit_id": list(range(n_households)),
        "benunit_weight": [1.0] * n_households,
    }

    # Create household data - one per employment income level
    household_data = {
        "household_id": list(range(n_households)),
        "household_weight": [1.0] * n_households,
        "region": ["LONDON"] * n_households,  # Required by policyengine-uk
        "council_tax": [0.0] * n_households,  # Simplified - no council tax
        "rent": [0.0] * n_households,  # Simplified - no rent
        "tenure_type": ["RENT_PRIVATELY"]
        * n_households,  # Required for uprating
    }

    # Create MicroDataFrames
    person_df = MicroDataFrame(
        pd.DataFrame(person_data), weights="person_weight"
    )
    benunit_df = MicroDataFrame(
        pd.DataFrame(benunit_data), weights="benunit_weight"
    )
    household_df = MicroDataFrame(
        pd.DataFrame(household_data), weights="household_weight"
    )

    # Create temporary file
    tmpdir = tempfile.mkdtemp()
    filepath = str(Path(tmpdir) / "employment_income_variation.h5")

    # Create dataset
    dataset = PolicyEngineUKDataset(
        name="Employment income variation",
        description="Single adult household with varying employment income",
        filepath=filepath,
        year=year,
        data=UKYearData(
            person=person_df,
            benunit=benunit_df,
            household=household_df,
        ),
    )

    return dataset


def run_simulation(dataset: PolicyEngineUKDataset) -> Simulation:
    """Run a single simulation for all employment income variations."""
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
    )
    simulation.run()
    return simulation


def extract_results_by_employment_income(
    simulation: Simulation, employment_incomes: list[float]
) -> dict:
    """Extract HBAI household net income and components for each employment income level.

    Uses Aggregate with filters to extract specific households.
    """
    hbai_net_income = []
    household_benefits = []
    household_tax = []
    employment_income_hh = []

    for emp_income in employment_incomes:
        # Get HBAI household net income
        agg = Aggregate(
            simulation=simulation,
            variable="hbai_household_net_income",
            aggregate_type=AggregateType.MEAN,
            filter_variable="employment_income",
            filter_variable_eq=emp_income,
            entity="household",
        )
        agg.run()
        hbai_net_income.append(agg.result)

        # Get household benefits
        agg = Aggregate(
            simulation=simulation,
            variable="household_benefits",
            aggregate_type=AggregateType.MEAN,
            filter_variable="employment_income",
            filter_variable_eq=emp_income,
            entity="household",
        )
        agg.run()
        household_benefits.append(agg.result)

        # Get household tax
        agg = Aggregate(
            simulation=simulation,
            variable="household_tax",
            aggregate_type=AggregateType.MEAN,
            filter_variable="employment_income",
            filter_variable_eq=emp_income,
            entity="household",
        )
        agg.run()
        household_tax.append(agg.result)

        # Get employment income at household level
        agg = Aggregate(
            simulation=simulation,
            variable="employment_income",
            aggregate_type=AggregateType.MEAN,
            filter_variable="employment_income",
            filter_variable_eq=emp_income,
            entity="household",
        )
        agg.run()
        employment_income_hh.append(agg.result)

    return {
        "employment_income": employment_incomes,
        "hbai_household_net_income": hbai_net_income,
        "household_benefits": household_benefits,
        "household_tax": household_tax,
        "employment_income_hh": employment_income_hh,
    }


def visualise_results(results: dict) -> None:
    """Create a line chart showing HBAI household net income and components."""
    fig = go.Figure()

    # Main HBAI net income line
    fig.add_trace(
        go.Scatter(
            x=results["employment_income"],
            y=results["hbai_household_net_income"],
            mode="lines+markers",
            name="HBAI household net income",
            line=dict(color="darkblue", width=3),
            marker=dict(size=5),
        )
    )

    # Employment income (gross)
    fig.add_trace(
        go.Scatter(
            x=results["employment_income"],
            y=results["employment_income_hh"],
            mode="lines",
            name="Employment income (gross)",
            line=dict(color="green", width=2, dash="dot"),
        )
    )

    # Household benefits
    fig.add_trace(
        go.Scatter(
            x=results["employment_income"],
            y=results["household_benefits"],
            mode="lines",
            name="Household benefits",
            line=dict(color="orange", width=2),
        )
    )

    # Household tax (negative for visual clarity)
    fig.add_trace(
        go.Scatter(
            x=results["employment_income"],
            y=[-t for t in results["household_tax"]],
            mode="lines",
            name="Household tax (negative)",
            line=dict(color="red", width=2),
        )
    )

    fig.update_layout(
        title="HBAI household net income and components by employment income",
        xaxis_title="Employment income (£)",
        yaxis_title="Amount (£)",
        height=600,
        width=1000,
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    fig.show()


def main():
    """Main execution function."""
    # Create employment income range from £0 to £100k
    # Using smaller intervals at lower incomes where the relationship is more interesting
    employment_incomes = (
        list(range(0, 20000, 1000))  # £0 to £20k in £1k steps
        + list(range(20000, 50000, 2500))  # £20k to £50k in £2.5k steps
        + list(range(50000, 100001, 5000))  # £50k to £100k in £5k steps
    )

    print(
        f"Creating dataset with {len(employment_incomes)} employment income variations..."
    )
    dataset = create_dataset_with_varied_employment_income(employment_incomes)

    print("Running simulation (single run for all variations)...")
    simulation = run_simulation(dataset)

    print("Extracting results using aggregate filters...")
    results = extract_results_by_employment_income(
        simulation, employment_incomes
    )

    print("\nSample results:")
    print(
        f"Employment income £0: HBAI net income £{results['hbai_household_net_income'][0]:,.0f}"
    )
    print(
        f"Employment income £25k: HBAI net income £{results['hbai_household_net_income'][employment_incomes.index(25000)]:,.0f}"
    )
    print(
        f"Employment income £50k: HBAI net income £{results['hbai_household_net_income'][employment_incomes.index(50000)]:,.0f}"
    )
    print(
        f"Employment income £100k: HBAI net income £{results['hbai_household_net_income'][-1]:,.0f}"
    )

    print("\nGenerating visualisation...")
    visualise_results(results)


if __name__ == "__main__":
    main()
