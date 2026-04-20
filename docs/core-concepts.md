# Core concepts

PolicyEngine.py is a Python package for tax-benefit microsimulation analysis. It provides a unified interface for running policy simulations, analysing distributional impacts, and visualising results across different countries.

## Quick start

Most analyses start from the country entry points on the top-level
package — ``policyengine.uk`` and ``policyengine.us``. They expose flat
keyword-argument functions that return structured results with
dot-access for scalar lookups.

```python
import policyengine as pe

# UK: single adult earning £50,000
uk = pe.uk.calculate_household(
    people=[{"age": 35, "employment_income": 50_000}],
    year=2026,
)
print(uk.household.hbai_household_net_income)  # net income
print(uk.person[0].income_tax)                  # per-person dot access

# US: married couple with two kids in Texas
us = pe.us.calculate_household(
    people=[
        {"age": 35, "employment_income": 40_000},
        {"age": 33},
        {"age": 8},
        {"age": 5},
    ],
    tax_unit={"filing_status": "JOINT"},
    household={"state_code": "TX"},
    year=2026,
)
print(us.tax_unit.income_tax, us.tax_unit.eitc, us.tax_unit.ctc)

# Apply a reform: just pass a parameter-path dict
reformed = pe.us.calculate_household(
    people=[{"age": 35, "employment_income": 60_000}],
    tax_unit={"filing_status": "SINGLE"},
    year=2026,
    reform={"gov.irs.credits.ctc.amount.adult_dependent": 1000},
)
```

Reforms can be scalar values (treated as ``{year}-01-01`` onwards) or a
mapping of effective-date strings to values for time-varying reforms.
Unknown variable names raise with suggestions instead of silently
returning zero.

For population-level analysis (budget impact, distributional effects),
see [Economic impact analysis](economic-impact-analysis.md).

## Architecture overview

The package is organised around several core concepts:

- **Tax-benefit models**: Country-specific implementations (UK, US) that define tax and benefit rules
- **Datasets**: Microdata representing populations at entity level (person, household, etc.)
- **Simulations**: Execution environments that apply tax-benefit models to datasets
- **Outputs**: Analysis tools for extracting insights from simulation results
- **Policies**: Parametric reforms that modify tax-benefit system parameters

## Tax-benefit models

Tax-benefit models define the rules and calculations for a country's tax and benefit system. Each model version contains:

- **Variables**: Calculated values (e.g., income tax, universal credit)
- **Parameters**: System settings (e.g., personal allowance, benefit rates)
- **Parameter values**: Time-bound values for parameters

### Using a tax-benefit model

The country entry points expose pinned model versions as ``pe.uk.model``
and ``pe.us.model``:

```python
import policyengine as pe

uk_latest = pe.uk.model
us_latest = pe.us.model

# UK model includes variables like:
# - income_tax, national_insurance, universal_credit
# - Parameters like personal allowance, NI thresholds

# US model includes variables like:
# - income_tax, payroll_tax, eitc, ctc, snap
# - Parameters like standard deduction, EITC rates
```

## Datasets

Datasets contain microdata representing a population. Each dataset has:

- **Entity-level data**: Separate dataframes for person, household, and other entities
- **Weights**: Survey weights for population representation
- **Join keys**: Relationships between entities (e.g., which household each person belongs to)

### Dataset structure

```python
from policyengine.tax_benefit_models.uk import PolicyEngineUKDataset  # or: pe.uk.PolicyEngineUKDataset

dataset = PolicyEngineUKDataset(
    name="FRS 2023-24",
    description="Family Resources Survey microdata",
    filepath="./data/frs_2023_24_year_2026.h5",
    year=2026,
)

# Access entity-level data
person_data = dataset.data.person      # MicroDataFrame
household_data = dataset.data.household
benunit_data = dataset.data.benunit    # Benefit unit (UK only)
```

### Creating custom datasets

You can create custom datasets for scenario analysis:

```python
import pandas as pd
from microdf import MicroDataFrame
from policyengine.tax_benefit_models.uk import PolicyEngineUKDataset, UKYearData

# Create person data
person_df = MicroDataFrame(
    pd.DataFrame({
        "person_id": [0, 1, 2],
        "person_household_id": [0, 0, 1],
        "person_benunit_id": [0, 0, 1],
        "age": [35, 8, 40],
        "employment_income": [30000, 0, 50000],
        "person_weight": [1.0, 1.0, 1.0],
    }),
    weights="person_weight"
)

# Create household data
household_df = MicroDataFrame(
    pd.DataFrame({
        "household_id": [0, 1],
        "region": ["LONDON", "SOUTH_EAST"],
        "rent": [15000, 12000],
        "household_weight": [1.0, 1.0],
    }),
    weights="household_weight"
)

# Create benunit data
benunit_df = MicroDataFrame(
    pd.DataFrame({
        "benunit_id": [0, 1],
        "would_claim_uc": [True, True],
        "benunit_weight": [1.0, 1.0],
    }),
    weights="benunit_weight"
)

dataset = PolicyEngineUKDataset(
    name="Custom scenario",
    description="Single parent vs single adult",
    filepath="./custom.h5",
    year=2026,
    data=UKYearData(
        person=person_df,
        household=household_df,
        benunit=benunit_df,
    )
)
```

