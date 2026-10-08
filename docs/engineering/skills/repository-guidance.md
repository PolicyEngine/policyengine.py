# Repository Guidance

Use this skill when making or reviewing repository-wide API, testing,
documentation, release, or package-boundary changes.

## Commands

```bash
make install                         # install deps (uv)
make format                          # format files
make lint                            # format check and ruff lint
uv run mypy src/policyengine         # type check
make test                            # test suite
make docs                            # build documentation

uv run pytest tests/test_household_impact.py::TestUKHouseholdImpact -v
```

Python 3.13+. Default branch: `main`. Tests that download representative
datasets need `HUGGING_FACE_TOKEN` set.

## What Lives Here

- `src/policyengine/core/` contains the shared simulation, dataset, and policy
  model.
- `src/policyengine/tax_benefit_models/uk/` contains UK-specific loaders and
  analysis.
- `src/policyengine/tax_benefit_models/us/` contains US-specific loaders and
  analysis.
- `src/policyengine/outputs/` contains decile, inequality, poverty, program
  statistics, and impact calculators.
- `src/policyengine/utils/` contains parametric-reform helpers, entity utilities,
  and shared support code.

Country pins live in `pyproject.toml` under the `[uk]`, `[us]`, and `[dev]`
extras. Bumping a pin is usually a patch-level change; include the motivation in
the PR body.

## Public Surface

- Prefer the country-model APIs over direct `policyengine-core` calls from
  user-facing code.
- Public input and output classes should be Pydantic models.
- Public result structures must be JSON-serialisable.
- Examples under `examples/` double as documentation. When changing a public
  API, update or add an example when useful.

## Testing

Keep tests focused on the changed behavior and avoid adding long-running
representative-data runs unless the change specifically needs that coverage.
When a test needs country package data, make the dependency explicit and skip
cleanly if credentials or local artifacts are unavailable.

## UK country filtering

Raw UK household data stores `region`. The UK model derives `country` from
that input during calculation. Filtering precedes calculation, so agents and
developers must use `region` for country selection even though the registry's
public identifiers start with `country/`.

| Public selector | Required input filter |
| --- | --- |
| `country/scotland` | `region == "SCOTLAND"` |
| `country/wales` | `region == "WALES"` |
| `country/northern_ireland` | `region == "NORTHERN_IRELAND"` |
| `country/england` | `region` is one of the nine English values below |

The English values are `NORTH_EAST`, `NORTH_WEST`, `YORKSHIRE`, `EAST_MIDLANDS`,
`WEST_MIDLANDS`, `EAST_OF_ENGLAND`, `LONDON`, `SOUTH_EAST`, and `SOUTH_WEST`.
There is no stored `ENGLAND` region value. Use explicit membership so unknown
or missing regions do not become English households.

Keep all four country entries as `RowFilterStrategy` so the simulation API can
combine them with `RegionGroupStrategy`. Do not add a dataset `country` column
or run a preliminary model calculation to work around an incorrect filter.
Preserve household membership, related people/benefit units, and weights.

Regression tests must exercise Scotland, Wales, Northern Ireland, and England
against household inputs with `region` and **no `country` column**, including
the string and byte representations accepted by the dataset loader. See
`tests/test_uk_regions.py` and the public explanation in `docs/regions.md`.

## Anti-Patterns

- Do not bypass the wrapper layer without a clear reason.
- Do not add untyped or non-serialisable public result containers.
- Do not hide country-package version changes; call them out in the PR body.
- Do not add `[codex]`, `[claude]`, `[copilot]`, or other agent labels to PR
  titles.
