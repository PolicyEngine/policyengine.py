---
title: "Impact analysis"
---

`economic_impact_analysis` runs a baseline and a reform simulation through a bundled set of outputs — decile impacts, program statistics, poverty, and inequality — and returns a typed `PolicyReformAnalysis`.

## Usage

```python
import policyengine as pe
from policyengine.core import Simulation

datasets = pe.us.ensure_datasets(
    datasets=["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"],
    years=[2026],
)
dataset = datasets["enhanced_cps_2024_2026"]

baseline = Simulation(dataset=dataset, tax_benefit_model_version=pe.us.model)
reformed = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.us.model,
    policy={"gov.irs.credits.ctc.amount.base[0].amount": 3_000},
)

analysis = pe.us.economic_impact_analysis(baseline, reformed)
```

The UK equivalent is `pe.uk.economic_impact_analysis`. Both call `Simulation.ensure()` internally — run/cached simulations are reused, fresh ones are computed and cached.

## What it returns

A `PolicyReformAnalysis` with:

| Attribute | Type | Content |
|---|---|---|
| `decile_impacts` | `OutputCollection[DecileImpact]` | Mean baseline / reform / change and winner-loser counts per decile |
| `program_statistics` | `OutputCollection[ProgramStatistics]` | Totals, counts, winners/losers per program |
| `baseline_poverty` | `OutputCollection[Poverty]` | Baseline rates by measure and demographic group |
| `reform_poverty` | `OutputCollection[Poverty]` | Reform rates, same schema as baseline |
| `baseline_inequality` | `Inequality` | Gini plus top / bottom income shares (baseline) |
| `reform_inequality` | `Inequality` | Same, under the reform |

`OutputCollection` exposes `.outputs` (typed list) and `.dataframe` (flat DataFrame).

```python
for prog in analysis.program_statistics.outputs:
    print(prog.program_name, prog.change)

for d in analysis.decile_impacts.outputs:
    print(d.decile, d.absolute_change, d.relative_change)

analysis.reform_inequality.gini - analysis.baseline_inequality.gini
```

## When to call it

- Producing a reform brief covering multiple metrics
- Standardising reporting across reforms where each run should cover the same bundle

## When not to

- If you only need one number (a budget cost, a single poverty rate), `ChangeAggregate` / `Aggregate` / `Poverty` avoids running ~30+ aggregations.
- If you're sweeping a parameter, cache the baseline and build a new reform simulation per iteration:

```python
baseline = Simulation(dataset=dataset, tax_benefit_model_version=pe.us.model)
for amount in [0, 1_000, 2_000, 3_000]:
    reformed = Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        policy={"gov.irs.credits.ctc.amount.base[0].amount": amount},
    )
    analysis = pe.us.economic_impact_analysis(baseline, reformed)
```

## Composing manually

`economic_impact_analysis` is a thin wrapper over the convenience functions in `policyengine.outputs`. Replicate it if you need a different bundle or can skip sections:

```python
from policyengine.outputs import (
    ChangeAggregate, ChangeAggregateType,
    calculate_decile_impacts,
    calculate_us_poverty_rates,
    calculate_us_inequality,
)

budget = ChangeAggregate(
    baseline_simulation=baseline,
    reform_simulation=reformed,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.SUM,
)
budget.run()

deciles = calculate_decile_impacts(baseline_simulation=baseline, reform_simulation=reformed)

baseline_poverty = calculate_us_poverty_rates(simulation=baseline)
reform_poverty = calculate_us_poverty_rates(simulation=reformed)

baseline_ineq = calculate_us_inequality(simulation=baseline)
reform_ineq = calculate_us_inequality(simulation=reformed)
```

## Next

- [Outputs](outputs.md) — individual output classes and their options
- [Regions](regions.md) — state, constituency, and district breakdowns
- [Examples](examples.md) — runnable scripts using this helper
