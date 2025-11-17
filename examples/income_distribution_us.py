"""Example: Plot US household income distribution using enhanced CPS microdata.

This script demonstrates:
1. Loading enhanced CPS representative household microdata
2. Running a full microsimulation to calculate household income and tax
3. Using Aggregate to calculate statistics within income deciles
4. Visualising the income distribution across the United States

Run: python examples/income_distribution_us.py
"""

import time
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from policyengine.core import Simulation
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.tax_benefit_models.us import (
    PolicyEngineUSDataset,
    us_latest,
)
from policyengine.utils.plotting import COLORS, format_fig


def load_representative_data(year: int = 2024) -> PolicyEngineUSDataset:
    """Load representative household microdata for a given year."""
    dataset_path = (
        Path(__file__).parent / "data" / f"enhanced_cps_2024_year_{year}.h5"
    )

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {dataset_path}. "
            "Run create_datasets() from policyengine.tax_benefit_models.us first."
        )

    dataset = PolicyEngineUSDataset(
        name=f"Enhanced CPS {year}",
        description=f"Representative household microdata for {year}",
        filepath=str(dataset_path),
        year=year,
    )
    dataset.load()
    return dataset


def run_simulation(dataset: PolicyEngineUSDataset) -> Simulation:
    """Run a microsimulation on the dataset."""
    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=us_latest,
    )
    simulation.run()
    return simulation


def calculate_income_decile_statistics(simulation: Simulation) -> dict:
    """Calculate total income, tax, and benefits by income deciles."""
    start_time = time.time()
    deciles = [f"D{i}" for i in range(1, 11)]
    market_incomes = []
    taxes = []
    benefits = []
    net_incomes = []
    counts = []

    # Calculate household-level aggregates by decile
    print("Calculating main statistics by decile...")
    main_stats_start = time.time()
    for decile_num in range(1, 11):
        decile_start = time.time()

        # Market income
        pre_create = time.time()
        agg = Aggregate(
            simulation=simulation,
            variable="household_market_income",
            aggregate_type=AggregateType.SUM,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile_num,
        )
        if decile_num == 1:
            print(
                f"    First Aggregate created ({time.time() - pre_create:.2f}s)"
            )
        pre_run = time.time()
        agg.run()
        if decile_num == 1:
            print(
                f"    First Aggregate.run() complete ({time.time() - pre_run:.2f}s)"
            )
        market_incomes.append(agg.result / 1e9)

        agg = Aggregate(
            simulation=simulation,
            variable="household_tax",
            aggregate_type=AggregateType.SUM,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile_num,
        )
        agg.run()
        taxes.append(agg.result / 1e9)

        agg = Aggregate(
            simulation=simulation,
            variable="household_benefits",
            aggregate_type=AggregateType.SUM,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile_num,
        )
        agg.run()
        benefits.append(agg.result / 1e9)

        agg = Aggregate(
            simulation=simulation,
            variable="household_net_income",
            aggregate_type=AggregateType.SUM,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile_num,
        )
        agg.run()
        net_incomes.append(agg.result / 1e9)

        agg = Aggregate(
            simulation=simulation,
            variable="household_weight",
            aggregate_type=AggregateType.SUM,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile_num,
        )
        agg.run()
        counts.append(agg.result / 1e6)

        print(f"  D{decile_num} complete ({time.time() - decile_start:.2f}s)")

    print(f"Main statistics complete ({time.time() - main_stats_start:.2f}s)")

    # Calculate individual benefit programs by decile
    benefit_programs_by_decile = {}

    # Person-level benefits (mapped to household for decile filtering)
    print("Calculating person-level benefit programs...")
    person_benefits_start = time.time()
    first_prog = True
    for prog in [
        "ssi",
        "social_security",
        "medicaid",
        "unemployment_compensation",
    ]:
        prog_start = time.time()
        prog_by_decile = []
        for decile_num in range(1, 11):
            if first_prog and decile_num == 1:
                pre_create = time.time()
            agg = Aggregate(
                simulation=simulation,
                variable=prog,
                entity="household",
                aggregate_type=AggregateType.SUM,
                filter_variable="household_net_income",
                quantile=10,
                quantile_eq=decile_num,
                debug_timing=first_prog and decile_num == 1,
            )
            if first_prog and decile_num == 1:
                print(
                    f"    First benefit Aggregate created ({time.time() - pre_create:.2f}s)"
                )
                pre_run = time.time()
            agg.run()
            if first_prog and decile_num == 1:
                print(
                    f"    First benefit Aggregate.run() complete ({time.time() - pre_run:.2f}s)"
                )
                first_prog = False
            prog_by_decile.append(agg.result / 1e9)
        benefit_programs_by_decile[prog] = prog_by_decile
        print(f"  {prog} complete ({time.time() - prog_start:.2f}s)")

    print(
        f"Person-level benefits complete ({time.time() - person_benefits_start:.2f}s)"
    )

    # SPM unit benefits (mapped to household for decile filtering)
    print("Calculating SPM unit benefit programs...")
    spm_benefits_start = time.time()
    for prog in ["snap", "tanf"]:
        prog_start = time.time()
        prog_by_decile = []
        for decile_num in range(1, 11):
            agg = Aggregate(
                simulation=simulation,
                variable=prog,
                entity="household",
                aggregate_type=AggregateType.SUM,
                filter_variable="household_net_income",
                quantile=10,
                quantile_eq=decile_num,
            )
            agg.run()
            prog_by_decile.append(agg.result / 1e9)
        benefit_programs_by_decile[prog] = prog_by_decile
        print(f"  {prog} complete ({time.time() - prog_start:.2f}s)")

    print(f"SPM benefits complete ({time.time() - spm_benefits_start:.2f}s)")

    # Tax unit benefits (mapped to household for decile filtering)
    print("Calculating tax unit benefit programs...")
    tax_benefits_start = time.time()
    for prog in ["eitc", "ctc"]:
        prog_start = time.time()
        prog_by_decile = []
        for decile_num in range(1, 11):
            agg = Aggregate(
                simulation=simulation,
                variable=prog,
                entity="household",
                aggregate_type=AggregateType.SUM,
                filter_variable="household_net_income",
                quantile=10,
                quantile_eq=decile_num,
            )
            agg.run()
            prog_by_decile.append(agg.result / 1e9)
        benefit_programs_by_decile[prog] = prog_by_decile
        print(f"  {prog} complete ({time.time() - prog_start:.2f}s)")

    print(f"Tax benefits complete ({time.time() - tax_benefits_start:.2f}s)")
    print(
        f"\nTotal statistics calculation time: {time.time() - start_time:.2f}s"
    )

    return {
        "deciles": deciles,
        "market_incomes": market_incomes,
        "taxes": taxes,
        "benefits": benefits,
        "net_incomes": net_incomes,
        "counts": counts,
        "benefit_programs_by_decile": benefit_programs_by_decile,
    }


