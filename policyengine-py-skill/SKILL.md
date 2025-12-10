---
name: policyengine-py
description: Tax-benefit microsimulation framework for creating datasets, running simulations, and analysing policy reforms
---

# PolicyEngine.py

PolicyEngine.py is a Python package for tax-benefit microsimulation analysis. It enables creating synthetic datasets, running simulations with UK/US tax-benefit models, and analysing policy reforms with distributional impacts.

## For Users 👥

### What is PolicyEngine.py?

PolicyEngine.py powers detailed tax-benefit analysis you see in PolicyEngine research:
- Income calculations for specific household scenarios
- Parameter sweep analysis showing how benefits phase out with income
- Policy reform impact analysis (winners, losers, revenue effects)
- Distributional analysis across income deciles

### Key Capabilities

**Scenario analysis:**
- Create synthetic households with specific characteristics
- Calculate net income, benefits, taxes for these households
- Vary parameters systematically (e.g. income from £0 to £100k)

**Policy reform analysis:**
- Define policy changes (e.g. increase personal allowance to £15,000)
- Compare baseline vs reform
- Calculate number of winners/losers
- Estimate revenue impact

**Distributional analysis:**
- Calculate statistics by income decile
- Analyse poverty impacts
- Generate weighted population estimates

## For Analysts 📊

### Installation

```bash
pip install policyengine
```

### Core Workflow

1. Create or load dataset with microdata
2. Run simulation applying tax-benefit rules
3. Extract results using output classes
4. Visualise using plotting utilities

### Pattern 1: Basic UK Scenario

```python
import pandas as pd
from microdf import MicroDataFrame
from policyengine.tax_benefit_models.uk import (
    PolicyEngineUKDataset,
    UKYearData,
    uk_latest
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
        "rent": [12000],
        "household_weight": [1.0],
    }),
    weights="household_weight"
)

# Create benunit data (UK only)
benunit_df = MicroDataFrame(
    pd.DataFrame({
        "benunit_id": [0],
        "would_claim_uc": [True],
        "benunit_weight": [1.0],
    }),
    weights="benunit_weight"
)

# Package into dataset
dataset = PolicyEngineUKDataset(
    name="Single person scenario",
    filepath="./temp.h5",
    year=2026,
    data=UKYearData(
        person=person_df,
        household=household_df,
        benunit=benunit_df,
    )
)

# Run simulation
sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
sim.run()

# Get results
output = sim.output_dataset.data
net_income = output.household["household_net_income"].iloc[0]
print(f"Net income: £{net_income:,.0f}")
```

### Pattern 2: Parameter Sweep

Analyse how outcomes vary across a parameter range:

```python
import numpy as np

# Create 50 scenarios with varying income
n = 50
incomes = np.linspace(0, 100000, n)

person_df = MicroDataFrame(
    pd.DataFrame({
        "person_id": range(n),
        "person_household_id": range(n),
        "person_benunit_id": range(n),
        "age": [30] * n,
        "employment_income": incomes,
        "person_weight": [1.0] * n,
    }),
    weights="person_weight"
)

# Create matching household/benunit data (n rows each)
household_df = MicroDataFrame(
    pd.DataFrame({
        "household_id": range(n),
        "region": ["LONDON"] * n,
        "rent": [12000] * n,
        "household_weight": [1.0] * n,
    }),
    weights="household_weight"
)

benunit_df = MicroDataFrame(
    pd.DataFrame({
        "benunit_id": range(n),
        "would_claim_uc": [True] * n,
        "benunit_weight": [1.0] * n,
    }),
    weights="benunit_weight"
)

# Create dataset and run simulation once for all scenarios
dataset = PolicyEngineUKDataset(
    name="Income sweep",
    filepath="./sweep.h5",
    year=2026,
    data=UKYearData(person=person_df, household=household_df, benunit=benunit_df)
)

sim = Simulation(dataset=dataset, tax_benefit_model_version=uk_latest)
sim.run()

# Extract results
output = sim.output_dataset.data
net_incomes = output.household["household_net_income"].values

# Plot
from policyengine.utils.plotting import format_fig, COLORS
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=incomes,
    y=net_incomes,
    line=dict(color=COLORS["primary"], width=3)
))
format_fig(fig, title="Net income by employment income",
           xaxis_title="Employment income (£)",
           yaxis_title="Net income (£)")
fig.show()
```

