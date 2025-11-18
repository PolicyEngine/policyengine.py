"""Example: Vary employment income and plot HBAI household net income.

This script demonstrates:
1. Creating a custom dataset with a single household template
2. Varying employment income from £0 to £100k
3. Running a single simulation for all variations
4. Using Aggregate with filters to extract results by employment income
5. Visualising the relationship between employment income and net income

IMPORTANT NOTES FOR CUSTOM DATASETS:
- Always set would_claim_* variables to True, otherwise benefits won't be claimed
  even if the household is eligible (they default to random/False)
- Always set disability variables explicitly (is_disabled_for_benefits, uc_limited_capability_for_WRA)
  to prevent random UC spikes from LCWRA element (£5,241/year extra if randomly assigned)
- Must include join keys: person_benunit_id, person_household_id in person data
- Required household fields: region, council_tax, rent, tenure_type
- Person-level variables are mapped to household level using weights

Run: python examples/employment_income_variation.py
"""

import tempfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest,
)
from policyengine.utils.plotting import COLORS, format_fig


def create_dataset_with_varied_employment_income(
    employment_incomes: list[float], year: int = 2026
) -> PolicyEngineUKDataset:
    """Create a dataset with one household template, varied by employment income.

    Each household is a single adult with 2 children, paying median UK rent.
    Employment income varies across households.
    """
    n_households = len(employment_incomes)
    n_households * 3  # 1 adult + 2 children per household

    # Create person data - one adult + 2 children per household
    person_ids = []
    benunit_ids = []
    household_ids = []
    ages = []
    employment_income = []
    person_weights = []
    is_disabled = []
    limited_capability = []

    person_id_counter = 0
    for hh_idx in range(n_households):
        # Adult
        person_ids.append(person_id_counter)
        benunit_ids.append(hh_idx)
        household_ids.append(hh_idx)
        ages.append(35)
        employment_income.append(employment_incomes[hh_idx])
        person_weights.append(1.0)
        is_disabled.append(False)
        limited_capability.append(False)
        person_id_counter += 1

        # Child 1 (age 8)
        person_ids.append(person_id_counter)
        benunit_ids.append(hh_idx)
        household_ids.append(hh_idx)
        ages.append(8)
        employment_income.append(0.0)
        person_weights.append(1.0)
        is_disabled.append(False)
        limited_capability.append(False)
        person_id_counter += 1

        # Child 2 (age 5)
        person_ids.append(person_id_counter)
        benunit_ids.append(hh_idx)
        household_ids.append(hh_idx)
        ages.append(5)
        employment_income.append(0.0)
        person_weights.append(1.0)
        is_disabled.append(False)
        limited_capability.append(False)
        person_id_counter += 1

    person_data = {
        "person_id": person_ids,
        "person_benunit_id": benunit_ids,
        "person_household_id": household_ids,
        "age": ages,
        "employment_income": employment_income,
        "person_weight": person_weights,
        "is_disabled_for_benefits": is_disabled,
        "uc_limited_capability_for_WRA": limited_capability,
    }

    # Create benunit data - one per household
    benunit_data = {
        "benunit_id": list(range(n_households)),
        "benunit_weight": [1.0] * n_households,
        # Would claim variables - MUST set to True or benefits won't be claimed!
        "would_claim_uc": [True] * n_households,
        "would_claim_WTC": [True] * n_households,
        "would_claim_CTC": [True] * n_households,
        "would_claim_IS": [True] * n_households,
        "would_claim_pc": [True] * n_households,
        "would_claim_child_benefit": [True] * n_households,
        "would_claim_housing_benefit": [True] * n_households,
    }

    # Create household data - one per employment income level
    median_annual_rent = 850 * 12  # £850/month = £10,200/year (median UK rent)
    household_data = {
        "household_id": list(range(n_households)),
        "household_weight": [1.0] * n_households,
        "region": ["LONDON"] * n_households,  # Required by policyengine-uk
        "council_tax": [0.0] * n_households,  # Simplified - no council tax
        "rent": [median_annual_rent] * n_households,  # Median UK rent
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

    # Individual benefits
    universal_credit = []
    child_benefit = []
    working_tax_credit = []
    child_tax_credit = []
    pension_credit = []
    income_support = []

    for hh_idx, emp_income in enumerate(employment_incomes):
        # Get HBAI household net income
        agg = Aggregate(
            simulation=simulation,
            variable="hbai_household_net_income",
            aggregate_type=AggregateType.MEAN,
            filter_variable="household_id",
            filter_variable_eq=hh_idx,
            entity="household",
        )
        agg.run()
        hbai_net_income.append(agg.result)

        # Get household benefits
        agg = Aggregate(
            simulation=simulation,
            variable="household_benefits",
            aggregate_type=AggregateType.MEAN,
            filter_variable="household_id",
            filter_variable_eq=hh_idx,
            entity="household",
        )
        agg.run()
        household_benefits.append(agg.result)

        # Get individual benefits (at benunit level, but we have 1:1 benunit:household mapping)
        for benefit_name, benefit_list in [
            ("universal_credit", universal_credit),
            ("child_benefit", child_benefit),
            ("working_tax_credit", working_tax_credit),
            ("child_tax_credit", child_tax_credit),
            ("pension_credit", pension_credit),
            ("income_support", income_support),
        ]:
            agg = Aggregate(
                simulation=simulation,
                variable=benefit_name,
                aggregate_type=AggregateType.MEAN,
                filter_variable="benunit_id",
                filter_variable_eq=hh_idx,
                entity="benunit",
            )
            agg.run()
            benefit_list.append(agg.result)

        # Get household tax
        agg = Aggregate(
            simulation=simulation,
            variable="household_tax",
            aggregate_type=AggregateType.MEAN,
            filter_variable="household_id",
            filter_variable_eq=hh_idx,
            entity="household",
        )
        agg.run()
        household_tax.append(agg.result)

        # Employment income at household level (just use the input value)
        employment_income_hh.append(emp_income)

    return {
        "employment_income": employment_incomes,
        "hbai_household_net_income": hbai_net_income,
        "household_benefits": household_benefits,
        "household_tax": household_tax,
        "employment_income_hh": employment_income_hh,
        "universal_credit": universal_credit,
        "child_benefit": child_benefit,
        "working_tax_credit": working_tax_credit,
        "child_tax_credit": child_tax_credit,
        "pension_credit": pension_credit,
        "income_support": income_support,
    }


def visualise_results(results: dict) -> None:
    """Create a stacked area chart showing income composition."""
    fig = go.Figure()

    # Calculate net employment income (employment income minus tax)
    net_employment = [
        emp - tax
        for emp, tax in zip(
            results["employment_income_hh"], results["household_tax"]
        )
    ]

    # Stack benefits and income components using PolicyEngine colors
    components = [
        ("Net employment income", net_employment, COLORS["primary"]),
        (
            "Universal Credit",
            results["universal_credit"],
            COLORS["blue_secondary"],
        ),
        ("Working Tax Credit", results["working_tax_credit"], COLORS["info"]),
        ("Child Tax Credit", results["child_tax_credit"], COLORS["success"]),
        ("Child Benefit", results["child_benefit"], COLORS["warning"]),
        ("Pension Credit", results["pension_credit"], COLORS["gray"]),
        ("Income Support", results["income_support"], COLORS["gray_dark"]),
    ]

    for name, values, color in components:
        fig.add_trace(
            go.Scatter(
                x=results["employment_income"],
                y=values,
                name=name,
                mode="lines",
                line=dict(width=0.5, color=color),
                stackgroup="one",
                fillcolor=color,
            )
        )

    # Apply PolicyEngine styling
    format_fig(
        fig,
        title="Household net income composition by employment income",
        xaxis_title="Employment income (£)",
        yaxis_title="Net income (£)",
        show_legend=True,
        height=700,
        width=1200,
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
    for emp_inc in [0, 25000, 50000, 100000]:
        idx = (
            employment_incomes.index(emp_inc)
            if emp_inc in employment_incomes
            else -1
        )
        if idx >= 0:
            print(
                f"  Employment income £{emp_inc:,}: HBAI net income £{results['hbai_household_net_income'][idx]:,.0f}"
            )

    print("\nGenerating visualisation...")
    visualise_results(results)


if __name__ == "__main__":
    main()
