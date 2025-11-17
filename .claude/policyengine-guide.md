# PolicyEngine.py - Claude Guide

This guide helps you use the policyengine.py package to perform tax-benefit microsimulation analysis.

## Core workflow

1. **Create or load a dataset** with microdata (person, household, etc.)
2. **Run a simulation** applying tax-benefit rules to the dataset
3. **Extract results** using output classes (Aggregate, ChangeAggregate)
4. **Visualise** using built-in plotting utilities

## Package structure

```
policyengine
├── core/
│   ├── Dataset, YearData         # Data containers
│   ├── Simulation                # Runs tax-benefit calculations
│   ├── Policy, Parameter         # Define reforms
│   └── map_to_entity()          # Entity mapping utility
├── outputs/
│   ├── Aggregate                 # Calculate statistics
│   └── ChangeAggregate          # Analyse reforms
├── tax_benefit_models/
│   ├── uk/                      # UK-specific models
│   └── us/                      # US-specific models
└── utils/
    └── plotting                 # Visualisation tools
```

## Quick start patterns

### Pattern 1: Synthetic scenario analysis

Use when: User wants to analyse specific household scenarios

```python
import pandas as pd
from microdf import MicroDataFrame
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest
)
from policyengine.core import Simulation

# Create synthetic person data
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

# Create benunit data (UK only)
benunit_df = MicroDataFrame(
    pd.DataFrame({
        "benunit_id": [0, 1],
        "would_claim_uc": [True, True],
        "benunit_weight": [1.0, 1.0],
    }),
    weights="benunit_weight"
)

# Package into dataset
dataset = PolicyEngineUKDataset(
    name="Custom scenario",
    description="Analysis scenario",
    filepath="./custom.h5",
    year=2026,
    data=UKYearData(
        person=person_df,
        household=household_df,
        benunit=benunit_df,
    )
)

# Run simulation
simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
simulation.run()

# Access results
output = simulation.output_dataset.data
print(output.household[["household_id", "household_net_income"]])
```

### Pattern 2: US synthetic scenario

```python
from policyengine.tax_benefit_models.us import (
    PolicyEngineUSDataset,
    USYearData,
    us_latest
)

# Create person data (note: US has more entity types)
person_df = MicroDataFrame(
    pd.DataFrame({
        "person_id": [0, 1, 2, 3],
        "person_household_id": [0, 0, 0, 0],
        "person_tax_unit_id": [0, 0, 0, 0],
        "person_spm_unit_id": [0, 0, 0, 0],
        "person_family_id": [0, 0, 0, 0],
        "person_marital_unit_id": [0, 0, 1, 2],
        "age": [35, 33, 8, 5],
        "employment_income": [60000, 40000, 0, 0],
        "person_weight": [1.0, 1.0, 1.0, 1.0],
    }),
    weights="person_weight"
)

# Create entity dataframes (tax_unit, spm_unit, family, marital_unit, household)
# ... (see examples/employment_income_variation_us.py for full pattern)

dataset = PolicyEngineUSDataset(
    name="US scenario",
    year=2024,
    filepath="./us_scenario.h5",
    data=USYearData(
        person=person_df,
        tax_unit=tax_unit_df,
        spm_unit=spm_unit_df,
        family=family_df,
        marital_unit=marital_unit_df,
        household=household_df,
    )
)
```

### Pattern 3: Parameter sweep analysis

Use when: User wants to vary one parameter across many values

```python
import numpy as np

# Create N scenarios with varying parameter
n_scenarios = 43
income_values = np.linspace(0, 100000, n_scenarios)

# Create person data with all scenarios
person_df = MicroDataFrame(
    pd.DataFrame({
        "person_id": range(n_scenarios),
        "person_household_id": range(n_scenarios),
        "person_benunit_id": range(n_scenarios),
        "age": [35] * n_scenarios,
        "employment_income": income_values,
        "person_weight": [1.0] * n_scenarios,
    }),
    weights="person_weight"
)

# Create matching household/benunit data
household_df = MicroDataFrame(
    pd.DataFrame({
        "household_id": range(n_scenarios),
        "region": ["LONDON"] * n_scenarios,
        "rent": [15000] * n_scenarios,
        "household_weight": [1.0] * n_scenarios,
    }),
    weights="household_weight"
)

# ... create dataset and run simulation once for all scenarios
```

### Pattern 4: Policy reform analysis

Use when: User wants to compare baseline vs reform

