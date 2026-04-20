---
title: "Outputs"
---

Outputs are Pydantic models that hold a simulation (or a baseline + reform pair) plus configuration, and populate result fields when you call `.run()`.

```python
out = Aggregate(
    simulation=baseline,
    variable="snap",
    aggregate_type=AggregateType.SUM,
)
out.run()
out.result
```

Convenience functions (e.g. `calculate_decile_impacts`, `calculate_us_poverty_rates`) construct and run collections of outputs in one call and return an `OutputCollection[T]` with `.outputs` (typed list) and `.dataframe`.

## Aggregate

Single-number summaries over one simulation.

```python
from policyengine.outputs import Aggregate, AggregateType

snap = Aggregate(
    simulation=baseline,
    variable="snap",
    aggregate_type=AggregateType.SUM,
)
snap.run()
snap.result
```

`AggregateType` values: `SUM`, `MEAN`, `COUNT`.

Filter by another variable:

```python
Aggregate(
    simulation=baseline,
    variable="household_net_income",
    aggregate_type=AggregateType.MEAN,
    filter_variable="household_size",
    filter_variable_geq=4,
)
```

Or by quantile:

```python
Aggregate(
    simulation=baseline,
    variable="household_net_income",
    aggregate_type=AggregateType.MEAN,
    filter_variable="household_net_income",
    quantile=10,
    quantile_eq=1,          # bottom decile
)
```

## ChangeAggregate

Difference between a baseline and a reform, optionally filtered.

```python
from policyengine.outputs import ChangeAggregate, ChangeAggregateType

budget = ChangeAggregate(
    baseline_simulation=baseline,
    reform_simulation=reform,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.SUM,
)
budget.run()
budget.result
```

`ChangeAggregateType` values: `SUM`, `MEAN`, `COUNT`.

The change is `reform - baseline`. Filter on the change itself:

```python
winners = ChangeAggregate(
    baseline_simulation=baseline,
    reform_simulation=reform,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_geq=1,           # households gaining at least $1
)
```

Or on a relative change — `relative_change_geq=0.05` selects households with a 5 %+ gain.

## DecileImpact

One decile's baseline mean, reform mean, and mean change. For all ten at once, use `calculate_decile_impacts`.

```python
from policyengine.outputs import calculate_decile_impacts

impacts = calculate_decile_impacts(
    baseline_simulation=baseline,
    reform_simulation=reform,
    income_variable="household_net_income",
)

for row in impacts.outputs:
    print(row.decile, row.absolute_change, row.relative_change)

impacts.dataframe                        # same data as a DataFrame
```

## IntraDecileImpact

Distribution of household-level impact within each decile (five bucket categories summing to 1.0). Use `compute_intra_decile_impacts` for the full set.

```python
from policyengine.outputs import compute_intra_decile_impacts

spread = compute_intra_decile_impacts(
    baseline_simulation=baseline,
    reform_simulation=reform,
    income_variable="household_net_income",
)
```

## Poverty

Poverty headcount and rate for one measure and one simulation.

```python
from policyengine.outputs import Poverty

rate = Poverty(
    simulation=baseline,
    poverty_variable="spm_unit_is_in_spm_poverty",
    entity="person",
)
rate.run()
rate.headcount, rate.total_population, rate.rate
```

For both baseline and reform, covering the canonical demographic breakdowns:

```python
from policyengine.outputs import calculate_us_poverty_rates

rates = calculate_us_poverty_rates(baseline_simulation=baseline, reform_simulation=reform)
rates.outputs                 # Poverty entries for each group × measure × sim
rates.dataframe
```

Equivalents exist for age, gender, and race: `calculate_us_poverty_by_age`, `_by_gender`, `_by_race`, and UK counterparts.

## Inequality

Gini, top-10 share, top-1 share, bottom-50 share — for one simulation.

```python
from policyengine.outputs import Inequality

ineq = Inequality(
    simulation=baseline,
    income_variable="household_net_income",
    entity="household",
)
ineq.run()
ineq.gini, ineq.top_10_share, ineq.top_1_share, ineq.bottom_50_share
```

For a baseline-vs-reform pair with sensible defaults:

```python
from policyengine.outputs import calculate_us_inequality, USInequalityPreset

baseline_ineq, reform_ineq = calculate_us_inequality(
    baseline_simulation=baseline,
    reform_simulation=reform,
    preset=USInequalityPreset.STANDARD,
)
```

## ProgramStatistics

Per-program totals, counts, and winners/losers for a reform.

```python
from policyengine.outputs import ProgramStatistics

stats = ProgramStatistics(
    baseline_simulation=baseline,
    reform_simulation=reform,
    program_name="snap",
    entity="spm_unit",
)
stats.run()
stats.baseline_total, stats.reform_total, stats.change
stats.baseline_count, stats.reform_count
stats.winners, stats.losers
```

`is_tax=True` treats the variable as a tax (positive baseline is a cost to households).

## Geographic outputs

### US congressional districts

```python
from policyengine.outputs import compute_us_congressional_district_impacts

impacts = compute_us_congressional_district_impacts(
    baseline_simulation=baseline,
    reform_simulation=reform,
)
for row in impacts.district_results:
    print(row["district_geoid"], row["avg_change"], row["winner_percentage"])
```

### UK constituencies / local authorities

Constituency and local-authority breakdowns require externally-supplied weight matrices:

```python
from policyengine.outputs import compute_uk_constituency_impacts

impacts = compute_uk_constituency_impacts(
    baseline_simulation=baseline,
    reform_simulation=reform,
    weight_matrix_path="parliamentary_constituency_weights.h5",
    constituency_csv_path="constituencies_2024.csv",
    year="2025",
)
impacts.constituency_results
```

`compute_uk_local_authority_impacts` follows the same pattern. See [Regions](regions.md).

## Writing your own

Subclass `Output`, declare Pydantic fields for configuration and results, implement `run()` to populate the result fields. The base class is a plain `BaseModel` — see `src/policyengine/outputs/aggregate.py` for the simplest reference implementation.
