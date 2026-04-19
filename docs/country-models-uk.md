# UK tax-benefit model

The UK tax-benefit model implements the United Kingdom's tax and benefit system using PolicyEngine UK as the underlying calculation engine.

## Quick start

```python
import policyengine as pe

# Single adult earning £50k
result = pe.uk.calculate_household(
    people=[{"age": 35, "employment_income": 50_000}],
    year=2026,
)
print(result.person[0].income_tax, result.household.hbai_household_net_income)

# Family renting, with benefit claims explicitly on
result = pe.uk.calculate_household(
    people=[
        {"age": 35, "employment_income": 30_000},
        {"age": 33},
        {"age": 8},
        {"age": 5},
    ],
    benunit={"would_claim_uc": True, "would_claim_child_benefit": True},
    household={"rent": 12_000, "region": "NORTH_WEST"},
    year=2026,
)

# Apply a reform
result = pe.uk.calculate_household(
    people=[{"age": 35, "employment_income": 50_000}],
    year=2026,
    reform={
        "gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000,
    },
)
```

For population-level analysis and reform analysis, see
[Economic impact analysis](economic-impact-analysis.md).

## Entity structure

The UK model uses three entity levels:

```
household
    └── benunit (benefit unit)
            └── person
```

### Person

Individual people with demographic and income characteristics.

**Key variables:**
- `age`: Person's age in years
- `employment_income`: Annual employment income
- `self_employment_income`: Annual self-employment income
- `pension_income`: Annual pension income
- `savings_interest_income`: Annual interest from savings
- `dividend_income`: Annual dividend income
- `income_tax`: Total income tax paid
- `national_insurance`: Total NI contributions
- `is_disabled_for_benefits`: Whether disabled for benefit purposes

### Benunit (benefit unit)

The unit for benefit assessment. Usually a single person or a couple with dependent children.

**Key variables:**
- `universal_credit`: Annual UC payment
- `child_benefit`: Annual child benefit
- `working_tax_credit`: Annual WTC (legacy system)
- `child_tax_credit`: Annual CTC (legacy system)
- `pension_credit`: Annual pension credit
- `income_support`: Annual income support
- `housing_benefit`: Annual housing benefit
- `council_tax_support`: Annual council tax support

**Important flags:**
- `would_claim_uc`: Must be True to claim UC
- `would_claim_WTC`: Must be True to claim WTC
- `would_claim_CTC`: Must be True to claim CTC
- `would_claim_IS`: Must be True to claim IS
- `would_claim_pc`: Must be True to claim pension credit
- `would_claim_child_benefit`: Must be True to claim child benefit
- `would_claim_housing_benefit`: Must be True to claim HB

### Household

The residence unit, typically sharing accommodation.

**Key variables:**
- `household_net_income`: Total household net income
- `hbai_household_net_income`: HBAI-equivalised net income
- `household_benefits`: Total benefits received
- `household_tax`: Total tax paid
- `household_market_income`: Total market income

**Required fields:**
- `region`: UK region (e.g., "LONDON", "SOUTH_EAST")
- `tenure_type`: Housing tenure (e.g., "RENT_PRIVATELY", "OWNED_OUTRIGHT")
- `rent`: Annual rent paid
- `council_tax`: Annual council tax

## Using the UK model

### Loading representative data

```python
from policyengine.tax_benefit_models.uk import PolicyEngineUKDataset

dataset = PolicyEngineUKDataset(
    name="FRS 2023-24",
    description="Family Resources Survey microdata",
    filepath="./data/frs_2023_24_year_2026.h5",
    year=2026,
)

print(f"People: {len(dataset.data.person):,}")
print(f"Benefit units: {len(dataset.data.benunit):,}")
print(f"Households: {len(dataset.data.household):,}")
```

### Creating custom scenarios

```python
import pandas as pd
from microdf import MicroDataFrame
from policyengine.tax_benefit_models.uk import UKYearData

# Single parent with 2 children
person_df = MicroDataFrame(
    pd.DataFrame({
        "person_id": [0, 1, 2],
        "person_benunit_id": [0, 0, 0],
        "person_household_id": [0, 0, 0],
        "age": [35, 8, 5],
        "employment_income": [25000, 0, 0],
        "person_weight": [1.0, 1.0, 1.0],
        "is_disabled_for_benefits": [False, False, False],
        "uc_limited_capability_for_WRA": [False, False, False],
    }),
    weights="person_weight"
)

benunit_df = MicroDataFrame(
    pd.DataFrame({
        "benunit_id": [0],
        "benunit_weight": [1.0],
        "would_claim_uc": [True],
        "would_claim_child_benefit": [True],
        "would_claim_WTC": [True],
        "would_claim_CTC": [True],
    }),
    weights="benunit_weight"
)

household_df = MicroDataFrame(
    pd.DataFrame({
        "household_id": [0],
        "household_weight": [1.0],
        "region": ["LONDON"],
        "rent": [15000],  # £1,250/month
        "council_tax": [2000],
        "tenure_type": ["RENT_PRIVATELY"],
    }),
    weights="household_weight"
)

dataset = PolicyEngineUKDataset(
    name="Single parent scenario",
    description="One adult, two children",
    filepath="./single_parent.h5",
    year=2026,
    data=UKYearData(
        person=person_df,
        benunit=benunit_df,
        household=household_df,
    )
)
```

### Running a simulation

```python
from policyengine.core import Simulation
import policyengine as pe

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
)
simulation.run()

# Check results
output = simulation.output_dataset.data
print(output.household[["household_net_income", "household_benefits", "household_tax"]])
```