def visualise_results(results: dict) -> None:
    """Create visualisations of income distribution."""
    # Create overview figure
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Market income by decile ($bn)",
            "Tax by decile ($bn)",
            "Benefits by program and decile ($bn)",
            "Households by decile (millions)",
        ),
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "bar"}],
        ],
    )

    # Market income
    fig.add_trace(
        go.Bar(
            x=results["deciles"],
            y=results["market_incomes"],
            marker_color=COLORS["primary"],
            name="Market income",
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    # Tax
    fig.add_trace(
        go.Bar(
            x=results["deciles"],
            y=results["taxes"],
            marker_color=COLORS["error"],
            name="Tax",
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    # Benefits by program (stacked) - with legend
    benefit_programs = [
        ("Social Security", "social_security", "#026AA2"),
        ("Medicaid", "medicaid", "#319795"),
        ("SNAP", "snap", "#22C55E"),
        ("EITC", "eitc", "#FEC601"),
        ("CTC", "ctc", "#1890FF"),
        ("SSI", "ssi", "#EF4444"),
        ("TANF", "tanf", "#667085"),
        ("Unemployment", "unemployment_compensation", "#101828"),
    ]

    for name, key, color in benefit_programs:
        if key in results["benefit_programs_by_decile"]:
            fig.add_trace(
                go.Bar(
                    x=results["deciles"],
                    y=results["benefit_programs_by_decile"][key],
                    name=name,
                    marker_color=color,
                    legendgroup="benefits",
                    showlegend=True,
                ),
                row=2,
                col=1,
            )

    # Household counts
    fig.add_trace(
        go.Bar(
            x=results["deciles"],
            y=results["counts"],
            marker_color=COLORS["info"],
            name="Households",
            showlegend=False,
        ),
        row=2,
        col=2,
    )

    fig.update_xaxes(title_text="Income decile", row=1, col=1)
    fig.update_xaxes(title_text="Income decile", row=1, col=2)
    fig.update_xaxes(title_text="Income decile", row=2, col=1)
    fig.update_xaxes(title_text="Income decile", row=2, col=2)

    # Apply PolicyEngine formatting
    format_fig(
        fig,
        title="US household income distribution (Enhanced CPS 2024)",
        show_legend=True,
        height=800,
        width=1400,
    )

    # Override legend position for subplot layout
    fig.update_layout(
        barmode="stack",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.45,
            xanchor="left",
            x=0.52,
            bgcolor="white",
            bordercolor="#E5E7EB",
            borderwidth=1,
        ),
    )

    fig.show()


def main():
    """Main execution function."""
    print("Loading enhanced CPS representative household data...")
    dataset = load_representative_data(year=2024)

    print(
        f"Dataset loaded: {len(dataset.data.person):,} people, {len(dataset.data.household):,} households"
    )

    print("Running microsimulation...")
    simulation = run_simulation(dataset)

    print("Calculating statistics by income decile...")
    results = calculate_income_decile_statistics(simulation)

    print("\nResults summary:")
    total_market_income = sum(results["market_incomes"])
    total_tax = sum(results["taxes"])
    total_benefits = sum(results["benefits"])
    total_net_income = sum(results["net_incomes"])
    total_households = sum(results["counts"])

    print(f"Total market income: ${total_market_income:.1f}bn")
    print(f"Total tax: ${total_tax:.1f}bn")
    print(f"Total benefits: ${total_benefits:.1f}bn")
    print(f"Total net income: ${total_net_income:.1f}bn")
    print(f"Total households: {total_households:.1f}m")
    print(
        f"Average effective tax rate: {total_tax / total_market_income * 100:.1f}%"
    )

    print("\nBenefit programs by decile:")
    benefit_programs = [
        ("Social Security", "social_security"),
        ("Medicaid", "medicaid"),
        ("SNAP", "snap"),
        ("EITC", "eitc"),
        ("CTC", "ctc"),
        ("SSI", "ssi"),
        ("TANF", "tanf"),
        ("Unemployment", "unemployment_compensation"),
    ]

    for name, key in benefit_programs:
        if key in results["benefit_programs_by_decile"]:
            total = sum(results["benefit_programs_by_decile"][key])
            print(f"\n  {name} (total: ${total:.1f}bn):")
            for i, decile in enumerate(results["deciles"]):
                value = results["benefit_programs_by_decile"][key][i]
                print(f"    {decile}: ${value:.1f}bn")

    print("\nGenerating visualisations...")
    visualise_results(results)


if __name__ == "__main__":
    main()