## Data loading

Before running simulations, you need representative microdata. The package provides three functions for managing datasets:

- **`ensure_datasets()`**: Load from disk if available, otherwise download and compute (recommended)
- **`create_datasets()`**: Always download from HuggingFace and compute from scratch
- **`load_datasets()`**: Load previously saved HDF5 files from disk

```python
from policyengine.tax_benefit_models.us import ensure_datasets  # or: pe.us.ensure_datasets

# First run: downloads from HuggingFace, computes variables, saves to ./data/
# Subsequent runs: loads from disk instantly
datasets = ensure_datasets(
    datasets=["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"],
    years=[2026],
    data_folder="./data",
)
dataset = datasets["enhanced_cps_2024_2026"]
```

```python
from policyengine.tax_benefit_models.uk import ensure_datasets  # or: pe.uk.ensure_datasets

datasets = ensure_datasets(
    datasets=["hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5"],
    years=[2026],
    data_folder="./data",
)
dataset = datasets["enhanced_frs_2023_24_2026"]
```

All datasets are stored as HDF5 files on disk. No database server is required.

## Simulations

Simulations apply tax-benefit models to datasets, calculating all variables for the specified year.

### Running a simulation

```python
import policyengine as pe
from policyengine.core import Simulation

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
)
simulation.run()

# Access output data
output_person = simulation.output_dataset.data.person
output_household = simulation.output_dataset.data.household

# Check calculated variables
print(output_household[["household_id", "household_net_income", "household_tax"]])
```

### Simulation lifecycle: `run()` vs `ensure()`

The `Simulation` class provides two methods for computing results:

| Method | Behaviour |
|---|---|
| `simulation.run()` | Always recomputes from scratch. No caching. |
| `simulation.ensure()` | Checks in-memory LRU cache, then tries loading from disk, then falls back to `run()` + `save()`. |

```python
# One-off computation (no caching)
simulation.run()

# Cache-or-compute (preferred for production use)
simulation.ensure()
```

`ensure()` uses a module-level LRU cache (max 100 simulations) and saves output datasets as HDF5 files alongside the input dataset. On repeated calls, it returns cached results instantly. For baseline-vs-reform comparisons, `economic_impact_analysis()` calls `ensure()` internally, so you rarely need to call it yourself.

### Accessing calculated variables

After running a simulation, you can access the calculated variables from the output dataset:

```python
simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
)
simulation.run()

# Access specific variables
output = simulation.output_dataset.data
person_data = output.person[["person_id", "age", "employment_income", "income_tax"]]
household_data = output.household[["household_id", "household_net_income"]]
benunit_data = output.benunit[["benunit_id", "universal_credit", "child_benefit"]]
```

## Policies

Policies modify tax-benefit system parameters through parametric reforms.

### Reform as a dict

The canonical form — same shape ``pe.{uk,us}.calculate_household(reform=...)``
accepts — is a flat ``{parameter.path: value}`` / ``{parameter.path: {date: value}}``
dict. ``Simulation`` compiles it to a ``Policy`` at construction:

```python
import policyengine as pe
from policyengine.core import Simulation

baseline = Simulation(dataset=dataset, tax_benefit_model_version=pe.uk.model)
reform = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
    # Personal allowance raised from ~£12,570 to £15,000.
    policy={"gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000},
)
baseline.run()
reform.run()
```

Scalar values default their effective date to ``{dataset.year}-01-01``.
For time-varying reforms pass a nested ``{date: value}`` mapping:

```python
policy = {
    "gov.hmrc.income_tax.allowances.personal_allowance.amount": {
        "2026-01-01": 13_000,
        "2027-01-01": 15_000,
    }
}
```

Unknown paths raise ``ValueError`` with a close-match suggestion.

### Reform as a Policy object (escape hatch)

For reforms that can't be expressed as parameter-value changes (e.g.,
custom ``simulation_modifier`` callables), build a ``Policy`` directly:

```python
from policyengine.core import Parameter, ParameterValue, Policy
import datetime

policy = Policy(
    name="Increased personal allowance",
    parameter_values=[
        ParameterValue(
            parameter=Parameter(
                name="gov.hmrc.income_tax.allowances.personal_allowance.amount",
                tax_benefit_model_version=pe.uk.model,
                data_type=float,
            ),
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            value=15_000,
        ),
    ],
)

Simulation(dataset=dataset, tax_benefit_model_version=pe.uk.model, policy=policy)
```