```python
from policyengine.core import Policy, Parameter, ParameterValue
import datetime

# Define reform
parameter = Parameter(
    name="gov.hmrc.income_tax.allowances.personal_allowance.amount",
    tax_benefit_model_version=uk_latest,
    description="Personal allowance",
    data_type=float,
)

policy = Policy(
    name="Increase personal allowance",
    description="Raises PA to £15,000",
    parameter_values=[
        ParameterValue(
            parameter=parameter,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            value=15000,
        )
    ],
)

# Run baseline
baseline_sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
baseline_sim.run()

# Run reform
reform_sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
    policy=policy,
)
reform_sim.run()

# Analyse impact
from policyengine.outputs.change_aggregate import (
    ChangeAggregate,
    ChangeAggregateType
)

winners = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_geq=1,  # Gain at least £1
)
winners.run()
print(f"Winners: {winners.result:,.0f}")
```

### Pattern 5: Extract aggregates

Use when: User wants statistics from simulation results

```python
from policyengine.outputs.aggregate import Aggregate, AggregateType

# Total spending on a benefit
total_uc = Aggregate(
    simulation=simulation,
    variable="universal_credit",
    entity="benunit",
    aggregate_type=AggregateType.SUM,
)
total_uc.run()
print(f"Total UC: £{total_uc.result / 1e9:.1f}bn")

# Mean income in top decile
top_decile_income = Aggregate(
    simulation=simulation,
    variable="household_net_income",
    entity="household",
    aggregate_type=AggregateType.MEAN,
    filter_variable="household_net_income",
    quantile=10,
    quantile_eq=10,  # 10th decile only
)
top_decile_income.run()
print(f"Top decile mean income: £{top_decile_income.result:,.0f}")

# Count households below poverty line
poverty_count = Aggregate(
    simulation=simulation,
    variable="household_id",
    entity="household",
    aggregate_type=AggregateType.COUNT,
    filter_variable="in_absolute_poverty_bhc",
    filter_eq=True,
)
poverty_count.run()
print(f"Households in poverty: {poverty_count.result:,.0f}")
```

### Pattern 6: Entity mapping

Use when: User needs to map data between entity levels

```python
# Map person income to household level (sum)
household_income = dataset.data.map_to_entity(
    source_entity="person",
    target_entity="household",
    columns=["employment_income"],
    how="sum"
)

# Map household rent to person level (broadcast)
person_rent = dataset.data.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["rent"],
    how="project"
)

# Split household savings equally per person
person_savings_share = dataset.data.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["total_savings"],
    how="divide"
)

# Map custom values
import numpy as np
custom_values = np.array([100, 200, 150])
household_totals = dataset.data.map_to_entity(
    source_entity="person",
    target_entity="household",
    values=custom_values,
    how="sum"
)
```

### Pattern 7: Visualisation

```python
from policyengine.utils.plotting import format_fig, COLORS
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=income_values,
    y=net_income_values,
    mode='lines',
    name='Net income',
    line=dict(color=COLORS["primary"], width=3)
))

format_fig(
    fig,
    title="Net income by employment income",
    xaxis_title="Employment income (£)",
    yaxis_title="Net income (£)",
    height=600,
    width=1000,
)
fig.show()
```

## Entity structures

### UK entities
```
household
    └── benunit (benefit unit - family claiming benefits together)
            └── person
```

### US entities
```
household
    ├── tax_unit (federal tax filing unit)
    ├── spm_unit (Supplemental Poverty Measure unit)
    ├── family (Census definition)
    └── marital_unit (married couple or single)
            └── person
```

## Key concepts

### 1. MicroDataFrame
All entity data uses `MicroDataFrame` which automatically handles survey weights:
```python
df = MicroDataFrame(pd_dataframe, weights="weight_column_name")
df.sum()  # Automatically weighted
```

### 2. Entity mapping
When variables are at different entity levels, automatic mapping occurs:
- **Person → Group**: Sum values within each group
- **Group → Person**: Replicate group value to all members

### 3. Required fields

**UK person:**
- `person_id`, `person_household_id`, `person_benunit_id`
- `age`, `employment_income`
- `person_weight`

**UK household:**
- `household_id`
- `region` (e.g., "LONDON", "SOUTH_EAST")
- `rent` (annual)
- `household_weight`

**UK benunit:**
- `benunit_id`
- `would_claim_uc` (boolean - CRITICAL for UC calculations)
- `benunit_weight`

**US person:**
- `person_id`, `person_household_id`, `person_tax_unit_id`, `person_spm_unit_id`, `person_family_id`, `person_marital_unit_id`
- `age`, `employment_income`
- `person_weight`

