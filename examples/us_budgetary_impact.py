"""Example: US budgetary impact comparison between baseline and reform.

Demonstrates the canonical policyengine.py workflow:
1. Ensure datasets exist (download + compute or load from cache)
2. Define a parametric reform
3. Run baseline and reform simulations
4. Use economic_impact_analysis() for the full analysis
5. Use ChangeAggregate for targeted single-metric queries

Run: python examples/us_budgetary_impact.py

System requirements: this example holds two full enhanced-CPS US
simulations in memory simultaneously to compute reform-vs-baseline
deltas. On a 2026 dataset (~101k people / 41k households) peak memory
has been observed at ~7.5 GiB RSS / ~80 GiB virtual, and end-to-end
runtime is ~20 minutes on a developer laptop. Run with at least 16 GiB
of free RAM and expect to close other memory-heavy applications. See
https://github.com/PolicyEngine/policyengine.py/issues/328 for tracking.
"""

import datetime

from policyengine.core import Parameter, ParameterValue, Policy, Simulation
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType,
)
from policyengine.tax_benefit_models.us import (
    economic_impact_analysis,
    ensure_datasets,
    us_latest,
)


def main():
    year = 2026

    # ── Step 1: Get dataset (downloads from HuggingFace on first run) ──
    print("Ensuring datasets are available...")
    datasets = ensure_datasets(
        datasets=["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"],
        years=[year],
        data_folder="./data",
    )
    dataset = datasets[f"enhanced_cps_2024_{year}"]
    print(f"  Loaded: {dataset}")

    # ── Step 2: Define a reform ──
    # Example: double the standard deduction for single filers
    param = Parameter(
        name="gov.irs.deductions.standard.amount.SINGLE",
        tax_benefit_model_version=us_latest,
    )
    reform = Policy(
        name="Double standard deduction (single)",
        parameter_values=[
            ParameterValue(
                parameter=param,
                start_date=datetime.date(year, 1, 1),
                end_date=datetime.date(year, 12, 31),
                value=30_950,
            ),
        ],
    )

    # ── Step 3: Create simulations ──
    baseline_sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=us_latest,
    )
    reform_sim = Simulation(
        dataset=dataset,
        tax_benefit_model_version=us_latest,
        policy=reform,
    )

    # ── Step 4a: Quick budgetary number via ChangeAggregate ──
    # This requires running the simulations first.
    print("\nRunning simulations...")
    baseline_sim.run()
    reform_sim.run()

    tax_change = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="household_tax",
        aggregate_type=ChangeAggregateType.SUM,
    )
    tax_change.run()
    print("\nQuick budgetary result:")
    print(f"  Tax revenue change: ${tax_change.result / 1e9:.2f}B")

    # Count winners and losers
    winners = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="household_net_income",
        aggregate_type=ChangeAggregateType.COUNT,
        change_geq=1,
    )
    losers = ChangeAggregate(
        baseline_simulation=baseline_sim,
        reform_simulation=reform_sim,
        variable="household_net_income",
        aggregate_type=ChangeAggregateType.COUNT,
        change_leq=-1,
    )
    winners.run()
    losers.run()
    print(f"  Winners: {winners.result / 1e6:.2f}M households")
    print(f"  Losers: {losers.result / 1e6:.2f}M households")

    # ── Step 4b: Full analysis via economic_impact_analysis ──
    # Note: this calls .ensure() internally, which is a no-op here since
    # we already ran the simulations above. If we hadn't called .run(),
    # ensure() would run + cache them automatically.
    print("\nRunning full economic impact analysis...")
    analysis = economic_impact_analysis(baseline_sim, reform_sim)

    print("\n=== Program-by-Program Impact ===")
    for prog in analysis.program_statistics.outputs:
        print(
            f"  {prog.program_name:30s}  "
            f"baseline=${prog.baseline_total / 1e9:8.1f}B  "
            f"reform=${prog.reform_total / 1e9:8.1f}B  "
            f"change=${prog.change / 1e9:+8.1f}B"
        )

    print("\n=== Decile Impacts ===")
    for d in analysis.decile_impacts.outputs:
        print(
            f"  Decile {d.decile:2d}:  "
            f"avg change=${d.absolute_change:+8.0f}  "
            f"relative={d.relative_change:+.2%}"
        )

    print("\n=== Poverty ===")
    for bp, rp in zip(
        analysis.baseline_poverty.outputs,
        analysis.reform_poverty.outputs,
        strict=True,
    ):
        print(
            f"  {bp.metric:30s}  "
            f"baseline={bp.rate:.4f}  "
            f"reform={rp.rate:.4f}  "
            f"change={rp.rate - bp.rate:+.4f}"
        )

    print("\n=== Inequality ===")
    bi = analysis.baseline_inequality
    ri = analysis.reform_inequality
    print(f"  Gini:           baseline={bi.gini:.4f}  reform={ri.gini:.4f}")
    print(
        f"  Top 10% share:  baseline={bi.top_10_share:.4f}  reform={ri.top_10_share:.4f}"
    )
    print(
        f"  Top 1% share:   baseline={bi.top_1_share:.4f}  reform={ri.top_1_share:.4f}"
    )


if __name__ == "__main__":
    main()
