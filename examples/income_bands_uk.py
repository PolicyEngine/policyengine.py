"""Example: Calculate net income and tax by income decile using representative microdata.

This script demonstrates:
1. Using representative household microdata
2. Running a full microsimulation to calculate income tax and net income
3. Using Aggregate to calculate statistics within income deciles using quantile filters
4. Visualising results with Plotly

Run: python examples/income_bands.py
"""

from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from policyengine.core import Simulation
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    uk_latest,
)


def load_representative_data(year: int = 2026) -> PolicyEngineUKDataset:
    """Load representative household microdata for a given year."""
    dataset_path = Path(f"./data/enhanced_frs_2023_24_year_{year}.h5")

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {dataset_path}. "
            "Run create_datasets() from policyengine.tax_benefit_models.uk first."
        )

    dataset = PolicyEngineUKDataset(
        name=f"Enhanced FRS {year}",
        description=f"Representative household microdata for {year}",
        filepath=str(dataset_path),
        year=year,
    )
    dataset.load()
    return dataset


def run_simulation(dataset: PolicyEngineUKDataset) -> Simulation:
    """Run a microsimulation on the dataset."""
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
    )
    simulation.run()
    return simulation


def calculate_income_decile_statistics(simulation: Simulation) -> dict:
    """Calculate total income, tax, and population by income deciles."""
    deciles = []
    net_incomes = []
    taxes = []
    counts = []

    for decile in range(1, 11):
        net_income_agg = Aggregate(
            simulation=simulation,
            variable="household_net_income",
            aggregate_type=AggregateType.SUM,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile,
        )
        net_income_agg.run()

        tax_agg = Aggregate(
            simulation=simulation,
            variable="household_tax",
            aggregate_type=AggregateType.SUM,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile,
        )
        tax_agg.run()

        count_agg = Aggregate(
            simulation=simulation,
            variable="household_net_income",
            aggregate_type=AggregateType.COUNT,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile,
        )
        count_agg.run()

        deciles.append(f"Decile {decile}")
        net_incomes.append(net_income_agg.result / 1e9)  # Convert to billions
        taxes.append(tax_agg.result / 1e9)
        counts.append(count_agg.result / 1e6)  # Convert to millions

    return {
        "deciles": deciles,
        "net_incomes": net_incomes,
        "taxes": taxes,
        "counts": counts,
    }


def visualise_results(results: dict) -> None:
    """Create visualisations of income decile statistics."""
    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=(
            "Net income by decile (£bn)",
            "Tax by decile (£bn)",
            "Households by decile (millions)",
        ),
        specs=[[{"type": "bar"}, {"type": "bar"}, {"type": "bar"}]],
    )

    fig.add_trace(
        go.Bar(
            x=results["deciles"],
            y=results["net_incomes"],
            marker_color="lightblue",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=results["deciles"],
            y=results["taxes"],
            marker_color="lightcoral",
        ),
        row=1,
        col=2,
    )

    fig.add_trace(
        go.Bar(
            x=results["deciles"],
            y=results["counts"],
            marker_color="lightgreen",
        ),
        row=1,
        col=3,
    )

    fig.update_xaxes(title_text="Income decile", row=1, col=1)
    fig.update_xaxes(title_text="Income decile", row=1, col=2)
    fig.update_xaxes(title_text="Income decile", row=1, col=3)

    fig.update_layout(
        title_text="Household income and tax distribution",
        showlegend=False,
        height=400,
    )

    fig.show()


def main():
    """Main execution function."""
    print("Loading representative household data...")
    dataset = load_representative_data(year=2026)

    print("Running microsimulation...")
    simulation = run_simulation(dataset)

    print("Calculating statistics by income decile...")
    results = calculate_income_decile_statistics(simulation)

    print("\nResults summary:")
    total_net_income = sum(results["net_incomes"])
    total_tax = sum(results["taxes"])
    total_households = sum(results["counts"])

    print(f"Total net income: £{total_net_income:.1f}bn")
    print(f"Total tax: £{total_tax:.1f}bn")
    print(f"Total households: {total_households:.1f}m")
    print(
        f"Average effective tax rate: {total_tax / (total_net_income + total_tax) * 100:.1f}%"
    )

    print("\nGenerating visualisations...")
    visualise_results(results)


if __name__ == "__main__":
    main()
