# Core concepts

PolicyEngine.py is a Python package for tax-benefit microsimulation analysis. It provides a unified interface for running policy simulations, analysing distributional impacts, and visualising results across different countries.

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

```python
from policyengine.tax_benefit_models.uk import uk_latest
from policyengine.tax_benefit_models.us import us_latest

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
from policyengine.tax_benefit_models.uk import PolicyEngineUKDataset

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

## Simulations

Simulations apply tax-benefit models to datasets, calculating all variables for the specified year.

### Running a simulation

```python
from policyengine.core import Simulation
from policyengine.tax_benefit_models.uk import uk_latest

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
simulation.run()

# Access output data
output_person = simulation.output_dataset.data.person
output_household = simulation.output_dataset.data.household

# Check calculated variables
print(output_household[["household_id", "household_net_income", "household_tax"]])
```

### Accessing calculated variables

After running a simulation, you can access the calculated variables from the output dataset:

```python
simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
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

### Creating a policy

```python
from policyengine.core import Policy, Parameter, ParameterValue
import datetime

# Define parameter to modify
parameter = Parameter(
    name="gov.hmrc.income_tax.allowances.personal_allowance.amount",
    tax_benefit_model_version=uk_latest,
    description="Personal allowance for income tax",
    data_type=float,
)

# Set new value
parameter_value = ParameterValue(
    parameter=parameter,
    start_date=datetime.date(2026, 1, 1),
    end_date=datetime.date(2026, 12, 31),
    value=15000,  # Increase from ~£12,570 to £15,000
)

policy = Policy(
    name="Increased personal allowance",
    description="Raises personal allowance to £15,000",
    parameter_values=[parameter_value],
)
```

### Running a reform simulation

```python
# Baseline simulation
baseline = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
baseline.run()

# Reform simulation
reform = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
    policy=policy,
)
reform.run()
```

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

See `examples/employment_income_variation_uk.py` for a complete example of:
- Creating custom datasets with varied parameters
- Running single simulations
- Extracting results with filters
- Visualising benefit phase-outs

### 2. Policy reform analysis

See `examples/policy_change_uk.py` for:
- Applying parametric reforms
- Comparing baseline and reform
- Analysing winners/losers by decile
- Calculating revenue impacts

### 3. Distributional analysis

See `examples/income_distribution_us.py` for:
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

- See `examples/` for complete working examples
- Review country-specific documentation:
  - [UK tax-benefit model](country-models-uk.md)
  - [US tax-benefit model](country-models-us.md)
- Explore the API reference for detailed class documentation
