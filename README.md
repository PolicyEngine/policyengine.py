# PolicyEngine.py

A Python package for tax-benefit microsimulation analysis. Run policy simulations, analyse distributional impacts, and visualise results across the UK and US.

## Quick start

### Household calculator

```python
import policyengine as pe

# UK: single adult earning £50,000
uk = pe.uk.calculate_household(
    people=[{"age": 35, "employment_income": 50_000}],
    year=2026,
)
print(uk.person[0].income_tax)                   # income tax
print(uk.household.hbai_household_net_income)    # net income

# US: single filer in California, with a reform
us = pe.us.calculate_household(
    people=[{"age": 35, "employment_income": 60_000}],
    tax_unit={"filing_status": "SINGLE"},
    household={"state_code": "CA"},
    year=2026,
    reform={"gov.irs.credits.ctc.amount.adult_dependent": 1000},
)
print(us.tax_unit.income_tax, us.household.household_net_income)
```

### Population analysis

```python
import policyengine as pe

microsim = pe.uk.managed_microsimulation()
print(microsim.policyengine_bundle["runtime_dataset_uri"])
```

For baseline-vs-reform comparisons, see `pe.uk.economic_impact_analysis`
and its US counterpart.

### Reproducible bundle metadata

Each `policyengine` release vendors the matching bundle manifest. The bundle
pins the human-facing `.py` version to exact direct PolicyEngine-owned package
versions, country data artifacts, and a validation digest.

```python
import policyengine as pe

pe.bundle.require_bundle("4.4.2", profile="uk")
print(pe.bundle.get_bundle_digest())
print(pe.uk.bundle["data_package"]["version"])
```

Use `pe.us.managed_microsimulation()` or `pe.uk.managed_microsimulation()` for
bundle-managed population runs. Direct country constructors, such as
`policyengine_us.Microsimulation`, bypass `.py` bundle enforcement. Set
`POLICYENGINE_BUNDLE_STRICT=1` to hard-fail when installed direct packages do
not match the vendored bundle.

## Documentation

**Core concepts:**
- [Core concepts](docs/core-concepts.md): Architecture, datasets, simulations, outputs
- [UK tax-benefit model](docs/country-models-uk.md): Entities, parameters, examples
- [US tax-benefit model](docs/country-models-us.md): Entities, parameters, examples

**Examples:**
- `examples/income_distribution_us.py`: Analyse benefit distribution by decile
- `examples/employment_income_variation_uk.py`: Model employment income phase-outs
- `examples/policy_change_uk.py`: Analyse policy reform impacts
- `examples/paper_repro_uk.py`: Reproduce the UK reform analysis used in the JOSS paper draft

## Installation

### As a library

```bash
pip install policyengine
```

Install a country profile to include the certified direct country dependencies:

```bash
pip install "policyengine[uk]==4.4.2"       # UK model profile
pip install "policyengine[us]==4.4.2"       # US model profile
pip install "policyengine[uk,us]==4.4.2"    # both country profiles
```

For exact transitive reproducibility, install with the matching constraints or
lock artifacts from the corresponding `policyengine-bundles` release.

### For development

```bash
git clone https://github.com/PolicyEngine/policyengine.py.git
cd policyengine.py
uv pip install -e .[dev]        # install with dev dependencies (pytest, ruff, mypy, etc.)
```

## Development

### Running configurations

| Configuration | Install | Use case |
|---------------|---------|----------|
| **Library user** | `pip install policyengine` | Using the package in your own code |
| **UK only** | `pip install policyengine[uk]` | Only need UK simulations |
| **US only** | `pip install policyengine[us]` | Only need US simulations |
| **Developer** | `uv pip install -e .[dev]` | Contributing to the package |

### Common commands

```bash
make format           # ruff format
make test             # pytest with coverage
make docs             # build static Quarto HTML docs
make docs-serve       # preview the docs locally
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
| Docs build | Required | Jupyter Book build |

### Versioning and releases

This project uses [towncrier](https://towncrier.readthedocs.io/) for changelog management. When making a PR, add a changelog fragment:

```bash
# Fragment types: breaking, added, changed, fixed, removed
echo "Description of change" > changelog.d/my-change.added
```

On merge, the versioning workflow bumps the version, builds the changelog, and creates a GitHub Release.

## Paper reproduction

Use the pinned interpreter and the UK extra to run the checked-in paper repro:

```bash
uv run --python 3.14 --extra uk python examples/paper_repro_uk.py
```

On first run this will create `./data/enhanced_frs_2023_24_year_2026.h5`.

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
import policyengine as pe
from policyengine.core import Simulation

simulation = Simulation(
    dataset=dataset,
    tax_benefit_model_version=pe.uk.model,
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
    tax_benefit_model_version=pe.uk.model,
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
    tax_benefit_model_version=pe.uk.model,
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
