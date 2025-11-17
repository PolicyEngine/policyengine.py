# PolicyEngine.py Quick Reference

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

## Minimal working example (US)

```python
import pandas as pd
from microdf import MicroDataFrame
from policyengine.tax_benefit_models.us import (
    PolicyEngineUSDataset, USYearData, us_latest
)
from policyengine.core import Simulation

# Person data (US requires more entity links)
person_df = MicroDataFrame(pd.DataFrame({
    "person_id": [0, 1],
    "person_household_id": [0, 0],
    "person_tax_unit_id": [0, 0],
    "person_spm_unit_id": [0, 0],
    "person_family_id": [0, 0],
    "person_marital_unit_id": [0, 0],
    "age": [35, 33],
    "employment_income": [60000, 40000],
    "person_weight": [1.0, 1.0],
}), weights="person_weight")

# Create minimal entity dataframes
entities = {}
for entity in ["tax_unit", "spm_unit", "family", "marital_unit"]:
    entities[entity] = MicroDataFrame(pd.DataFrame({
        f"{entity}_id": [0],
        f"{entity}_weight": [1.0],
    }), weights=f"{entity}_weight")

household_df = MicroDataFrame(pd.DataFrame({
    "household_id": [0],
    "state_code": ["CA"],
    "household_weight": [1.0],
}), weights="household_weight")

# Create dataset
dataset = PolicyEngineUSDataset(
    name="Example",
    filepath="./temp.h5",
    year=2024,
    data=USYearData(
        person=person_df,
        tax_unit=entities["tax_unit"],
        spm_unit=entities["spm_unit"],
        family=entities["family"],
        marital_unit=entities["marital_unit"],
        household=household_df,
    )
)

# Run simulation
sim = Simulation(dataset=dataset, tax_benefit_model_version=us_latest)
sim.run()

# Get results
print(sim.output_dataset.data.household[["household_net_income"]])
```

## Common patterns

### Parameter sweep (vary one input)
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

### Policy reform
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

### Extract aggregate statistics
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
    filter_geq=65,  # Age >= 65
)
count.run()
```

### Compare baseline vs reform
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

### Entity mapping
```python
# Sum person income to household
household_income = dataset.data.map_to_entity(
    source_entity="person",
    target_entity="household",
    columns=["employment_income"],
    how="sum"
)

# Broadcast household rent to persons
person_rent = dataset.data.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["rent"],
    how="project"
)

# Divide household value equally per person
per_person = dataset.data.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["total_savings"],
    how="divide"
)

# Map custom values
custom_totals = dataset.data.map_to_entity(
    source_entity="person",
    target_entity="household",
    values=custom_array,
    how="sum"
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

## Common UK regions
```python
["LONDON", "SOUTH_EAST", "SOUTH_WEST", "EAST_OF_ENGLAND",
 "WEST_MIDLANDS", "EAST_MIDLANDS", "YORKSHIRE",
 "NORTH_WEST", "NORTH_EAST", "WALES", "SCOTLAND", "NORTHERN_IRELAND"]
```

## Common US state codes
```python
["CA", "NY", "TX", "FL", "PA", "IL", "OH", "GA", "NC", "MI", ...]
```

## Aggregate filter options
```python
# Exact match
filter_eq=value

# Greater than/equal
filter_geq=value

# Less than/equal
filter_leq=value

# Quantile filtering (deciles)
quantile=10          # Split into 10 groups
quantile_eq=1        # First decile only
quantile_geq=9       # Top two deciles
quantile_leq=2       # Bottom two deciles
```

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

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No UC calculated | Set `would_claim_uc=True` |
| Random UC spikes | Set `is_disabled_for_benefits=False`, `uc_limited_capability_for_WRA=False` |
| KeyError on column | Check variable name in docs, may be different entity level |
| Empty results | Check weights sum correctly, verify ID linkages |
| Slow performance | Use parameter sweep pattern (one simulation for N scenarios) |

## Visualisation template
```python
from policyengine.utils.plotting import format_fig, COLORS
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(x=x_vals, y=y_vals, line=dict(color=COLORS["primary"])))
format_fig(fig, title="Title", xaxis_title="X", yaxis_title="Y")
fig.show()
```
