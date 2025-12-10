"""Distributional analysis: setting the UK basic rate to 17p.

This script analyses the impact of reducing the income tax basic rate from 20% to 17%.
"""

import datetime

import numpy as np
import pandas as pd
from microdf import MicroDataFrame

from policyengine.core import Parameter, ParameterValue, Policy, Simulation
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.outputs.change_aggregate import ChangeAggregate, ChangeAggregateType
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest,
)


def create_representative_dataset(year: int, n_households: int = 10000) -> PolicyEngineUKDataset:
    """Create synthetic representative UK household data.

    Creates a distribution of households with varying income levels
    that approximates the UK income distribution.
    """
    np.random.seed(42)

    # UK income distribution parameters (approximate)
    # Using a log-normal distribution to represent income
    # Median ~£35k, with long right tail
    log_incomes = np.random.normal(loc=10.3, scale=0.8, size=n_households)
    employment_incomes = np.clip(np.exp(log_incomes), 0, 500000)

    # Add some zero-income households (unemployed, retired, etc.) ~15%
    zero_income_mask = np.random.random(n_households) < 0.15
    employment_incomes[zero_income_mask] = 0

    # Create ages (working age and some retired)
    ages = np.random.choice(
        range(18, 80),
        size=n_households,
        p=np.array([1.0 if 25 <= a <= 65 else 0.5 for a in range(18, 80)]) /
          sum([1.0 if 25 <= a <= 65 else 0.5 for a in range(18, 80)])
    )

    # Regions weighted by population (normalised to sum to 1)
    region_probs = np.array([0.13, 0.14, 0.09, 0.10, 0.09, 0.07, 0.08, 0.11, 0.04, 0.05, 0.08, 0.02])
    region_probs = region_probs / region_probs.sum()
    regions = np.random.choice(
        ["LONDON", "SOUTH_EAST", "SOUTH_WEST", "EAST_OF_ENGLAND",
         "WEST_MIDLANDS", "EAST_MIDLANDS", "YORKSHIRE", "NORTH_WEST",
         "NORTH_EAST", "WALES", "SCOTLAND", "NORTHERN_IRELAND"],
        size=n_households,
        p=region_probs
    )

    # Rents based on region
    base_rents = {
        "LONDON": 18000, "SOUTH_EAST": 14000, "SOUTH_WEST": 11000,
        "EAST_OF_ENGLAND": 12000, "WEST_MIDLANDS": 9000, "EAST_MIDLANDS": 8500,
        "YORKSHIRE": 8000, "NORTH_WEST": 8500, "NORTH_EAST": 7000,
        "WALES": 7500, "SCOTLAND": 8000, "NORTHERN_IRELAND": 7000
    }
    rents = np.array([base_rents[r] * np.random.uniform(0.7, 1.3) for r in regions])

    # Household weights (each household represents ~2.8 households in the UK, given ~28m households)
    household_weight = 28_000_000 / n_households

    # Person data (1 person per household for simplicity)
    person_df = MicroDataFrame(
        pd.DataFrame({
            "person_id": range(n_households),
            "person_household_id": range(n_households),
            "person_benunit_id": range(n_households),
            "age": ages,
            "employment_income": employment_incomes,
            "self_employment_income": np.zeros(n_households),
            "pension_income": np.where(ages >= 66, np.random.uniform(8000, 20000, n_households), 0),
            "person_weight": np.full(n_households, household_weight),
            "is_disabled_for_benefits": np.zeros(n_households, dtype=bool),
            "uc_limited_capability_for_WRA": np.zeros(n_households, dtype=bool),
        }),
        weights="person_weight"
    )

    # Benunit data
    benunit_df = MicroDataFrame(
        pd.DataFrame({
            "benunit_id": range(n_households),
            "benunit_weight": np.full(n_households, household_weight),
            "would_claim_uc": np.ones(n_households, dtype=bool),
            "would_claim_child_benefit": np.zeros(n_households, dtype=bool),
            "would_claim_WTC": np.ones(n_households, dtype=bool),
            "would_claim_CTC": np.zeros(n_households, dtype=bool),
        }),
        weights="benunit_weight"
    )

    # Household data
    household_df = MicroDataFrame(
        pd.DataFrame({
            "household_id": range(n_households),
            "household_weight": np.full(n_households, household_weight),
            "region": regions,
            "rent": rents,
            "council_tax": np.random.uniform(1200, 3000, n_households),
            "tenure_type": np.random.choice(
                ["RENT_PRIVATELY", "RENT_FROM_COUNCIL", "OWNED_OUTRIGHT", "OWNED_WITH_MORTGAGE"],
                size=n_households,
                p=np.array([0.20, 0.17, 0.33, 0.30]) / sum([0.20, 0.17, 0.33, 0.30])
            ),
        }),
        weights="household_weight"
    )

    dataset = PolicyEngineUKDataset(
        name=f"Synthetic UK households {year}",
        description="Synthetic representative UK household data",
        filepath=f"./synthetic_uk_{year}.h5",
        year=year,
        data=UKYearData(
            person=person_df,
            benunit=benunit_df,
            household=household_df,
        )
    )

    return dataset


