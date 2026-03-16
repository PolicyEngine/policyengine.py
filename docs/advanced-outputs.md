# Advanced outputs

Beyond `Aggregate` and `ChangeAggregate` (covered in [Core concepts](core-concepts.md)), the package provides specialised output types for distributional analysis, poverty measurement, and inequality metrics.

All output types follow the same pattern: create an instance, call `.run()`, read the result fields. Convenience functions are provided for common use cases.

## OutputCollection

Many convenience functions return an `OutputCollection[T]`, a container holding both the individual output objects and a pandas DataFrame:

```python
from policyengine.core import OutputCollection

# Returned by calculate_decile_impacts(), calculate_us_poverty_rates(), etc.
collection = calculate_us_poverty_rates(simulation)

# Access individual objects
for poverty in collection.outputs:
    print(f"{poverty.poverty_type}: {poverty.rate:.4f}")

# Access as DataFrame
print(collection.dataframe)
```

## DecileImpact

Calculates the impact of a policy reform on a single income decile: baseline and reform mean income, absolute and relative change, and counts of people better off, worse off, and unchanged.

### Using the convenience function

```python
from policyengine.outputs.decile_impact import calculate_decile_impacts

decile_impacts = calculate_decile_impacts(
    dataset=dataset,
    tax_benefit_model_version=us_latest,
    baseline_policy=None,           # Current law
    reform_policy=reform,
    income_variable="household_net_income",  # Default for US
)

for d in decile_impacts.outputs:
    print(f"Decile {d.decile}: "
          f"baseline={d.baseline_mean:,.0f}, "
          f"reform={d.reform_mean:,.0f}, "
          f"change={d.absolute_change:+,.0f} "
          f"({d.relative_change:+.2f}%)")
```

### Using directly

```python
from policyengine.outputs.decile_impact import DecileImpact

impact = DecileImpact(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    income_variable="household_net_income",
    decile=5,  # 5th decile
)
impact.run()

print(f"Count better off: {impact.count_better_off:,.0f}")
print(f"Count worse off: {impact.count_worse_off:,.0f}")
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `income_variable` | `equiv_hbai_household_net_income` | Income variable to group by and measure changes |
| `decile_variable` | `None` | Use a pre-computed grouping variable instead of `qcut` |
| `entity` | Auto-detected | Entity level for the income variable |
| `quantiles` | `10` | Number of quantile groups (10 = deciles, 5 = quintiles) |

For US simulations, use `income_variable="household_net_income"`. The UK default (`equiv_hbai_household_net_income`) is the equivalised HBAI measure.

## IntraDecileImpact

Classifies people within each decile into five income change categories:

| Category | Threshold |
|---|---|
| Lose more than 5% | change <= -5% |
| Lose less than 5% | -5% < change <= -0.1% |
| No change | -0.1% < change <= 0.1% |
| Gain less than 5% | 0.1% < change <= 5% |
| Gain more than 5% | change > 5% |

Proportions are people-weighted (using `household_count_people * household_weight`).

### Using the convenience function

```python
from policyengine.outputs.intra_decile_impact import compute_intra_decile_impacts

intra = compute_intra_decile_impacts(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    income_variable="household_net_income",
)

for row in intra.outputs:
    if row.decile == 0:
        label = "Overall"
    else:
        label = f"Decile {row.decile}"
    print(f"{label}: "
          f"lose>5%={row.lose_more_than_5pct:.2%}, "
          f"lose<5%={row.lose_less_than_5pct:.2%}, "
          f"no change={row.no_change:.2%}, "
          f"gain<5%={row.gain_less_than_5pct:.2%}, "
          f"gain>5%={row.gain_more_than_5pct:.2%}")
```

The function returns deciles 1-10 plus an overall average at `decile=0`.

## Poverty

Calculates poverty headcount and rates for a single simulation, with optional demographic filtering.

### Poverty types

**UK** (4 measures):
- Absolute before housing costs (BHC)
- Absolute after housing costs (AHC)
- Relative before housing costs (BHC)
- Relative after housing costs (AHC)

**US** (2 measures):
- SPM poverty
- Deep SPM poverty (below 50% of SPM threshold)

### Calculating all poverty rates

```python
from policyengine.outputs.poverty import (
    calculate_uk_poverty_rates,
    calculate_us_poverty_rates,
)