### Combining policies

Policies can be combined using the `+` operator:

```python
combined = policy_a + policy_b
# Concatenates parameter_values and chains simulation_modifiers
```

### Simulation modifiers

For reforms that cannot be expressed as parameter value changes, `Policy` accepts a `simulation_modifier` callable that directly manipulates the underlying `policyengine_core` simulation:

```python
def my_modifier(sim):
    """Custom reform logic applied to the core simulation object."""
    p = sim.tax_benefit_system.parameters
    # Modify parameters programmatically
    return sim

policy = Policy(
    name="Custom reform",
    simulation_modifier=my_modifier,
)
```

Note: the UK model supports `simulation_modifier`. The US model currently only uses the `parameter_values` path.

## Dynamic behavioural responses

The `Dynamic` class is structurally identical to `Policy` and represents behavioural responses to policy changes (e.g., labour supply elasticities). It is applied after the policy in the simulation pipeline.

```python
from policyengine.core.dynamic import Dynamic

dynamic = Dynamic(
    name="Labour supply response",
    parameter_values=[...],  # Same format as Policy
)

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
    policy=policy,
    dynamic=dynamic,
)
```

Dynamic responses can also be combined using the `+` operator and support `simulation_modifier` callables.

## Outputs

Output classes provide structured analysis of simulation results.

### Aggregate

Calculate aggregate statistics (sum, mean, count) for any variable:

```python
from policyengine.outputs.aggregate import Aggregate, AggregateType

# Total universal credit spending
agg = Aggregate(
    simulation=simulation,
    variable="universal_credit",
    aggregate_type=AggregateType.SUM,
    entity="benunit",  # Map to benunit level
)
agg.run()
print(f"Total UC spending: £{agg.result / 1e9:.1f}bn")

# Mean household income in top decile
agg = Aggregate(
    simulation=simulation,
    variable="household_net_income",
    aggregate_type=AggregateType.MEAN,
    filter_variable="household_net_income",
    quantile=10,
    quantile_eq=10,  # 10th decile
)
agg.run()
print(f"Mean income in top decile: £{agg.result:,.0f}")
```

### ChangeAggregate

Analyse impacts of policy reforms:

```python
from policyengine.outputs.change_aggregate import ChangeAggregate, ChangeAggregateType

# Count winners and losers
winners = ChangeAggregate(
    baseline_simulation=baseline,
    reform_simulation=reform,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_geq=1,  # Gain at least £1
)
winners.run()
print(f"Winners: {winners.result / 1e6:.1f}m households")

losers = ChangeAggregate(
    baseline_simulation=baseline,
    reform_simulation=reform,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_leq=-1,  # Lose at least £1
)
losers.run()
print(f"Losers: {losers.result / 1e6:.1f}m households")

# Revenue impact
revenue = ChangeAggregate(
    baseline_simulation=baseline,
    reform_simulation=reform,
    variable="household_tax",
    aggregate_type=ChangeAggregateType.SUM,
)
revenue.run()
print(f"Revenue change: £{revenue.result / 1e9:.1f}bn")
```

## Entity mapping

The package automatically handles entity mapping when variables are defined at different entity levels.

### Entity hierarchy

**UK:**
```
household
    └── benunit (benefit unit)
            └── person
```

**US:**
```
household
    ├── tax_unit
    ├── spm_unit
    ├── family
    └── marital_unit
            └── person
```

### Automatic mapping

When you request a person-level variable (like `ssi`) at household level, the package:
1. Sums person-level values within each household (aggregation)
2. Returns household-level data with proper weights

```python
# SSI is defined at person level, but we want household-level totals
agg = Aggregate(
    simulation=simulation,
    variable="ssi",  # Person-level variable
    entity="household",  # Target household level
    aggregate_type=AggregateType.SUM,
)
# Internally maps person → household by summing SSI for all persons in each household
```

When you request a household-level variable at person level:
1. Replicates household values to all persons in that household (expansion)

### Direct entity mapping

You can also map data between entities directly using the `map_to_entity` method:

```python
# Map person income to household level (sum)
household_income = dataset.data.map_to_entity(
    source_entity="person",
    target_entity="household",
    columns=["employment_income"],
    how="sum"
)

# Map household rent to person level (project/broadcast)
person_rent = dataset.data.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["rent"],
    how="project"
)
```

#### Mapping with custom values

You can map custom value arrays instead of existing columns:

```python
# Map custom per-person values to household level
import numpy as np

# Create custom values (e.g., imputed data)
custom_values = np.array([100, 200, 150, 300])

household_totals = dataset.data.map_to_entity(
    source_entity="person",
    target_entity="household",
    values=custom_values,
    how="sum"
)
```

#### Aggregation methods