### Pattern 3: Policy Reform Analysis

```python
import datetime
from policyengine.core import Policy, Parameter, ParameterValue

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

### Pattern 4: Extract Aggregates

```python
from policyengine.outputs.aggregate import Aggregate, AggregateType

# Total benefit spending
total_uc = Aggregate(
    simulation=sim,
    variable="universal_credit",
    entity="benunit",
    aggregate_type=AggregateType.SUM,
)
total_uc.run()
print(f"Total UC: £{total_uc.result / 1e9:.1f}bn")

# Mean income in top decile
top_decile = Aggregate(
    simulation=sim,
    variable="household_net_income",
    entity="household",
    aggregate_type=AggregateType.MEAN,
    filter_variable="household_net_income",
    quantile=10,
    quantile_eq=10,
)
top_decile.run()
print(f"Top decile mean: £{top_decile.result:,.0f}")

# Count in poverty
poverty_count = Aggregate(
    simulation=sim,
    variable="household_id",
    entity="household",
    aggregate_type=AggregateType.COUNT,
    filter_variable="in_absolute_poverty_bhc",
    filter_eq=True,
)
poverty_count.run()
print(f"In poverty: {poverty_count.result:,.0f}")
```

### Pattern 5: US Scenario

```python
from policyengine.tax_benefit_models.us import (
    PolicyEngineUSDataset,
    USYearData,
    us_latest
)

# US requires more entity types
person_df = MicroDataFrame(
    pd.DataFrame({
        "person_id": [0, 1],
        "person_household_id": [0, 0],
        "person_tax_unit_id": [0, 0],
        "person_spm_unit_id": [0, 0],
        "person_family_id": [0, 0],
        "person_marital_unit_id": [0, 0],
        "age": [35, 33],
        "employment_income": [60000, 40000],
        "person_weight": [1.0, 1.0],
    }),
    weights="person_weight"
)

# Create minimal entity dataframes
entities = {}
for entity in ["tax_unit", "spm_unit", "family", "marital_unit"]:
    entities[entity] = MicroDataFrame(
        pd.DataFrame({
            f"{entity}_id": [0],
            f"{entity}_weight": [1.0],
        }),
        weights=f"{entity}_weight"
    )

household_df = MicroDataFrame(
    pd.DataFrame({
        "household_id": [0],
        "state_code": ["CA"],
        "household_weight": [1.0],
    }),
    weights="household_weight"
)

dataset = PolicyEngineUSDataset(
    name="US scenario",
    filepath="./us_temp.h5",
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

sim = Simulation(dataset=dataset, tax_benefit_model_version=us_latest)
sim.run()
```

### Pattern 6: Entity Mapping

Map data between entity levels (person ↔ household ↔ benunit):

```python
# Sum person income to household level
household_income = dataset.data.map_to_entity(
    source_entity="person",
    target_entity="household",
    columns=["employment_income"],
    how="sum"
)

# Broadcast household rent to person level
person_rent = dataset.data.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["rent"],
    how="project"
)

