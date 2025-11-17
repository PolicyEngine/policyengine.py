# US tax-benefit model

The US tax-benefit model implements the United States federal tax and benefit system using PolicyEngine US as the underlying calculation engine.

## Entity structure

The US model uses a more complex entity hierarchy:

```
household
    ├── tax_unit (federal tax filing unit)
    ├── spm_unit (Supplemental Poverty Measure unit)
    ├── family (Census definition)
    └── marital_unit (married couple or single person)
            └── person
```

### Person

Individual people with demographic and income characteristics.

**Key variables:**
- `age`: Person's age in years
- `employment_income`: Annual employment income
- `self_employment_income`: Annual self-employment income
- `social_security`: Annual Social Security benefits
- `ssi`: Annual Supplemental Security Income
- `medicaid`: Annual Medicaid value
- `medicare`: Annual Medicare value
- `unemployment_compensation`: Annual unemployment benefits

### Tax unit

The federal tax filing unit (individual or married filing jointly).

**Key variables:**
- `income_tax`: Federal income tax liability
- `employee_payroll_tax`: Employee payroll tax (FICA)
- `eitc`: Earned Income Tax Credit
- `ctc`: Child Tax Credit
- `income_tax_before_credits`: Tax before credits

### SPM unit

The Supplemental Poverty Measure unit used for SNAP and other means-tested benefits.

**Key variables:**
- `snap`: Annual SNAP (food stamps) benefits
- `tanf`: Annual TANF (cash assistance) benefits
- `spm_unit_net_income`: SPM net income
- `spm_unit_size`: Number of people in unit

### Family

Census definition of family (related individuals).

**Key variables:**
- `family_id`: Family identifier
- `family_weight`: Survey weight

### Marital unit

Married couple or single person.

**Key variables:**
- `marital_unit_id`: Marital unit identifier
- `marital_unit_weight`: Survey weight

### Household

The residence unit.

**Key variables:**
- `household_net_income`: Total household net income
- `household_benefits`: Total benefits received
- `household_tax`: Total tax paid
- `household_market_income`: Total market income before taxes and transfers

**Required fields:**
- `state_code`: State (e.g., "CA", "NY", "TX")

## Using the US model

### Loading representative data

```python
from policyengine.tax_benefit_models.us import PolicyEngineUSDataset

dataset = PolicyEngineUSDataset(
    name="Enhanced CPS 2024",
    description="Enhanced Current Population Survey microdata",
    filepath="./data/enhanced_cps_2024_year_2024.h5",
    year=2024,
)

print(f"People: {len(dataset.data.person):,}")
print(f"Tax units: {len(dataset.data.tax_unit):,}")
print(f"SPM units: {len(dataset.data.spm_unit):,}")
print(f"Households: {len(dataset.data.household):,}")
```

### Creating custom scenarios

```python
import pandas as pd
from microdf import MicroDataFrame
from policyengine.tax_benefit_models.us import USYearData

# Married couple with 2 children
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

tax_unit_df = MicroDataFrame(
    pd.DataFrame({
        "tax_unit_id": [0],
        "tax_unit_weight": [1.0],
    }),
    weights="tax_unit_weight"
)

spm_unit_df = MicroDataFrame(
    pd.DataFrame({
        "spm_unit_id": [0],
        "spm_unit_weight": [1.0],
    }),
    weights="spm_unit_weight"
)

family_df = MicroDataFrame(
    pd.DataFrame({
        "family_id": [0],
        "family_weight": [1.0],
    }),
    weights="family_weight"
)

marital_unit_df = MicroDataFrame(
    pd.DataFrame({
        "marital_unit_id": [0, 1, 2],
        "marital_unit_weight": [1.0, 1.0, 1.0],
    }),
    weights="marital_unit_weight"
)

household_df = MicroDataFrame(
    pd.DataFrame({
        "household_id": [0],
        "household_weight": [1.0],
        "state_code": ["CA"],
    }),
    weights="household_weight"
)

dataset = PolicyEngineUSDataset(
    name="Married couple scenario",
    description="Two adults, two children",
    filepath="./married_couple.h5",
    year=2024,
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

### Running a simulation

```python
from policyengine.core import Simulation
from policyengine.tax_benefit_models.us import us_latest

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=us_latest,
)
simulation.run()

