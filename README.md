# PolicyEngine.py

A Python package for tax-benefit microsimulation analysis. Run policy simulations, analyse distributional impacts, and visualise results across the UK and US.

## Quick start

```python
from policyengine.core import Simulation
from policyengine.tax_benefit_models.uk import PolicyEngineUKDataset, uk_latest
from policyengine.outputs.aggregate import Aggregate, AggregateType

# Load representative microdata
dataset = PolicyEngineUKDataset(
    name="FRS 2023-24",
    filepath="./data/frs_2023_24_year_2026.h5",
    year=2026,
)

# Run simulation
simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
simulation.run()

# Calculate total universal credit spending
agg = Aggregate(
    simulation=simulation,
    variable="universal_credit",
    aggregate_type=AggregateType.SUM,
    entity="benunit",
)
agg.run()
print(f"Total UC spending: £{agg.result / 1e9:.1f}bn")
```

## Documentation

**Core concepts:**
- [Core concepts](docs/core-concepts.md): Architecture, datasets, simulations, outputs
- [UK tax-benefit model](docs/country-models-uk.md): Entities, parameters, examples
- [US tax-benefit model](docs/country-models-us.md): Entities, parameters, examples

**Examples:**
- `examples/income_distribution_us.py`: Analyse benefit distribution by decile
- `examples/employment_income_variation_uk.py`: Model employment income phase-outs
- `examples/policy_change_uk.py`: Analyse policy reform impacts

## Installation

```bash
pip install policyengine
```

## Features

- **Multi-country support**: UK and US tax-benefit systems
- **Representative microdata**: Load FRS, CPS, or create custom scenarios
- **Policy reforms**: Parametric reforms with date-bound parameter values
- **Distributional analysis**: Aggregate statistics by income decile, demographics
- **Entity mapping**: Automatic mapping between person, household, tax unit levels
- **Visualisation**: PolicyEngine-branded charts with Plotly

## Key concepts

### Datasets

Datasets contain microdata at entity level (person, household, tax unit). Load representative data or create custom scenarios:

```python
from policyengine.tax_benefit_models.uk import PolicyEngineUKDataset

dataset = PolicyEngineUKDataset(
    name="Representative data",
    filepath="./data/frs_2023_24_year_2026.h5",
    year=2026,
)
dataset.load()
```

### Simulations

Simulations apply tax-benefit models to datasets:

```python
from policyengine.core import Simulation
from policyengine.tax_benefit_models.uk import uk_latest

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
simulation.run()

# Access calculated variables
output = simulation.output_dataset.data
print(output.household[["household_net_income", "household_benefits"]])
```

### Outputs

Extract insights with aggregate statistics:

```python
from policyengine.outputs.aggregate import Aggregate, AggregateType

# Mean income in top decile
agg = Aggregate(
    simulation=simulation,
    variable="household_net_income",
    aggregate_type=AggregateType.MEAN,
    filter_variable="household_net_income",
    quantile=10,
    quantile_eq=10,
)
agg.run()
print(f"Top decile mean income: £{agg.result:,.0f}")
```

### Policy reforms

Apply parametric reforms:

```python
from policyengine.core import Policy, Parameter, ParameterValue
import datetime

parameter = Parameter(
    name="gov.hmrc.income_tax.allowances.personal_allowance.amount",
    tax_benefit_model_version=uk_latest,
    data_type=float,
)

policy = Policy(
    name="Increase personal allowance",
    parameter_values=[
        ParameterValue(
            parameter=parameter,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
            value=15000,
        )
    ],
)

# Run reform simulation
reform_sim = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
    policy=policy,
)
reform_sim.run()
```

## Country models

### UK

Three entity levels:
- **Person**: Individual with income and demographics
- **Benunit**: Benefit unit (single person or couple with children)
- **Household**: Residence unit

Key benefits: Universal Credit, Child Benefit, Pension Credit
Key taxes: Income tax, National Insurance

### US

Six entity levels:
- **Person**: Individual
- **Tax unit**: Federal tax filing unit
- **SPM unit**: Supplemental Poverty Measure unit
- **Family**: Census family definition
- **Marital unit**: Married couple or single person
- **Household**: Residence unit

Key benefits: SNAP, TANF, EITC, CTC, SSI, Social Security
Key taxes: Federal income tax, payroll tax

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

AGPL-3.0
