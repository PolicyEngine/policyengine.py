---
name: policyengine
description: Guide for using policyengine.py to perform tax-benefit microsimulation analysis. Use when working with simulations, datasets, policy reforms, or aggregations.
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# PolicyEngine.py Guide

This skill helps you use the policyengine.py package for tax-benefit microsimulation analysis.

## Quick reference

For full documentation, see the supporting files in this directory:
- [quick-reference.md](quick-reference.md) - Syntax cheat sheet and imports
- [working-with-simulations.md](working-with-simulations.md) - Deep dive on simulations, caching, and entity mapping

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
│   │   ├── .run()                # Execute simulation
│   │   ├── .ensure()             # Run if needed (cached)
│   │   ├── .save()               # Save to disk
│   │   └── .load()               # Load from disk
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

## Imports cheat sheet

```python
# Core
from policyengine.core import Simulation, Policy, Parameter, ParameterValue

# UK
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest
)

# US
from policyengine.tax_benefit_models.us import (
    PolicyEngineUSDataset,
    USYearData,
    us_latest
)

# Outputs
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.outputs.change_aggregate import ChangeAggregate, ChangeAggregateType

# Utilities
from policyengine.utils.plotting import format_fig, COLORS
from microdf import MicroDataFrame
import pandas as pd
import numpy as np
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

## Minimal working example (UK)

```python
import pandas as pd
from microdf import MicroDataFrame
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset, UKYearData, uk_latest
)
from policyengine.core import Simulation

# Person data
person_df = MicroDataFrame(pd.DataFrame({
    "person_id": [0],
    "person_household_id": [0],
    "person_benunit_id": [0],
    "age": [30],
    "employment_income": [30000],
    "person_weight": [1.0],
}), weights="person_weight")

# Household data
household_df = MicroDataFrame(pd.DataFrame({
    "household_id": [0],
    "region": ["LONDON"],
    "rent": [12000],
    "household_weight": [1.0],
}), weights="household_weight")

# Benunit data
benunit_df = MicroDataFrame(pd.DataFrame({
    "benunit_id": [0],
    "would_claim_uc": [True],
    "benunit_weight": [1.0],
}), weights="benunit_weight")

# Create dataset
dataset = PolicyEngineUKDataset(
    name="Example",
    filepath="./temp.h5",
    year=2026,
    data=UKYearData(person=person_df, household=household_df, benunit=benunit_df)
)

# Run simulation
sim = Simulation(dataset=dataset, tax_benefit_model_version=uk_latest)
sim.run()

# Get results
output = sim.output_dataset.data
print(output.household[["household_net_income"]])
```

## Common patterns

### Pattern 1: Parameter sweep (vary one input)

```python
n = 50
incomes = np.linspace(0, 100000, n)

person_df = MicroDataFrame(pd.DataFrame({
    "person_id": range(n),
    "person_household_id": range(n),
    "person_benunit_id": range(n),
    "age": [30] * n,
    "employment_income": incomes,
    "person_weight": [1.0] * n,
}), weights="person_weight")

# Create matching household/benunit data with n rows
# ... then run simulation once for all scenarios
```

### Pattern 2: Policy reform

```python
import datetime
from policyengine.core import Policy, Parameter, ParameterValue

parameter = Parameter(
    name="gov.hmrc.income_tax.allowances.personal_allowance.amount",
    tax_benefit_model_version=uk_latest,
    description="Personal allowance",
    data_type=float,
)

policy = Policy(
    name="Reform",
    description="Change PA",
    parameter_values=[ParameterValue(
        parameter=parameter,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 31),
        value=15000,
    )]
)

# Run with policy
reform_sim = Simulation(dataset=dataset, tax_benefit_model_version=uk_latest, policy=policy)
```

### Pattern 3: Extract aggregate statistics

```python
from policyengine.outputs.aggregate import Aggregate, AggregateType

# Sum
total = Aggregate(
    simulation=sim,
    variable="universal_credit",
    entity="benunit",
    aggregate_type=AggregateType.SUM,
)
total.run()