# Check results
output = simulation.output_dataset.data
print(output.household[["household_net_income", "household_benefits", "household_tax"]])
```

## Key parameters

### Income tax

- `gov.irs.income.standard_deduction.joint`: Standard deduction (married filing jointly)
- `gov.irs.income.standard_deduction.single`: Standard deduction (single)
- `gov.irs.income.bracket.rates[0]`: 10% bracket rate
- `gov.irs.income.bracket.rates[1]`: 12% bracket rate
- `gov.irs.income.bracket.rates[2]`: 22% bracket rate
- `gov.irs.income.bracket.thresholds.joint[0]`: 10% bracket threshold (MFJ)
- `gov.irs.income.bracket.thresholds.single[0]`: 10% bracket threshold (single)

### Payroll tax

- `gov.ssa.payroll.rate.employee`: Employee OASDI rate (6.2%)
- `gov.medicare.payroll.rate`: Medicare rate (1.45%)
- `gov.ssa.payroll.cap`: OASDI wage base ($168,600 in 2024)

### Child Tax Credit

- `gov.irs.credits.ctc.amount.base`: Base CTC amount ($2,000 per child)
- `gov.irs.credits.ctc.refundable.amount.max`: Maximum refundable amount ($1,700)
- `gov.irs.credits.ctc.phase_out.threshold.joint`: Phase-out threshold (MFJ)
- `gov.irs.credits.ctc.phase_out.rate`: Phase-out rate

### Earned Income Tax Credit

- `gov.irs.credits.eitc.max[0]`: Maximum EITC (0 children)
- `gov.irs.credits.eitc.max[1]`: Maximum EITC (1 child)
- `gov.irs.credits.eitc.max[2]`: Maximum EITC (2 children)
- `gov.irs.credits.eitc.max[3]`: Maximum EITC (3+ children)
- `gov.irs.credits.eitc.phase_out.start[0]`: Phase-out start (0 children)
- `gov.irs.credits.eitc.phase_out.rate[0]`: Phase-out rate (0 children)

### SNAP

- `gov.usda.snap.normal_allotment.max[1]`: Maximum benefit (1 person)
- `gov.usda.snap.normal_allotment.max[2]`: Maximum benefit (2 people)
- `gov.usda.snap.income_limit.net`: Net income limit (100% FPL)
- `gov.usda.snap.income_deduction.earned.rate`: Earned income deduction rate (20%)

## Common policy reforms

### Increasing standard deduction

```python
from policyengine.core import Policy, Parameter, ParameterValue
import datetime

parameter = Parameter(
    name="gov.irs.income.standard_deduction.single",
    tax_benefit_model_version=us_latest,
    description="Standard deduction (single)",
    data_type=float,
)

policy = Policy(
    name="Increase standard deduction to $20,000",
    description="Raises single standard deduction from $14,600 to $20,000",
    parameter_values=[
        ParameterValue(
            parameter=parameter,
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            value=20000,
        )
    ],
)
```

### Expanding Child Tax Credit

```python
parameter = Parameter(
    name="gov.irs.credits.ctc.amount.base",
    tax_benefit_model_version=us_latest,
    description="Base CTC amount",
    data_type=float,
)

policy = Policy(
    name="Increase CTC to $3,000",
    description="Expands CTC from $2,000 to $3,000 per child",
    parameter_values=[
        ParameterValue(
            parameter=parameter,
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            value=3000,
        )
    ],
)
```

### Making CTC fully refundable

```python
parameter = Parameter(
    name="gov.irs.credits.ctc.refundable.amount.max",
    tax_benefit_model_version=us_latest,
    description="Maximum refundable CTC",
    data_type=float,
)

