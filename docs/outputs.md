---
title: "Outputs"
---

Outputs are callables that consume a `Simulation` (or baseline + reform pair) and return a typed result. Every page uses the same pattern: construct the output with the variables you want, call `.compute(sim)` or `.compute(baseline, reformed)`.

## Aggregate

Single-number summaries over the population.

```python
from policyengine.outputs import Aggregate, AggregateType

cost = Aggregate(variable="snap", type=AggregateType.SUM).compute(baseline)
average = Aggregate(variable="household_net_income", type=AggregateType.MEAN).compute(baseline)
```

`AggregateType` options: `SUM`, `MEAN`, `MEDIAN`, `COUNT_POSITIVE`, `COUNT`, plus quantile types.

### Filtering

Apply a pandas-style filter to the population before aggregating:

```python
Aggregate(
    variable="household_net_income",
    type=AggregateType.MEAN,
    filter="household_size >= 4",
).compute(baseline)
```

## ChangeAggregate

Difference or percent change between a baseline and a reform.

```python
from policyengine.outputs import ChangeAggregate, ChangeAggregateType

impact = ChangeAggregate(
    variable="household_net_income",
    type=ChangeAggregateType.DIFFERENCE,
).compute(baseline, reformed)
```

`ChangeAggregateType` options: `DIFFERENCE`, `PERCENT_CHANGE`, `RELATIVE_CHANGE`.

## DecileImpact

Average net-income change by income decile, and winners-vs-losers counts.

```python
from policyengine.outputs import DecileImpact

impact = DecileImpact().compute(baseline, reformed)

impact.mean_change_by_decile          # dict {1: -50, 2: 120, ...}
impact.winners_losers_by_decile       # dict {1: {"winners": 0.1, "losers": 0.3, "neutral": 0.6}, ...}
```

Defaults to household-level equivalized net income. Pass `income_variable=` to override.

## IntraDecileImpact

Distribution of household-level impact within each income decile — not just mean, but how much spread.

```python
from policyengine.outputs import IntraDecileImpact

spread = IntraDecileImpact().compute(baseline, reformed)
```

## Poverty

Poverty rate before and after a reform, by demographic group.

```python
from policyengine.outputs import Poverty, AGE_GROUPS, RACE_GROUPS

rates = Poverty(
    income_variable="spm_unit_net_income",
    poverty_measure="spm",
    groups=AGE_GROUPS + RACE_GROUPS,
).compute(baseline, reformed)
```

US defaults cover SPM; UK defaults cover AHC and BHC. Deep poverty is available with `measure="deep_spm"` (US).

## Inequality

Gini and top income shares.

```python
from policyengine.outputs import Inequality, USInequalityPreset

result = Inequality(preset=USInequalityPreset.SPM).compute(baseline, reformed)

result.gini                              # {'baseline': 0.48, 'reformed': 0.47}
result.top_ten_share                     # before/after
result.top_one_share
result.top_tenth_of_one_share
```

## Geographic breakdowns

### CongressionalDistrictImpact (US)

```python
from policyengine.outputs import CongressionalDistrictImpact

impacts = CongressionalDistrictImpact().compute(baseline, reformed)
# Per-district winners/losers, cost, poverty change
```

### ConstituencyImpact (UK) / LocalAuthorityImpact (UK)

```python
from policyengine.outputs import ConstituencyImpact, LocalAuthorityImpact

constituency = ConstituencyImpact().compute(baseline, reformed)
la = LocalAuthorityImpact().compute(baseline, reformed)
```

## ProgramStatistics

Program-level counts and dollar amounts — who enrolls, how much they receive.

```python
from policyengine.outputs import ProgramStatistics

stats = ProgramStatistics(program="snap").compute(baseline)

stats.total_households
stats.total_enrolled
stats.total_cost
stats.mean_benefit
```

## Combining outputs

Every output stores a `to_dict()` representation. Collect them into a dashboard via a collection:

```python
from policyengine.core import OutputCollection

dashboard = OutputCollection(
    cost=ChangeAggregate("snap", ChangeAggregateType.DIFFERENCE),
    poverty=Poverty(income_variable="spm_unit_net_income"),
    deciles=DecileImpact(),
).compute(baseline, reformed)
```

The collection dispatches to each output and returns a dict keyed by the names you assign.

## Writing your own output

Subclass `Output` or `ChangeOutput`. See `src/policyengine/outputs/aggregate.py` for the simplest reference implementation.
