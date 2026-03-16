# Economic impact analysis

The `economic_impact_analysis()` function is the canonical way to compare a baseline simulation against a reform simulation. It produces a comprehensive `PolicyReformAnalysis` containing decile impacts, programme-by-programme statistics, poverty rates, and inequality metrics in a single call.

## Overview

There are two approaches to comparing simulations:

| Approach | Use case |
|---|---|
| `ChangeAggregate` | Single-metric queries: "What is the total tax revenue change?" |
| `economic_impact_analysis()` | Full analysis: decile impacts, programme stats, poverty, inequality |

`ChangeAggregate` gives you one number per call. `economic_impact_analysis()` runs ~30+ aggregate computations and returns a structured result containing everything.

## Full analysis workflow

### US example

```python
import datetime
from policyengine.core import Parameter, ParameterValue, Policy, Simulation
from policyengine.tax_benefit_models.us import (
    economic_impact_analysis,
    ensure_datasets,
    us_latest,
)

# 1. Load data
datasets = ensure_datasets(
    datasets=["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"],
    years=[2026],
    data_folder="./data",
)
dataset = datasets["enhanced_cps_2024_2026"]

# 2. Define reform
param = Parameter(
    name="gov.irs.deductions.standard.amount.SINGLE",
    tax_benefit_model_version=us_latest,
)
reform = Policy(
    name="Double standard deduction (single)",
    parameter_values=[
        ParameterValue(
            parameter=param,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            value=30_950,
        ),
    ],
)

# 3. Create simulations (no need to call .run() — ensure() is called internally)
baseline_sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=us_latest,
)
reform_sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=us_latest,
    policy=reform,
)

# 4. Run full analysis
analysis = economic_impact_analysis(baseline_sim, reform_sim)
```

### UK example

```python
import datetime
from policyengine.core import Parameter, ParameterValue, Policy, Simulation
from policyengine.tax_benefit_models.uk import (
    economic_impact_analysis,
    ensure_datasets,
    uk_latest,
)

datasets = ensure_datasets(
    datasets=["hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5"],
    years=[2026],
    data_folder="./data",
)
dataset = datasets["enhanced_frs_2023_24_2026"]

param = Parameter(
    name="gov.hmrc.income_tax.allowances.personal_allowance.amount",
    tax_benefit_model_version=uk_latest,
)
reform = Policy(
    name="Zero personal allowance",
    parameter_values=[
        ParameterValue(
            parameter=param,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            value=0,
        ),
    ],
)

baseline_sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
reform_sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
    policy=reform,
)

analysis = economic_impact_analysis(baseline_sim, reform_sim)
```

## What `economic_impact_analysis()` computes

The function calls `ensure()` on both simulations (run + cache if not already computed), then produces:

### Decile impacts

Mean income changes by income decile (1-10), with counts of people better off, worse off, and unchanged.

```python
for d in analysis.decile_impacts.outputs:
    print(f"Decile {d.decile}: avg change={d.absolute_change:+.0f}, "
          f"relative={d.relative_change:+.2f}%")
```

**Fields on each `DecileImpact`:**
- `decile`: 1-10
- `baseline_mean`, `reform_mean`: Mean income before and after reform
- `absolute_change`: Mean absolute income change
- `relative_change`: Mean percentage income change
- `count_better_off`, `count_worse_off`, `count_no_change`: Weighted counts

### Programme/program statistics

Per-programme totals, changes, and winner/loser counts.

**US programs analysed:** `income_tax`, `payroll_tax`, `state_income_tax`, `snap`, `tanf`, `ssi`, `social_security`, `medicare`, `medicaid`, `eitc`, `ctc`

**UK programmes analysed:** `income_tax`, `national_insurance`, `vat`, `council_tax`, `universal_credit`, `child_benefit`, `pension_credit`, `income_support`, `working_tax_credit`, `child_tax_credit`

```python
for p in analysis.program_statistics.outputs:  # US
    print(f"{p.program_name}: baseline=${p.baseline_total/1e9:.1f}B, "
          f"reform=${p.reform_total/1e9:.1f}B, change=${p.change/1e9:+.1f}B")
```