policy = Policy(
    name="Fully refundable CTC",
    description="Makes entire $2,000 CTC refundable",
    parameter_values=[
        ParameterValue(
            parameter=parameter,
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            value=2000,  # Match base amount
        )
    ],
)
```

## State variations

The US model includes state-level variations for:

- **State income tax**: Different rates and structures by state
- **State EITC**: State supplements to federal EITC
- **Medicaid**: State-specific eligibility and benefits
- **TANF**: State-administered cash assistance

### State codes

Use two-letter state codes (e.g., "CA", "NY", "TX"). All 50 states plus DC are supported.

## Entity mapping considerations

The US model's complex entity structure requires careful attention to entity mapping:

### Person → Household

When mapping person-level variables (like `ssi`) to household level, values are summed across all household members:

```python
agg = Aggregate(
    simulation=simulation,
    variable="ssi",  # Person-level
    entity="household",  # Aggregate to household
    aggregate_type=AggregateType.SUM,
)
# Result: Total SSI for all persons in each household
```

### Tax unit → Household

Tax units nest within households. A household may contain multiple tax units (e.g., adult child filing separately):

```python
agg = Aggregate(
    simulation=simulation,
    variable="income_tax",  # Tax unit level
    entity="household",  # Aggregate to household
    aggregate_type=AggregateType.SUM,
)
# Result: Total income tax for all tax units in each household
```

### Household → Person

Household variables are replicated to all household members:

```python
# household_net_income at person level
# Each person in household gets the same household_net_income value
```

### Direct entity mapping

For complex multi-entity scenarios, you can use `map_to_entity` directly:

```python
# Map SPM unit SNAP benefits to household level
household_snap = dataset.data.map_to_entity(
    source_entity="spm_unit",
    target_entity="household",
    columns=["snap"],
    how="sum"
)

# Split tax unit income equally among persons
person_tax_income = dataset.data.map_to_entity(
    source_entity="tax_unit",
    target_entity="person",
    columns=["taxable_income"],
    how="divide"
)

# Map custom analysis values
custom_analysis = dataset.data.map_to_entity(
    source_entity="person",
    target_entity="tax_unit",
    values=custom_values_array,
    how="sum"
)
```

See the [Entity mapping section](core-concepts.md#entity-mapping) in Core Concepts for full documentation on aggregation methods.

## Data sources

The US model can use several data sources:

1. **Current Population Survey (CPS)**: Census Bureau household survey
   - ~60,000 households
   - Detailed income and demographic data
   - Published annually

2. **Enhanced CPS**: Calibrated and enhanced version
   - Uprated to population totals
   - Imputed benefit receipt
   - Multiple projection years

3. **Custom datasets**: User-created scenarios
   - Full control over household composition
   - Exact income levels
   - Specific tax filing scenarios

## Validation

When creating custom datasets, validate:

1. **Entity relationships**: All persons link to valid tax_unit, spm_unit, household
2. **Join key naming**: Use `person_household_id`, `person_tax_unit_id`, etc.
3. **Weights**: Appropriate weights for each entity level
4. **State codes**: Valid two-letter codes
5. **Filing status**: Tax units should reflect actual filing patterns

## Examples

See working examples in the `examples/` directory:

- `income_distribution_us.py`: Analyse benefit distribution by income decile
- `employment_income_variation_us.py`: Vary employment income, analyse phase-outs
- `speedtest_us_simulation.py`: Performance benchmarking

## References

- PolicyEngine US documentation: https://policyengine.github.io/policyengine-us/
- IRS tax information: https://www.irs.gov/forms-pubs
- Benefits.gov: https://www.benefits.gov/
- SPM methodology: https://www.census.gov/topics/income-poverty/supplemental-poverty-measure.html
