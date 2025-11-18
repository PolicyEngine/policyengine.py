"""Example: Vary employment income and plot household net income (US).

This script demonstrates:
1. Creating a custom dataset with a single household template
2. Varying employment income from $0 to $200k
3. Running a single simulation for all variations
4. Using Aggregate with filters to extract results by employment income
5. Visualising the relationship between employment income and net income

Run: python examples/employment_income_variation_us.py
"""

import tempfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from microdf import MicroDataFrame

from policyengine.core import Simulation
from policyengine.tax_benefit_models.us import (
    PolicyEngineUSDataset,
    USYearData,
    us_latest,
)
from policyengine.utils.plotting import COLORS, format_fig


def create_dataset_with_varied_employment_income(
    employment_incomes: list[float], year: int = 2024
) -> PolicyEngineUSDataset:
    """Create a dataset with one household template, varied by employment income.

    Each household is a single adult with 2 children.
    Employment income varies across households.
    """
    n_households = len(employment_incomes)
    n_households * 3  # 1 adult + 2 children per household

    # Create person data - one adult + 2 children per household
    person_ids = []
    household_ids = []
    marital_unit_ids = []
    family_ids = []
    spm_unit_ids = []
    tax_unit_ids = []
    ages = []
    employment_income = []
    person_weights = []

    person_id_counter = 0
    for hh_idx in range(n_households):
        # Adult
        person_ids.append(person_id_counter)
        household_ids.append(hh_idx)
        marital_unit_ids.append(hh_idx)
        family_ids.append(hh_idx)
        spm_unit_ids.append(hh_idx)
        tax_unit_ids.append(hh_idx)
        ages.append(35)
        employment_income.append(employment_incomes[hh_idx])
        person_weights.append(1000.0)
        person_id_counter += 1

        # Child 1 (age 8)
        person_ids.append(person_id_counter)
        household_ids.append(hh_idx)
        marital_unit_ids.append(hh_idx)
        family_ids.append(hh_idx)
        spm_unit_ids.append(hh_idx)
        tax_unit_ids.append(hh_idx)
        ages.append(8)
        employment_income.append(0.0)
        person_weights.append(1000.0)
        person_id_counter += 1

        # Child 2 (age 5)
        person_ids.append(person_id_counter)
        household_ids.append(hh_idx)
        marital_unit_ids.append(hh_idx)
        family_ids.append(hh_idx)
        spm_unit_ids.append(hh_idx)
        tax_unit_ids.append(hh_idx)
        ages.append(5)
        employment_income.append(0.0)
        person_weights.append(1000.0)
        person_id_counter += 1

    person_data = {
        "person_id": person_ids,
        "household_id": household_ids,
        "marital_unit_id": marital_unit_ids,
        "family_id": family_ids,
        "spm_unit_id": spm_unit_ids,
        "tax_unit_id": tax_unit_ids,
        "age": ages,
        "employment_income": employment_income,
        "person_weight": person_weights,
    }

    # Create household data
    household_data = {
        "household_id": list(range(n_households)),
        "state_name": ["CA"] * n_households,  # California
        "household_weight": [1000.0] * n_households,
    }

    # Create group entity data
    marital_unit_data = {
        "marital_unit_id": list(range(n_households)),
        "marital_unit_weight": [1000.0] * n_households,
    }

    family_data = {
        "family_id": list(range(n_households)),
        "family_weight": [1000.0] * n_households,
    }

    spm_unit_data = {
        "spm_unit_id": list(range(n_households)),
        "spm_unit_weight": [1000.0] * n_households,
    }

    tax_unit_data = {
        "tax_unit_id": list(range(n_households)),
        "tax_unit_weight": [1000.0] * n_households,
    }

    # Create MicroDataFrames
    person_df = MicroDataFrame(
        pd.DataFrame(person_data), weights="person_weight"
    )
    household_df = MicroDataFrame(
        pd.DataFrame(household_data), weights="household_weight"
    )
    marital_unit_df = MicroDataFrame(
        pd.DataFrame(marital_unit_data), weights="marital_unit_weight"
    )
    family_df = MicroDataFrame(
        pd.DataFrame(family_data), weights="family_weight"
    )
    spm_unit_df = MicroDataFrame(
        pd.DataFrame(spm_unit_data), weights="spm_unit_weight"
    )
    tax_unit_df = MicroDataFrame(
        pd.DataFrame(tax_unit_data), weights="tax_unit_weight"
    )

    # Create temporary file
    tmpdir = tempfile.mkdtemp()
    filepath = str(Path(tmpdir) / "employment_income_variation_us.h5")

    # Create dataset
    dataset = PolicyEngineUSDataset(
        name="Employment income variation (US)",
        description="Single adult household with 2 children, varying employment income",
        filepath=filepath,
        year=year,
        data=USYearData(
            person=person_df,
            household=household_df,
            marital_unit=marital_unit_df,
            family=family_df,
            spm_unit=spm_unit_df,
            tax_unit=tax_unit_df,
        ),
    )

    return dataset


