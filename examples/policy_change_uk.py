"""Example: Analyse policy change impacts using ChangeAggregate with parametric reforms.

This script demonstrates:
1. Loading representative household microdata
2. Applying parametric reforms (e.g., setting personal allowance to zero)
3. Running baseline and reform simulations
4. Using ChangeAggregate to analyse winners, losers, and impact sizes by income decile
5. Using quantile filters for decile-based analysis
6. Visualising results with Plotly

Run: python examples/policy_change.py
"""

import datetime
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from policyengine.core import Parameter, ParameterValue, Policy, Simulation
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType,
)
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


def create_personal_allowance_reform(year: int) -> Policy:
    """Create a policy that sets personal allowance to zero."""
    parameter = Parameter(
        id=f"{uk_latest.id}-gov.hmrc.income_tax.allowances.personal_allowance.amount",
        name="gov.hmrc.income_tax.allowances.personal_allowance.amount",
        tax_benefit_model_version=uk_latest,
        description="Personal allowance for income tax",
        data_type=float,
    )

    parameter_value = ParameterValue(
        parameter=parameter,
        start_date=datetime.date(year, 1, 1),
        end_date=datetime.date(year, 12, 31),
        value=0,
    )

    return Policy(
        name="Zero personal allowance",
        description="Sets personal allowance to £0",
        parameter_values=[parameter_value],
    )


def run_baseline_simulation(dataset: PolicyEngineUKDataset) -> Simulation:
    """Run baseline microsimulation without policy changes."""
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
    )
    simulation.run()
    return simulation


def run_reform_simulation(
    dataset: PolicyEngineUKDataset, policy: Policy
) -> Simulation:
    """Run reform microsimulation with policy changes."""
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
        policy=policy,
    )
    simulation.run()
    return simulation


def analyse_overall_impact(
    baseline_sim: Simulation, reform_sim: Simulation
) -> dict:
    """Analyse overall winners, losers, and financial impact."""
    winners = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="household_net_income",
        aggregate_type=ChangeAggregateType.COUNT,
        change_geq=1,
    )
    winners.run()

    losers = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="household_net_income",
        aggregate_type=ChangeAggregateType.COUNT,
        change_leq=-1,
    )
    losers.run()

    no_change = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="household_net_income",
        aggregate_type=ChangeAggregateType.COUNT,
        change_eq=0,
    )
    no_change.run()

    total_change = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="household_net_income",
        aggregate_type=ChangeAggregateType.SUM,
    )
    total_change.run()

    tax_revenue_change = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="household_tax",
        aggregate_type=ChangeAggregateType.SUM,
    )
    tax_revenue_change.run()

    return {
        "winners": winners.result / 1e6,  # Convert to millions
        "losers": losers.result / 1e6,
        "no_change": no_change.result / 1e6,
        "total_change": total_change.result / 1e9,  # Convert to billions
        "tax_revenue_change": tax_revenue_change.result / 1e9,
    }


def analyse_impact_by_income_decile(
    baseline_sim: Simulation, reform_sim: Simulation
) -> dict:
    """Analyse impact by income decile."""
    decile_labels = []
    decile_losers = []
    decile_avg_loss = []

    for decile in range(1, 11):
        label = f"Decile {decile}"

        # Count losers in this decile
        count_agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="household_net_income",
            aggregate_type=ChangeAggregateType.COUNT,
            change_leq=-1,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile,
        )
        count_agg.run()

        # Average loss for all households in this decile
        mean_agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="household_net_income",
            aggregate_type=ChangeAggregateType.MEAN,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile,
        )
        mean_agg.run()

        decile_labels.append(label)
        decile_losers.append(count_agg.result / 1e6)  # Convert to millions
        decile_avg_loss.append(mean_agg.result)

    return {
        "labels": decile_labels,
        "losers": decile_losers,
        "avg_loss": decile_avg_loss,
    }


def visualise_results(
    overall: dict, by_decile: dict, reform_name: str
) -> None:
    """Create visualisations of policy change impacts."""
    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=(
            "Winners vs losers (millions)",
            "Losers by income decile (millions)",
            "Average loss by income decile (£)",
        ),
        specs=[[{"type": "bar"}, {"type": "bar"}, {"type": "bar"}]],
    )

    fig.add_trace(
        go.Bar(
            x=["Winners", "No change", "Losers"],
            y=[
                overall["winners"],
                overall["no_change"],
                overall["losers"],
            ],
            marker_color=["green", "gray", "red"],
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=by_decile["labels"],
            y=by_decile["losers"],
            marker_color="lightcoral",
        ),
        row=1,
        col=2,
    )

    fig.add_trace(
        go.Bar(
            x=by_decile["labels"],
            y=by_decile["avg_loss"],
            marker_color="orange",
        ),
        row=1,
        col=3,
    )

    fig.update_xaxes(title_text="Category", row=1, col=1)
    fig.update_xaxes(title_text="Income decile", row=1, col=2)
    fig.update_xaxes(title_text="Income decile", row=1, col=3)

    fig.update_layout(
        title_text=f"Policy change impact analysis: {reform_name}",
        showlegend=False,
        height=400,
    )

    fig.show()


def print_summary(overall: dict, decile: dict, reform_name: str) -> None:
    """Print summary statistics."""
    print("=" * 60)
    print(f"Policy change impact summary: {reform_name}")
    print("=" * 60)
    print("\nOverall impact:")
    print(f"  Winners: {overall['winners']:.2f}m households")
    print(f"  Losers: {overall['losers']:.2f}m households")
    print(f"  No change: {overall['no_change']:.2f}m households")
    print("\nFinancial impact:")
    print(
        f"  Net income change: £{overall['total_change']:.2f}bn (negative = loss)"
    )
    print(f"  Tax revenue change: £{overall['tax_revenue_change']:.2f}bn")
    print("\nImpact by income decile:")
    for i, label in enumerate(decile["labels"]):
        print(
            f"  {label}: {decile['losers'][i]:.2f}m losers, avg change £{decile['avg_loss'][i]:.0f}"
        )
    print("=" * 60)


def main():
    """Main execution function."""
    year = 2026

    print("Loading representative household data...")
    dataset = load_representative_data(year=year)

    print("Creating policy reform (zero personal allowance)...")
    reform = create_personal_allowance_reform(year=year)

    print("Running baseline simulation...")
    baseline_sim = run_baseline_simulation(dataset)

    print("Running reform simulation...")
    reform_sim = run_reform_simulation(dataset, reform)

    print("Analysing overall impact...")
    overall_impact = analyse_overall_impact(baseline_sim, reform_sim)

    print("Analysing impact by income decile...")
    decile_impact = analyse_impact_by_income_decile(baseline_sim, reform_sim)

    print_summary(overall_impact, decile_impact, reform.name)

    print("\nGenerating visualisations...")
    visualise_results(overall_impact, decile_impact, reform.name)


if __name__ == "__main__":
    main()
