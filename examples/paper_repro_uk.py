"""Reproduce the UK policy-reform analysis used in the JOSS paper draft.

This script uses the same reform shown in `paper.md`, but adds the missing
dataset setup so it can run end-to-end from a fresh checkout.

Run:
    uv run --python 3.14 --extra uk python examples/paper_repro_uk.py
"""

import datetime

from policyengine.core import Parameter, ParameterValue, Policy, Simulation
from policyengine.tax_benefit_models.uk import (
    ensure_datasets,
    economic_impact_analysis,
    uk_latest,
)


def load_dataset(year: int = 2026):
    """Load or create the enhanced UK dataset used for population analysis."""
    datasets = ensure_datasets(
        datasets=["hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5"],
        years=[year],
    )
    return datasets[f"enhanced_frs_2023_24_{year}"]


def create_reform(year: int = 2026) -> Policy:
    """Set the UK personal allowance to zero for one tax year."""
    parameter = Parameter(
        name="gov.hmrc.income_tax.allowances.personal_allowance.amount",
        tax_benefit_model_version=uk_latest,
    )

    return Policy(
        name="Zero personal allowance",
        parameter_values=[
            ParameterValue(
                parameter=parameter,
                start_date=datetime.date(year, 1, 1),
                end_date=datetime.date(year, 12, 31),
                value=0,
            )
        ],
    )


def main():
    dataset = load_dataset()
    reform = create_reform()

    baseline = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
    )
    reformed = Simulation(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
        policy=reform,
    )

    analysis = economic_impact_analysis(baseline, reformed)

    first_decile = analysis.decile_impacts.outputs[0]

    print(f"Dataset: {dataset.filepath}")
    print(f"Households: {len(dataset.data.household):,}")
    print(f"Baseline Gini: {analysis.baseline_inequality.gini:.4f}")
    print(f"Reform Gini: {analysis.reform_inequality.gini:.4f}")
    print(f"Decile 1 mean change: {first_decile.absolute_change:,.2f}")
    print(f"Programmes analysed: {len(analysis.programme_statistics.outputs)}")


if __name__ == "__main__":
    main()