def create_basic_rate_reform(year: int) -> Policy:
    """Create a policy that sets the basic rate to 17%."""
    parameter = Parameter(
        id=f"{uk_latest.id}-gov.hmrc.income_tax.rates.uk[0].rate",
        name="gov.hmrc.income_tax.rates.uk[0].rate",
        tax_benefit_model_version=uk_latest,
        description="Income tax basic rate",
        data_type=float,
    )

    parameter_value = ParameterValue(
        parameter=parameter,
        start_date=datetime.date(year, 1, 1),
        end_date=datetime.date(year, 12, 31),
        value=0.17,  # 17%
    )

    return Policy(
        name="Basic rate 17%",
        description="Reduces income tax basic rate from 20% to 17%",
        parameter_values=[parameter_value],
    )


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
        "winners": winners.result / 1e6,
        "losers": losers.result / 1e6,
        "no_change": no_change.result / 1e6,
        "total_change": total_change.result / 1e9,
        "tax_revenue_change": tax_revenue_change.result / 1e9,
    }


def analyse_impact_by_income_decile(
    baseline_sim: Simulation, reform_sim: Simulation
) -> dict:
    """Analyse impact by income decile."""
    decile_labels = []
    decile_winners = []
    decile_avg_gain = []
    decile_total_gain = []

    for decile in range(1, 11):
        label = f"Decile {decile}"

        # Count winners in this decile
        count_agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="household_net_income",
            aggregate_type=ChangeAggregateType.COUNT,
            change_geq=1,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile,
        )
        count_agg.run()

        # Average gain for all households in this decile
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

        # Total gain in this decile
        sum_agg = ChangeAggregate(
            baseline_simulation=baseline_sim,
            reform_simulation=reform_sim,
            variable="household_net_income",
            aggregate_type=ChangeAggregateType.SUM,
            filter_variable="household_net_income",
            quantile=10,
            quantile_eq=decile,
        )
        sum_agg.run()

        decile_labels.append(label)
        decile_winners.append(count_agg.result / 1e6)
        decile_avg_gain.append(mean_agg.result)
        decile_total_gain.append(sum_agg.result / 1e9)

    return {
        "labels": decile_labels,
        "winners": decile_winners,
        "avg_gain": decile_avg_gain,
        "total_gain": decile_total_gain,
    }


def print_summary(overall: dict, decile: dict, reform_name: str) -> None:
    """Print summary statistics."""
    print("=" * 70)
    print(f"Distributional analysis: {reform_name}")
    print("=" * 70)
    print("\nOverall impact:")
    print(f"  Winners: {overall['winners']:.2f}m households")
    print(f"  Losers: {overall['losers']:.2f}m households")
    print(f"  No change: {overall['no_change']:.2f}m households")
    print("\nFinancial impact:")
    print(f"  Net income change: +£{overall['total_change']:.2f}bn")
    print(f"  Tax revenue change: £{overall['tax_revenue_change']:.2f}bn")
    print("\nImpact by income decile:")
    print("-" * 70)
    print(f"{'Decile':<12} {'Winners (m)':<15} {'Avg gain (£)':<15} {'Total (£bn)':<15}")
    print("-" * 70)
    for i, label in enumerate(decile["labels"]):
        print(
            f"{label:<12} {decile['winners'][i]:>10.2f}     {decile['avg_gain'][i]:>10.0f}     {decile['total_gain'][i]:>10.2f}"
        )
    print("-" * 70)
    print("=" * 70)


def main():
    """Main execution function."""
    year = 2026

    print("Creating synthetic representative UK household data...")
    dataset = create_representative_dataset(year=year, n_households=10000)
    print(f"Created dataset: {dataset}")

    print("\nCreating policy reform (basic rate 17%)...")
    reform = create_basic_rate_reform(year=year)

    print("Running baseline simulation...")
    baseline_sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
    )
    baseline_sim.run()

    print("Running reform simulation...")
    reform_sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
        policy=reform,
    )
    reform_sim.run()

    print("Analysing overall impact...")
    overall_impact = analyse_overall_impact(baseline_sim, reform_sim)

    print("Analysing impact by income decile...")
    decile_impact = analyse_impact_by_income_decile(baseline_sim, reform_sim)

    print("\n")
    print_summary(overall_impact, decile_impact, reform.name)


if __name__ == "__main__":
    main()