**Fields on each `ProgramStatistics` / `ProgrammeStatistics`:**
- `program_name` / `programme_name`: Variable name
- `baseline_total`, `reform_total`: Weighted sums
- `change`: `reform_total - baseline_total`
- `baseline_count`, `reform_count`: Weighted recipient counts
- `winners`, `losers`: Weighted counts of people gaining/losing

### Poverty rates

Poverty headcount and rates for both baseline and reform simulations.

**US poverty types:** SPM poverty, deep SPM poverty

**UK poverty types:** Absolute BHC, absolute AHC, relative BHC, relative AHC

```python
for bp, rp in zip(analysis.baseline_poverty.outputs,
                  analysis.reform_poverty.outputs):
    print(f"{bp.poverty_type}: baseline={bp.rate:.4f}, reform={rp.rate:.4f}")
```

### Inequality metrics

Gini coefficient and income share metrics for both simulations.

```python
bi = analysis.baseline_inequality
ri = analysis.reform_inequality
print(f"Gini: baseline={bi.gini:.4f}, reform={ri.gini:.4f}")
print(f"Top 10% share: baseline={bi.top_10_share:.4f}, reform={ri.top_10_share:.4f}")
print(f"Top 1% share: baseline={bi.top_1_share:.4f}, reform={ri.top_1_share:.4f}")
print(f"Bottom 50% share: baseline={bi.bottom_50_share:.4f}, reform={ri.bottom_50_share:.4f}")
```

## The `PolicyReformAnalysis` return type

```python
class PolicyReformAnalysis(BaseModel):
    decile_impacts: OutputCollection[DecileImpact]
    program_statistics: OutputCollection[ProgramStatistics]       # US
    # programme_statistics: OutputCollection[ProgrammeStatistics]  # UK
    baseline_poverty: OutputCollection[Poverty]
    reform_poverty: OutputCollection[Poverty]
    baseline_inequality: Inequality
    reform_inequality: Inequality
```

Each `OutputCollection` contains:
- `outputs`: List of individual output objects
- `dataframe`: A pandas DataFrame with all results in tabular form

## Using ChangeAggregate for targeted queries

When you only need a single metric, `ChangeAggregate` is more direct than the full analysis pipeline. It requires that both simulations have already been run (or ensure'd).

### Tax revenue change

```python
from policyengine.outputs.change_aggregate import ChangeAggregate, ChangeAggregateType

baseline_sim.run()
reform_sim.run()

revenue = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="household_tax",
    aggregate_type=ChangeAggregateType.SUM,
)
revenue.run()
print(f"Revenue change: ${revenue.result / 1e9:.1f}B")
```

### Winners and losers

```python
winners = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_geq=1,  # Gained at least $1
)
winners.run()

losers = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_leq=-1,  # Lost at least $1
)
losers.run()
```

### Filtering by income decile

```python
# Average loss in the 3rd income decile
avg_loss = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.MEAN,
    filter_variable="household_net_income",
    quantile=10,
    quantile_eq=3,
)
avg_loss.run()
```

### Filter options reference

**Absolute change filters:**
- `change_geq`: Change >= value (e.g., gain >= 500)
- `change_leq`: Change <= value (e.g., loss <= -500)
- `change_eq`: Change == value

**Relative change filters:**
- `relative_change_geq`: Relative change >= value (decimal, e.g., 0.05 = 5%)
- `relative_change_leq`: Relative change <= value
- `relative_change_eq`: Relative change == value

**Variable filters:**
- `filter_variable`: Variable to filter on (from the baseline simulation)
- `filter_variable_eq`, `filter_variable_leq`, `filter_variable_geq`: Comparison operators

**Quantile filters:**
- `quantile`: Number of quantiles (e.g., 10 for deciles, 5 for quintiles)
- `quantile_eq`: Exact quantile (e.g., 3 for 3rd decile)
- `quantile_leq`: Maximum quantile
- `quantile_geq`: Minimum quantile

## Examples

- [UK policy reform analysis](examples.md#uk-policy-reform-analysis): Full reform analysis with ChangeAggregate and visualisation
- [US budgetary impact](examples.md#us-budgetary-impact): Budgetary impact comparing both approaches