**US household:**
- `household_id`
- `state_code` (e.g., "CA", "NY")
- `household_weight`

### 4. Common pitfalls

**Always set would_claim variables:**
```python
"would_claim_uc": [True] * n_benunits  # UK
```

**Set disability variables to avoid spikes:**
```python
"is_disabled_for_benefits": [False] * n_people
"uc_limited_capability_for_WRA": [False] * n_people
```

**Use consistent ID linkages:**
```python
# Person 0 must link to valid household_id and benunit_id
person_df["person_household_id"] = [0, 0, 1]  # Persons 0,1 in household 0
```

## Finding parameters

### UK common parameters
```
gov.hmrc.income_tax.allowances.personal_allowance.amount
gov.hmrc.national_insurance.class_1.rates.main
gov.dwp.universal_credit.means_test.reduction_rate
gov.dwp.universal_credit.elements.child.first_child
gov.dwp.child_benefit.amount.first_child
```

### US common parameters
```
gov.irs.income.standard_deduction.single
gov.irs.income.standard_deduction.joint
gov.irs.credits.ctc.amount.base
gov.irs.credits.ctc.refundable.amount.max
gov.irs.credits.eitc.max[0]  # 0 children
gov.usda.snap.normal_allotment.max[1]  # 1 person
```

## Aggregation methods for entity mapping

- `how='sum'`: Aggregate by summing (person → group default)
- `how='first'`: Take first value in group
- `how='project'`: Broadcast group value to members (group → person default)
- `how='divide'`: Split equally among members

## Response patterns

When user asks to:

1. **"Analyse a family with £X income"** → Use Pattern 1 (synthetic scenario)
2. **"How does income vary from £0 to £100k"** → Use Pattern 3 (parameter sweep)
3. **"What if we increased personal allowance?"** → Use Pattern 4 (policy reform)
4. **"How many people benefit?"** → Use Pattern 5 (extract aggregates)
5. **"Compare US vs UK"** → Create both datasets, run separately
6. **"Show me the phase-out"** → Use Pattern 3 + Pattern 7 (sweep + visualise)

## Debugging tips

1. **Check dataset shape**: `len(dataset.data.person)` should match expectations
2. **Verify linkages**: All person IDs should map to valid household IDs
3. **Check weights**: `dataset.data.household["household_weight"].sum()`
4. **Inspect output columns**: `list(simulation.output_dataset.data.person.columns)`
5. **Test small first**: Use 3-5 scenarios before scaling to 100+

## Example responses

**User: "What's the net income of a single person earning £30k in London?"**

```python
# I'll create a synthetic dataset with one person earning £30k in London
# and run a UK simulation to calculate their net income.

import pandas as pd
from microdf import MicroDataFrame
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset, UKYearData, uk_latest
)
from policyengine.core import Simulation

# Create person data
person_df = MicroDataFrame(
    pd.DataFrame({
        "person_id": [0],
        "person_household_id": [0],
        "person_benunit_id": [0],
        "age": [30],
        "employment_income": [30000],
        "person_weight": [1.0],
    }),
    weights="person_weight"
)

# Create household data
household_df = MicroDataFrame(
    pd.DataFrame({
        "household_id": [0],
        "region": ["LONDON"],
        "rent": [12000],  # Typical London rent
        "household_weight": [1.0],
    }),
    weights="household_weight"
)

# Create benunit data
benunit_df = MicroDataFrame(
    pd.DataFrame({
        "benunit_id": [0],
        "would_claim_uc": [True],
        "benunit_weight": [1.0],
    }),
    weights="benunit_weight"
)

# Create and run simulation
dataset = PolicyEngineUKDataset(
    name="Single person £30k",
    filepath="./temp_scenario.h5",
    year=2026,
    data=UKYearData(
        person=person_df,
        household=household_df,
        benunit=benunit_df,
    )
)

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
simulation.run()

# Extract results
output = simulation.output_dataset.data
net_income = output.household["household_net_income"].iloc[0]
income_tax = output.person["income_tax"].iloc[0]
ni = output.person["national_insurance"].iloc[0]

print(f"Employment income: £30,000")
print(f"Income tax: £{income_tax:,.0f}")
print(f"National Insurance: £{ni:,.0f}")
print(f"Net income: £{net_income:,.0f}")
```

## Additional resources

- Full examples in `examples/` directory
- Core concepts: `docs/core-concepts.md`
- UK model: `docs/country-models-uk.md`
- US model: `docs/country-models-us.md`
