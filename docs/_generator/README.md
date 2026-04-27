# Reference generator prototype

Auto-generates one Quarto page per variable in a country model, plus a program coverage index and one page per program, purely from metadata on the `Variable` classes and `programs.yaml`.

## Run

```bash
# Full US reference (takes a couple of minutes — 4,686 variables)
python docs/_generator/build_reference.py --country us --out docs/_generated/reference/us

# Preview a filtered subset
python docs/_generator/build_reference.py --country us --filter chip --out /tmp/ref-preview
```

Then render:

```bash
cd /tmp/ref-preview && quarto render
```

## What's generated from code alone

Per variable:

- Title and identifier
- Metadata table: entity, value type, unit, period, `defined_for` gate
- Documentation (docstring)
- Components (`adds` / `subtracts` lists)
- Statutory references (from `reference = ...`)
- Source file path and line number

Per program: a row in the generated program coverage index pulled from `programs.yaml` (name, category, agency, status, coverage, root variable), plus a generated program page with metadata, notes, and links to implementation variables.

Per directory (`gov/hhs/chip/`, `gov/usda/snap/`, etc.): a listing page using Quarto's built-in directory listing so the nav auto-organizes.

## What still requires hand-authored prose

- Methodology narrative (why the model is structured this way)
- Tutorials (how to use `policyengine.py`)
- Paper content (peer-reviewable argument)
- Per-country deep dives that read as essays rather than reference lookups

## Design

The generator reads directly from the imported country model — no web API calls, no intermediate JSON. This keeps the build offline-reproducible and version-pinned to whatever country model the `policyengine.py` package has installed. Re-running the generator on release produces a snapshot of the reference docs tied to the exact published model versions.

Extensions worth considering:

1. Walk `parameters/` YAML tree and emit a page per parameter with its time series, breakdowns, and references.
2. For each variable with a formula, surface the dependency graph (other variables / parameters it reads). `policyengine_core`'s `Variable.exhaustive_parameter_dependencies` gets partway there.
3. For each calibration target (in `policyengine-us-data/storage/calibration_targets/*.csv`), emit a page describing source, aggregation level, freshness.
4. Add reverse links from variable pages back to the programs that use them.
