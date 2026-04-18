# Development

## Principles

1. **STRONG** preference for simplicity. Let's make this package as simple as it possibly can be.
2. Remember the goal of this package: to make it easy to create, run, save and analyse PolicyEngine simulations. When considering further features, always ask: can we instead *make it super easy* for people to do this outside the package?
3. Be consistent about property names. `name` = human readable few words you could put as the noun in a sentence without fail. `id` = unique identifier, ideally a UUID. `description` = longer human readable text that describes the object. `created_at` and `updated_at` = timestamps for when the object was created and last updated.
4. Constraints can be good. We should set constraints where they help us simplify the codebase and usage, but not where they unnecessarily block useful functionality.

## Setup

```bash
git clone https://github.com/PolicyEngine/policyengine.py.git
cd policyengine.py
uv pip install -e ".[dev]"
```

This installs the shared analysis layer, both country model extras, and the dev
dependencies used in CI (pytest, ruff, mypy, towncrier).

## Common commands

```bash
make format           # ruff format
make test             # pytest with coverage
make docs             # build static MyST/Jupyter Book 2 HTML docs
make docs-serve       # preview the docs locally
make clean            # remove caches, build artifacts, .h5 files
```

## Testing

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

## Linting and formatting

```bash
ruff format .                    # format code
ruff check .                     # lint
mypy src/policyengine            # type check (informational)
```

## CI pipeline

PRs trigger the following checks:

| Check | Status | Command |
|---|---|---|
| Lint + format | Required | `ruff check .` + `ruff format --check .` |
| Tests (Python 3.13) | Required | `make test` |
| Tests (Python 3.14) | Required | `make test` |
| Mypy | Informational | `mypy src/policyengine` |
| Docs build | Required | `make docs` |

## Versioning and releases

This project uses [towncrier](https://towncrier.readthedocs.io/) for changelog management. When making a PR, add a changelog fragment:

```bash
# Fragment types: breaking, added, changed, fixed, removed
echo "Description of change" > changelog.d/my-change.added
```

On merge, the versioning workflow bumps the version, builds the changelog, and creates a GitHub Release.

For the target release-bundle architecture, see [Release bundles](release-bundles.md). That document defines the split between country `*-data` build manifests and `policyengine.py` certified runtime bundles.

## Architecture

### Package layout

```
src/policyengine/
├── core/                  # Domain models (Simulation, Dataset, Policy, etc.)
├── tax_benefit_models/
│   ├── uk/                # UK model, datasets, analysis, outputs
│   └── us/                # US model, datasets, analysis, outputs
├── outputs/               # Output templates (Aggregate, Poverty, etc.)
├── countries/             # Geographic region registries
└── utils/                 # Helpers (reforms, entity mapping, plotting)
```

### Key design decisions

**Pydantic everywhere**: All domain objects are Pydantic `BaseModel` subclasses. This gives us validation, serialisation, and clear field documentation.

**HDF5 for storage**: Datasets and simulation outputs are stored as HDF5 files. No database server is required. The `MicroDataFrame` from the `microdf` package wraps pandas DataFrames with weight-aware `.sum()`, `.mean()`, `.count()`.

**Country-specific model classes**: `PolicyEngineUSLatest` and `PolicyEngineUKLatest` each implement `run()`, `save()`, and `load()`. The US model passes reforms as a dict at `Microsimulation(reform=...)` construction time. The UK model supports both parametric reforms and `simulation_modifier` callables applied post-construction.

**LRU cache + file caching**: `Simulation.ensure()` checks an in-process LRU cache (max 100 entries), then tries loading from disk, then falls back to `run()` + `save()`.

**Output pattern**: All output types inherit from `Output`, implement `.run()`, and populate result fields. Convenience functions (e.g., `calculate_us_poverty_rates()`) create, run, and return collections of output objects.