## Key parameters

### Income tax

- `gov.hmrc.income_tax.allowances.personal_allowance.amount`: Personal allowance (£12,570 in 2024-25)
- `gov.hmrc.income_tax.rates.uk[0].rate`: Basic rate (20%)
- `gov.hmrc.income_tax.rates.uk[1].rate`: Higher rate (40%)
- `gov.hmrc.income_tax.rates.uk[2].rate`: Additional rate (45%)
- `gov.hmrc.income_tax.rates.uk[0].threshold`: Basic rate threshold (£50,270)
- `gov.hmrc.income_tax.rates.uk[1].threshold`: Higher rate threshold (£125,140)

### National insurance

- `gov.hmrc.national_insurance.class_1.main.primary_threshold`: Primary threshold (£12,570)
- `gov.hmrc.national_insurance.class_1.main.upper_earnings_limit`: Upper earnings limit (£50,270)
- `gov.hmrc.national_insurance.class_1.main.rate`: Main rate (12% below UEL, 2% above)

### Universal credit

- `gov.dwp.universal_credit.elements.standard_allowance.single_adult`: Standard allowance for single adult (£334.91/month in 2024-25)
- `gov.dwp.universal_credit.elements.child.first_child`: First child element (£333.33/month)
- `gov.dwp.universal_credit.elements.child.subsequent_child`: Subsequent children (£287.92/month each)
- `gov.dwp.universal_credit.means_test.reduction_rate`: Taper rate (55%)
- `gov.dwp.universal_credit.means_test.earned_income.disregard`: Work allowance

### Child benefit

- `gov.hmrc.child_benefit.rates.eldest_child`: First child rate (£25.60/week)
- `gov.hmrc.child_benefit.rates.additional_child`: Additional children (£16.95/week each)
- `gov.hmrc.child_benefit.income_tax_charge.threshold`: HICBC threshold (£60,000)

## Common policy reforms

All reform examples use the same flat ``{parameter.path: value}`` dict
the household calculator accepts. ``Simulation`` compiles it into a
``Policy`` at construction; scalar values default to
``{dataset.year}-01-01``.

### Increasing personal allowance

```python
policy = {"gov.hmrc.income_tax.allowances.personal_allowance.amount": 15_000}
```

### Adjusting UC taper rate

```python
policy = {"gov.dwp.universal_credit.means_test.reduction_rate": 0.50}
```

### Abolishing the two-child limit

```python
# Set the subsequent-child element equal to the first-child rate.
policy = {"gov.dwp.universal_credit.elements.child.subsequent_child": 333.33}
```

Plug any of the above into ``Simulation(policy=policy, ...)``.

## Regional variations

The UK model accounts for regional differences:

- **Council tax**: Varies by local authority
- **Rent levels**: Regional housing markets
- **Scottish income tax**: Different rates and thresholds for Scottish taxpayers

### Regions

Valid region values:
- `LONDON`
- `SOUTH_EAST`
- `SOUTH_WEST`
- `EAST_OF_ENGLAND`
- `WEST_MIDLANDS`
- `EAST_MIDLANDS`
- `YORKSHIRE`
- `NORTH_WEST`
- `NORTH_EAST`
- `WALES`
- `SCOTLAND`
- `NORTHERN_IRELAND`

## Entity mapping

The UK model has a simpler entity structure than the US, with three levels: person → benunit → household.

### Direct entity mapping

You can map data between entities using the `map_to_entity` method:

```python
# Map person income to benunit level
benunit_income = dataset.data.map_to_entity(
    source_entity="person",
    target_entity="benunit",
    columns=["employment_income"],
    how="sum"
)

# Split household rent equally among persons
person_rent_share = dataset.data.map_to_entity(
    source_entity="household",
    target_entity="person",
    columns=["rent"],
    how="divide"
)

# Map benunit UC to household level
household_uc = dataset.data.map_to_entity(
    source_entity="benunit",
    target_entity="household",
    columns=["universal_credit"],
    how="sum"
)
```

See the [Entity mapping section](core-concepts.md#entity-mapping) in Core Concepts for full documentation on aggregation methods.

## Data sources

The UK model can use several data sources:

1. **Family Resources Survey (FRS)**: Official UK household survey
   - ~19,000 households
   - Detailed income and benefit receipt
   - Published annually

2. **Enhanced FRS**: Uprated and enhanced version
   - Calibrated to population totals
   - Additional imputed variables
   - Multiple projection years

3. **Custom datasets**: User-created scenarios
   - Full control over household composition
   - Exact income levels
   - Specific benefit claiming patterns

## Validation

When creating custom datasets, validate:

1. **Would claim flags**: All set to True
2. **Disability flags**: Set explicitly (not random)
3. **Join keys**: Person data links to benunits and households
4. **Required fields**: Region, tenure_type set correctly
5. **Weights**: Sum to expected values
6. **Income ranges**: Realistic values

## Examples

- [UK employment income variation](examples.md#uk-employment-income-variation): Vary employment income, analyse benefit phase-outs
- [UK policy reform analysis](examples.md#uk-policy-reform-analysis): Apply reforms, analyse winners/losers
- [UK income bands](examples.md#uk-income-bands): Calculate net income and tax by income decile

## References

- PolicyEngine UK documentation: https://policyengine.github.io/policyengine-uk/
- UK tax-benefit system: https://www.gov.uk/browse/benefits
- HBAI methodology: https://www.gov.uk/government/statistics/households-below-average-income-for-financial-years-ending-1995-to-2023