The `how` parameter controls how values are mapped:

**Person → Group (aggregation):**
- `how='sum'` (default): Sum values within each group
- `how='first'`: Take first person's value in each group

```python
# Sum person incomes to household level
household_income = data.map_to_entity(
    source_entity="person",
    target_entity="household",
    columns=["employment_income"],
    how="sum"
)

# Take first person's age as household reference
household_age = data.map_to_entity(
    source_entity="person",
    target_entity="household",
    columns=["age"],
    how="first"
)
```

**Group → Person (expansion):**
- `how='project'` (default): Broadcast group value to all members
- `how='divide'`: Split group value equally among members

```python
# Broadcast household rent to each person
person_rent = data.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["rent"],
    how="project"
)

# Split household savings equally per person
person_savings = data.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["total_savings"],
    how="divide"
)
```

**Group → Group (via person entity):**
- `how='sum'` (default): Sum through person entity
- `how='first'`: Take first source group's value
- `how='project'`: Broadcast first source group's value
- `how='divide'`: Split proportionally based on person counts

```python
# UK: Sum benunit benefits to household level
household_benefits = data.map_to_entity(
    source_entity="benunit",
    target_entity="household",
    columns=["universal_credit"],
    how="sum"
)

# US: Map tax unit income to household, splitting by members
household_from_tax = data.map_to_entity(
    source_entity="tax_unit",
    target_entity="household",
    columns=["taxable_income"],
    how="divide"
)
```

## Visualisation

The package includes utilities for creating PolicyEngine-branded visualisations:

```python
from policyengine.utils.plotting import format_fig, COLORS
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))

format_fig(
    fig,
    title="My chart",
    xaxis_title="X axis",
    yaxis_title="Y axis",
    height=600,
    width=800,
)
fig.show()
```

### Brand colours

```python
COLORS = {
    "primary": "#319795",        # Teal
    "success": "#22C55E",        # Green
    "warning": "#FEC601",        # Yellow
    "error": "#EF4444",          # Red
    "info": "#1890FF",           # Blue
    "blue_secondary": "#026AA2", # Dark blue
    "gray": "#667085",           # Gray
}
```

## Common workflows

### 1. Analyse employment income variation

See [UK employment income variation](examples.md#uk-employment-income-variation) for a complete example of:
- Creating custom datasets with varied parameters
- Running single simulations
- Extracting results with filters
- Visualising benefit phase-outs

### 2. Policy reform analysis

See [UK policy reform analysis](examples.md#uk-policy-reform-analysis) for:
- Applying parametric reforms
- Comparing baseline and reform
- Analysing winners/losers by decile
- Calculating revenue impacts

### 3. Distributional analysis

See [US income distribution](examples.md#us-income-distribution) for:
- Loading representative microdata
- Calculating statistics by income decile
- Mapping variables across entity levels
- Creating interactive visualisations

## Best practices

### Creating custom datasets

1. **Always set would_claim variables**: Benefits won't be claimed unless explicitly enabled
   ```python
   "would_claim_uc": [True] * n_households
   ```

2. **Set disability variables explicitly**: Prevents random UC spikes from LCWRA element
   ```python
   "is_disabled_for_benefits": [False] * n_people
   "uc_limited_capability_for_WRA": [False] * n_people
   ```

3. **Include required join keys**: Person data needs entity membership
   ```python
   "person_household_id": household_ids
   "person_benunit_id": benunit_ids  # UK only
   ```

4. **Set required household fields**: Vary by country
   ```python
   # UK
   "region": ["LONDON"] * n_households
   "tenure_type": ["RENT_PRIVATELY"] * n_households

   # US
   "state_code": ["CA"] * n_households
   ```

### Performance optimisation

1. **Single simulation for variations**: Create all scenarios in one dataset, run once
2. **Custom variable selection**: Only calculate needed variables
3. **Filter efficiently**: Use quantile filters for decile analysis
4. **Parallel analysis**: Multiple Aggregate calls can run independently

### Data integrity

1. **Check weights**: Ensure weights sum to expected population
2. **Validate join keys**: All persons should link to valid households
3. **Review output ranges**: Check calculated values are reasonable
4. **Test edge cases**: Zero income, high income, disabled, elderly

## Next steps

- [Economic impact analysis](economic-impact-analysis.md): Full baseline-vs-reform comparison workflow
- [Advanced outputs](advanced-outputs.md): DecileImpact, Poverty, Inequality, IntraDecileImpact
- [Regions and scoping](regions-and-scoping.md): Sub-national analysis (states, constituencies, districts)
- Country-specific documentation:
  - [UK tax-benefit model](country-models-uk.md)
  - [US tax-benefit model](country-models-us.md)
- [Visualisation](visualisation.md): Publication-ready charts
- [Examples](examples.md): Complete working scripts