# Divide household value equally per person
per_person_share = dataset.data.map_to_entity(
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

## For Contributors 💻

### Repository

**Location:** PolicyEngine/policyengine.py

**Clone:**
```bash
git clone https://github.com/PolicyEngine/policyengine.py
cd policyengine.py
```

### Package Structure

```
policyengine/
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

### Entity Structures

**UK entities:**
```
household
    └── benunit (benefit unit - family claiming benefits together)
            └── person
```

**US entities:**
```
household
    ├── tax_unit (federal tax filing unit)
    ├── spm_unit (Supplemental Poverty Measure unit)
    ├── family (Census definition)
    └── marital_unit (married couple or single)
            └── person
```

### Required Fields

**UK person:**
- `person_id`, `person_household_id`, `person_benunit_id`
- `age`, `employment_income`
- `person_weight`

**UK household:**
- `household_id`
- `region` (e.g. "LONDON", "SOUTH_EAST")
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
- `state_code` (e.g. "CA", "NY")
- `household_weight`

### Key Concepts

**1. MicroDataFrame:**
All entity data uses `MicroDataFrame` which automatically handles survey weights:
```python
df = MicroDataFrame(pd_dataframe, weights="weight_column_name")
df.sum()  # Automatically weighted
```

**2. Entity mapping:**
When variables are at different entity levels, automatic mapping occurs:
- **Person → Group:** Sum values within each group
- **Group → Person:** Replicate group value to all members

**3. Aggregation methods:**
- `how='sum'`: Aggregate by summing (person → group default)
- `how='first'`: Take first value in group
- `how='project'`: Broadcast group value to members (group → person default)
- `how='divide'`: Split equally amongst members

### Common Parameters

**UK:**
```
gov.hmrc.income_tax.allowances.personal_allowance.amount
gov.hmrc.income_tax.rates.uk[0]  # Basic rate
gov.hmrc.national_insurance.class_1.rates.main
gov.dwp.universal_credit.means_test.reduction_rate
gov.dwp.universal_credit.elements.child.first_child
gov.dwp.child_benefit.amount.first_child
```

**US:**
```
gov.irs.income.standard_deduction.single
gov.irs.income.standard_deduction.joint
gov.irs.credits.ctc.amount.base
gov.irs.credits.eitc.max[0]
gov.ssa.payroll.rate.employee
gov.usda.snap.normal_allotment.max[1]
```

### Common Pitfalls

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

### Debugging Tips

1. Check dataset shape: `len(dataset.data.person)` should match expectations
2. Verify linkages: All person IDs should map to valid household IDs
3. Check weights: `dataset.data.household["household_weight"].sum()`
4. Inspect output columns: `list(simulation.output_dataset.data.person.columns)`
5. Test small first: Use 3-5 scenarios before scaling to 100+

### Testing

```bash
# Run tests
make test

# Or
pytest tests/ -v
```

### Contributing

Follow policyengine-standards-skill and policyengine-code-style-skill.

## Advanced Patterns

### Aggregate Filter Options

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

### Visualisation Template

```python
from policyengine.utils.plotting import format_fig, COLORS
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=x_vals,
    y=y_vals,
    line=dict(color=COLORS["primary"], width=3)
))
format_fig(
    fig,
    title="Title",
    xaxis_title="X axis",
    yaxis_title="Y axis",
    height=600,
    width=1000,
)
fig.show()
```

## Response Patterns

When user asks to:

1. **"Analyse a family with £X income"** → Use Pattern 1 (basic scenario)
2. **"How does income vary from £0 to £100k"** → Use Pattern 2 (parameter sweep)
3. **"What if we increased personal allowance?"** → Use Pattern 3 (policy reform)
4. **"How many people benefit?"** → Use Pattern 4 (extract aggregates)
5. **"Compare US vs UK"** → Create both datasets, run separately
6. **"Show me the phase-out"** → Use Pattern 2 + visualisation

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No UC calculated | Set `would_claim_uc=True` |
| Random UC spikes | Set `is_disabled_for_benefits=False`, `uc_limited_capability_for_WRA=False` |
| KeyError on column | Check variable name in docs, may be different entity level |
| Empty results | Check weights sum correctly, verify ID linkages |
| Slow performance | Use parameter sweep pattern (one simulation for N scenarios) |

## Related Skills

- **microdf-skill** - Weighted DataFrames for inequality/poverty analysis
- **policyengine-uk-skill** - UK tax-benefit system knowledge
- **policyengine-us-skill** - US tax-benefit system knowledge
- **policyengine-analysis-skill** - Using results for policy analysis
- **policyengine-uk-data-skill** - UK survey data enhancement

## Resources

**Repository:** https://github.com/PolicyEngine/policyengine.py
**Documentation:** See `.claude/policyengine-guide.md` and `.claude/quick-reference.md` in repository
**Examples:** `examples/` directory in repository
**Issues:** https://github.com/PolicyEngine/policyengine.py/issues