# Mean
avg = Aggregate(
    simulation=sim,
    variable="household_net_income",
    entity="household",
    aggregate_type=AggregateType.MEAN,
)
avg.run()

# Count with filter
count = Aggregate(
    simulation=sim,
    variable="person_id",
    entity="person",
    aggregate_type=AggregateType.COUNT,
    filter_variable="age",
    filter_geq=65,
)
count.run()
```

### Pattern 4: Compare baseline vs reform

```python
from policyengine.outputs.change_aggregate import ChangeAggregate, ChangeAggregateType

winners = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="household_net_income",
    aggregate_type=ChangeAggregateType.COUNT,
    change_geq=1,
)
winners.run()

revenue = ChangeAggregate(
    baseline_simulation=baseline_sim,
    reform_simulation=reform_sim,
    variable="household_tax",
    aggregate_type=ChangeAggregateType.SUM,
)
revenue.run()
```

### Pattern 5: Entity mapping

```python
# Sum person income to household
household_income = output.map_to_entity(
    source_entity="person",
    target_entity="household",
    columns=["employment_income"],
    how="sum"
)

# Broadcast household rent to persons
person_rent = output.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["rent"],
    how="project"
)

# Divide household value equally per person
per_person = output.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["total_savings"],
    how="divide"
)
```

## Critical fields

### UK
- **Person**: `person_id`, `person_household_id`, `person_benunit_id`, `age`, `employment_income`, `person_weight`
- **Household**: `household_id`, `region`, `rent`, `household_weight`
- **Benunit**: `benunit_id`, `would_claim_uc`, `benunit_weight`

### US
- **Person**: `person_id`, `person_household_id`, `person_tax_unit_id`, `person_spm_unit_id`, `person_family_id`, `person_marital_unit_id`, `age`, `employment_income`, `person_weight`
- **Household**: `household_id`, `state_code`, `household_weight`
- **Other entities**: Each needs `{entity}_id` and `{entity}_weight`

## Common pitfalls

- **Always set would_claim variables**: `"would_claim_uc": [True] * n_benunits` (UK)
- **Set disability variables to avoid spikes**: `"is_disabled_for_benefits": [False]`, `"uc_limited_capability_for_WRA": [False]`
- **Use consistent ID linkages**: Person IDs must map to valid household/benunit IDs
- **Use `sim.ensure()` for caching**: Avoids redundant simulation runs

## Common parameters

### UK
```
gov.hmrc.income_tax.allowances.personal_allowance.amount
gov.hmrc.income_tax.rates.uk[0]  # Basic rate
gov.hmrc.national_insurance.class_1.rates.main
gov.dwp.universal_credit.means_test.reduction_rate
gov.dwp.universal_credit.elements.child.first_child
gov.dwp.child_benefit.amount.first_child
```

### US
```
gov.irs.income.standard_deduction.single
gov.irs.income.standard_deduction.joint
gov.irs.credits.ctc.amount.base
gov.irs.credits.eitc.max[0]
gov.ssa.payroll.rate.employee
gov.usda.snap.normal_allotment.max[1]
```

## MicroDataFrame

A pandas DataFrame that automatically handles weights for survey microdata:

```python
df = MicroDataFrame(pd_dataframe, weights="weight_column_name")
df.sum()   # Automatically weighted
df.mean()  # Automatically weighted
```

## Visualisation template

```python
from policyengine.utils.plotting import format_fig, COLORS
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(x=x_vals, y=y_vals, line=dict(color=COLORS["primary"])))
format_fig(fig, title="Title", xaxis_title="X", yaxis_title="Y")
fig.show()
```

## Response patterns

When user asks to:

1. **"Analyse a family with £X income"** → Use synthetic scenario pattern
2. **"How does income vary from £0 to £100k"** → Use parameter sweep pattern
3. **"What if we increased personal allowance?"** → Use policy reform pattern
4. **"How many people benefit?"** → Use aggregate extraction pattern
5. **"Compare US vs UK"** → Create both datasets, run separately
6. **"Show me the phase-out"** → Use sweep + visualisation patterns
