---
title: "Development"
---

## Setup

```bash
git clone https://github.com/PolicyEngine/policyengine.py
cd policyengine.py
uv pip install -e ".[dev]"
```

## Running tests

```bash
make test                     # unit tests
pytest tests/                 # same via pytest
pytest tests/integration      # integration tests (slower, needs h5 data)
```

## Formatting and linting

```bash
make format                   # ruff format
ruff check .                  # ruff lint
```

## Building docs

```bash
make docs                     # quarto render docs -> docs/_site/
make docs-serve               # quarto preview docs with live reload
```

## Regenerating auto-reference pages

```bash
make docs-generate-reference  # pulls variable catalog from installed country models
```

Commit the regenerated pages alongside any country-model bumps. CI will check the reference is current.

## CI

Four workflows in `.github/workflows/`:

- **`pr_code_changes.yaml`** — unit tests, lint, format, changelog fragment on every PR touching code.
- **`pr_docs_changes.yaml`** — verifies `quarto render docs` succeeds on every PR touching docs.
- **`push.yaml`** — full integration tests + publish path on merge to main.
- **`versioning.yaml`** — auto-bumps version when changelog fragments land.

## Contributing

- Follow the existing API shape: `pe.us.calculate_household`, `pe.us.Simulation`, `pe.outputs.*`. Don't add one-off helpers that bypass these.
- New output types subclass `Output` or `ChangeOutput` and live in `src/policyengine/outputs/`.
- Country-specific helpers go under `src/policyengine/tax_benefit_models/<country>/`.
- Add a changelog fragment in `changelog.d/` following towncrier conventions: `echo "Description." > changelog.d/<branch>.<type>.md`. Types: `added`, `changed`, `fixed`, `removed`, `breaking`.

## Architecture

```
src/policyengine/
├── core/                        # Simulation, Dataset, Output base classes
├── countries/                   # Country-neutral protocols
├── data/                        # Generic dataset loading
├── graph/                       # Variable dependency graph (for reference docs)
├── outputs/                     # Typed output classes
├── provenance/                  # Manifests, certification, reproducibility
├── results/                     # Typed household-result structures
├── tax_benefit_models/
│   ├── us/                      # US entry point (calculate_household, model, datasets)
│   ├── uk/                      # UK equivalent
│   └── common/                  # Shared model-version scaffolding
└── utils/
```

Everything users touch is exposed through the top-level `policyengine` namespace. Internal modules are imports of convenience; the contract is the exposed API.