# US
us_poverty = calculate_us_poverty_rates(simulation)
for p in us_poverty.outputs:
    print(f"{p.poverty_type}: headcount={p.headcount:,.0f}, rate={p.rate:.4f}")

# UK
uk_poverty = calculate_uk_poverty_rates(simulation)
for p in uk_poverty.outputs:
    print(f"{p.poverty_type}: headcount={p.headcount:,.0f}, rate={p.rate:.4f}")
```

### Poverty by demographic group

```python
from policyengine.outputs.poverty import (
    calculate_us_poverty_by_age,
    calculate_us_poverty_by_gender,
    calculate_us_poverty_by_race,
    calculate_uk_poverty_by_age,
    calculate_uk_poverty_by_gender,
)

# By age group (child <18, adult 18-64, senior 65+)
by_age = calculate_us_poverty_by_age(simulation)
for p in by_age.outputs:
    print(f"{p.filter_group} {p.poverty_type}: {p.rate:.4f}")

# By gender
by_gender = calculate_us_poverty_by_gender(simulation)

# By race (US only: WHITE, BLACK, HISPANIC, OTHER)
by_race = calculate_us_poverty_by_race(simulation)
```

### Custom filters

```python
from policyengine.outputs.poverty import Poverty

# Child poverty only
child_poverty = Poverty(
    simulation=simulation,
    poverty_variable="spm_unit_is_in_spm_poverty",
    entity="person",
    filter_variable="age",
    filter_variable_leq=17,
)
child_poverty.run()
print(f"Child SPM poverty rate: {child_poverty.rate:.4f}")
```

### Result fields

| Field | Description |
|---|---|
| `headcount` | Weighted count of people in poverty |
| `total_population` | Weighted total population (after filters) |
| `rate` | `headcount / total_population` |
| `filter_group` | Group label set by demographic convenience functions |

## Inequality

Calculates weighted inequality metrics for a single simulation: Gini coefficient and income share measures.

### Using convenience functions

```python
from policyengine.outputs.inequality import (
    calculate_uk_inequality,
    calculate_us_inequality,
)

# US (uses household_net_income by default)
ineq = calculate_us_inequality(simulation)
print(f"Gini: {ineq.gini:.4f}")
print(f"Top 10% share: {ineq.top_10_share:.4f}")
print(f"Top 1% share: {ineq.top_1_share:.4f}")
print(f"Bottom 50% share: {ineq.bottom_50_share:.4f}")

# UK (uses equiv_hbai_household_net_income by default)
ineq = calculate_uk_inequality(simulation)
```

### With demographic filters

```python
# Inequality among working-age adults only
ineq = calculate_us_inequality(
    simulation,
    filter_variable="age",
    filter_variable_geq=18,
    filter_variable_leq=64,
)
```

### Using directly

```python
from policyengine.outputs.inequality import Inequality

ineq = Inequality(
    simulation=simulation,
    income_variable="household_net_income",
    entity="household",
)
ineq.run()
```

### Result fields

| Field | Description |
|---|---|
| `gini` | Weighted Gini coefficient (0 = perfect equality, 1 = perfect inequality) |
| `top_10_share` | Share of total income held by top 10% |
| `top_1_share` | Share of total income held by top 1% |
| `bottom_50_share` | Share of total income held by bottom 50% |

## Comparing baseline and reform

Poverty and inequality are single-simulation outputs. To compare baseline and reform, compute both and take the difference:

```python
baseline_poverty = calculate_us_poverty_rates(baseline_sim)
reform_poverty = calculate_us_poverty_rates(reform_sim)

for bp, rp in zip(baseline_poverty.outputs, reform_poverty.outputs):
    change = rp.rate - bp.rate
    print(f"{bp.poverty_type}: {bp.rate:.4f} -> {rp.rate:.4f} ({change:+.4f})")

baseline_ineq = calculate_us_inequality(baseline_sim)
reform_ineq = calculate_us_inequality(reform_sim)
print(f"Gini change: {reform_ineq.gini - baseline_ineq.gini:+.4f}")
```

The `economic_impact_analysis()` function does this automatically and returns both baseline and reform poverty/inequality in the `PolicyReformAnalysis` result. See [Economic impact analysis](economic-impact-analysis.md).