def run_simulation(dataset: PolicyEngineUSDataset) -> Simulation:
    """Run a single simulation for all employment income variations."""

    simulation = Simulation(
        dataset=dataset,
        tax_benefit_model_version=us_latest,
    )
    simulation.run()
    return simulation


def extract_results_by_employment_income(
    simulation: Simulation, employment_incomes: list[float]
) -> dict:
    """Extract household net income and components for each employment income level.

    Directly accesses output data by row index since we have one household per income level.
    """
    import pandas as pd

    # Get output data
    household_df = pd.DataFrame(simulation.output_dataset.data.household)
    spm_unit_df = pd.DataFrame(simulation.output_dataset.data.spm_unit)
    tax_unit_df = pd.DataFrame(simulation.output_dataset.data.tax_unit)

    # Extract results (one row per household/spm_unit/tax_unit)
    household_net_income = household_df["household_net_income"].tolist()
    household_benefits = household_df["household_benefits"].tolist()
    household_tax = household_df["household_tax"].tolist()

    snap = spm_unit_df["snap"].tolist()
    tanf = spm_unit_df["tanf"].tolist()

    eitc = tax_unit_df["eitc"].tolist()
    ctc = tax_unit_df["ctc"].tolist()

    employment_income_hh = employment_incomes

    return {
        "employment_income": employment_incomes,
        "household_net_income": household_net_income,
        "household_benefits": household_benefits,
        "household_tax": household_tax,
        "employment_income_hh": employment_income_hh,
        "snap": snap,
        "tanf": tanf,
        "eitc": eitc,
        "ctc": ctc,
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
        ("SNAP", results["snap"], COLORS["blue_secondary"]),
        ("TANF", results["tanf"], COLORS["info"]),
        ("EITC", results["eitc"], COLORS["success"]),
        ("CTC", results["ctc"], COLORS["warning"]),
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
        xaxis_title="Employment income ($)",
        yaxis_title="Net income ($)",
        show_legend=True,
        height=700,
        width=1200,
    )

    fig.show()


def main():
    """Main execution function."""
    # Create employment income range from $0 to $200k
    # Using smaller intervals at lower incomes where the relationship is more interesting
    employment_incomes = (
        list(range(0, 40000, 2000))  # $0 to $40k in $2k steps
        + list(range(40000, 100000, 5000))  # $40k to $100k in $5k steps
        + list(range(100000, 200001, 10000))  # $100k to $200k in $10k steps
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
    for emp_inc in [0, 50000, 100000, 200000]:
        idx = (
            employment_incomes.index(emp_inc)
            if emp_inc in employment_incomes
            else -1
        )
        if idx >= 0:
            print(
                f"  Employment income ${emp_inc:,}: household net income ${results['household_net_income'][idx]:,.0f}"
            )

    print("\nGenerating visualisation...")
    visualise_results(results)


if __name__ == "__main__":
    main()
