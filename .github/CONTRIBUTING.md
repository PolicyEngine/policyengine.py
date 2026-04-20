# Contributing to policyengine.py

See the [shared PolicyEngine contribution guide](https://github.com/PolicyEngine/.github/blob/main/CONTRIBUTING.md) for cross-repo conventions (towncrier changelog fragments, `uv run`, PR description format, anti-patterns). This file covers policyengine.py specifics.

## Commands

```bash
make install                         # install deps (uv)
make format                          # format (required)
ruff check .                         # lint
uv run mypy src/policyengine         # type check
make test                            # test suite
make docs                            # build documentation

uv run pytest tests/test_household_impact.py::TestUKHouseholdImpact -v
```

Python 3.13+. Default branch: `main`. Tests that download representative datasets need `HUGGING_FACE_TOKEN` set.

## What lives here

policyengine.py is the user-facing analysis package. It wraps `policyengine-uk` and `policyengine-us` with a common `Simulation` object, dataset loaders, and result models (poverty, inequality, decile impacts, programme statistics).

- `src/policyengine/core/` — the shared simulation, dataset, and policy model
- `src/policyengine/tax_benefit_models/uk/` — UK-specific loaders and analysis
- `src/policyengine/tax_benefit_models/us/` — US-specific loaders and analysis
- `src/policyengine/outputs/` — decile/inequality/poverty calculators
- `src/policyengine/utils/` — parametric-reform helpers, entity utilities

Country pins live in `pyproject.toml` under the `[uk]` / `[us]` / `[dev]` extras. Bumping a pin is a patch-level change most of the time; include the motivation in the PR body.

## Repo-specific anti-patterns

- **Don't** bypass the country-model APIs with direct `policyengine-core` calls from user-facing code. The wrapper exists so analyses survive core API changes.
- **Don't** add new public classes without Pydantic models for input/output. JSON round-trip is a documented property of the public surface.
- **Don't** cache arbitrary Python objects — the `core.Simulation` output must be serialisable.

## Examples and notebooks

`examples/` holds runnable scripts that double as documentation. When changing a public API, update or add an example.
