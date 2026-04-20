---
title: "Impact analysis"
---

`economic_impact_analysis` runs a baseline-vs-reform comparison and returns a bundle of standard outputs — budget cost, poverty change, distributional impact, inequality — in one call.

## One-liner

```python
from policyengine.us import economic_impact_analysis

impact = economic_impact_analysis(
    reform={"gov.irs.credits.ctc.amount.adult_dependent": 1_000},
    year=2026,
)

impact.budget.total_change
impact.poverty.rate_change
impact.deciles.mean_change_by_decile
impact.inequality.gini
```

The UK equivalent is `from policyengine.uk import economic_impact_analysis`.

## What it computes

Each call produces:

| Section | Content |
|---|---|
| `budget` | Total budget cost (`household_net_income` sum change) |
| `poverty` | SPM poverty rate before/after (US) or AHC rate (UK), plus demographic breakdowns |
| `deep_poverty` | Same as above for half-of-poverty-threshold (US only) |
| `deciles` | Mean net-income change by income decile; winners-vs-losers |
| `intra_deciles` | Distribution of impact within each decile |
| `inequality` | Gini and top-income shares |

All sections compute against the same baseline and reform simulations, so results are internally consistent.

## Under the hood

`economic_impact_analysis` is a thin wrapper around the individual output classes — same as composing them manually:

```python
baseline = pe.Simulation(country="us", dataset=DEFAULT_US_DATASET, year=2026)
reformed = pe.Simulation(country="us", dataset=DEFAULT_US_DATASET, year=2026, reform=REFORM)

budget = ChangeAggregate("household_net_income", ChangeAggregateType.DIFFERENCE).compute(baseline, reformed)
poverty = Poverty(...).compute(baseline, reformed)
# ...
```

If you need a subset of outputs or want to cache the baseline across multiple reform scenarios, compose directly rather than calling `economic_impact_analysis` repeatedly.

## Passing your own data

By default, `economic_impact_analysis` uses the pinned default dataset for each country. For custom datasets:

```python
impact = economic_impact_analysis(
    reform=REFORM,
    year=2026,
    dataset="hf://policyengine/policyengine-us-data/enhanced_cps_2023.h5",
)
```

## Non-parametric reforms

For structural reforms, construct the simulations yourself and pass them to the outputs directly. `economic_impact_analysis` only accepts parametric reform dicts.

## Next

- [Outputs](outputs.md) — catalog of individual output classes
- [Regions](regions.md) — state/constituency-level impact breakdowns
- [Examples](examples.md) — full runnable scripts using this helper
