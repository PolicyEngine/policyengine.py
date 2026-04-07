# PolicyEngine.py

A Python package for tax-benefit microsimulation analysis. Run policy simulations, analyse distributional impacts, and visualise results across the UK and US.

## Quick start

Install the UK country model first:

```bash
pip install "policyengine[uk]"
```

```python
from policyengine.core import Simulation
from policyengine.outputs.aggregate import Aggregate, AggregateType
from policyengine.tax_benefit_models.uk import ensure_datasets, uk_latest

# First run downloads representative microdata to ./data; later runs reuse it
datasets = ensure_datasets(
    datasets=["hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5"],
    years=[2026],
    data_folder="./data",
)
dataset = datasets["enhanced_frs_2023_24_2026"]

# Run simulation
simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=uk_latest,
)
simulation.ensure()

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

## Smoke test

To verify a fresh install without downloading representative datasets:

```bash
pip install "policyengine[uk,us]"
python examples/household_impact_example.py
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

### As a library

```bash
pip install policyengine
```

This installs the shared analysis layer only. Add country model extras for the
systems you want to analyze:

```bash
pip install "policyengine[uk]"      # shared layer + UK model
pip install "policyengine[us]"      # shared layer + US model
pip install "policyengine[uk,us]"   # shared layer + both country models
```

### For development

```bash
git clone https://github.com/PolicyEngine/policyengine.py.git
cd policyengine.py
uv pip install -e ".[dev]"      # install with dev dependencies (pytest, ruff, mypy, etc.)
```

## Development

### Running configurations

| Configuration | Install | Use case |
|---------------|---------|----------|
| **Library user** | `pip install policyengine` | Shared analysis layer only |
| **UK only** | `pip install "policyengine[uk]"` | Shared layer plus UK simulations |
| **US only** | `pip install "policyengine[us]"` | Shared layer plus US simulations |
| **Both countries** | `pip install "policyengine[uk,us]"` | Shared layer plus UK and US simulations |
| **Developer** | `uv pip install -e ".[dev]"` | Contributing to the package |

### Common commands

```bash
make format           # ruff format
make test             # pytest with coverage
make docs             # run the MyST docs build used in CI via npx
make clean            # remove caches, build artifacts, .h5 files
```

### Testing

Tests require a `HUGGING_FACE_TOKEN` environment variable for downloading datasets:

```bash
export HUGGING_FACE_TOKEN=hf_...
make test
```

To run a specific test:

```bash
pytest tests/test_models.py -v
pytest tests/test_parametric_reforms.py -k "test_uk" -v
```

### Linting and type checking

```bash
ruff format .                    # format code
ruff check .                     # lint
mypy src/policyengine            # type check (informational — not yet enforced in CI)
```

### CI pipeline

PRs trigger the following checks:

| Check | Status | Command |
|-------|--------|---------|
| Lint + format | Required | `ruff check .` + `ruff format --check .` |
| Tests (Python 3.13) | Required | `make test` |
| Tests (Python 3.14) | Required | `make test` |
| Mypy | Informational | `mypy src/policyengine` |
| Docs build | Required | `make docs` |

### Versioning and releases

This project uses [towncrier](https://towncrier.readthedocs.io/) for changelog management. When making a PR, add a changelog fragment:

```bash
# Fragment types: breaking, added, changed, fixed, removed
echo "Description of change" > changelog.d/my-change.added
```

On merge, the versioning workflow bumps the version, builds the changelog, and creates a GitHub Release.

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
from policyengine.tax_benefit_models.uk import ensure_datasets

datasets = ensure_datasets(
    datasets=["hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5"],
    years=[2026],
    data_folder="./data",
)
dataset = datasets["enhanced_frs_2023_24_2026"]
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

See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) for development setup and guidelines.

## License

AGPL-3.0
