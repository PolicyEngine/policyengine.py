# Data certification

Use this skill when certifying a country data release for `policyengine.py`,
or reviewing a certification change.

## What certification is

A data release is published on Hugging Face with a release manifest: per-
artifact repo/revision/sha256 pins, build provenance, compatibility claims,
and region dataset templates. Certification asserts that *this*
`policyengine.py` release, with the model package pinned in
`pyproject.toml`, serves that data release — and the assertion is only made
good by the test suite passing on the exact pinned pair.

There is no intermediate bundle repo. The `data_releases.{country}` entry in
`src/policyengine/data/bundle/manifest.json` is derived directly from the data
release manifest.

## Certifying a release

Open the work on a fresh branch from current `main` (use a clean worktree if
the checkout is dirty).

```bash
python scripts/bundle.py certify-data --country uk --data-producer populace \
  --manifest-uri "hf://dataset/policyengine/populace-uk-private@<tag>/releases/<tag>/release_manifest.json"
```

For US Populace certification, certify the Populace release manifest directly:

```bash
python scripts/bundle.py certify-data --country us --data-producer populace \
  --manifest-uri "hf://dataset/policyengine/populace-us@<tag>/releases/<tag>/release_manifest.json" \
  --model-version "<policyengine-us-version>"
```

US state and congressional-district regions are row filters over the certified
national Populace dataset. Certification writes:

```json
"region_datasets": {
  "national": {"path_template": "populace_us_2024.h5"}
}
```

If the Populace release publishes derived `states/*.h5` or `districts/*.h5`
files for compatibility checks, certification omits them from the runtime
bundle. The national H5 is the canonical `.py` dataset.

The script fetches and validates the manifest (every artifact must carry a
revision pin; the certified dataset must be reachable), writes the canonical
bundle manifest, exact-pins the country model package in that same manifest,
regenerates derived bundle metadata, and writes a Towncrier changelog fragment.

Private data (UK) requires `HUGGING_FACE_TOKEN` or `HF_TOKEN`.

After running:

- run `python scripts/bundle.py check`,
- run the full test suite — snapshot drift from a model bump is refreshed
  with `PE_UPDATE_SNAPSHOTS=1 pytest tests/test_household_calculator_snapshot.py`,
- commit `src/policyengine/data/bundle/manifest.json`, `pyproject.toml`, the
  Towncrier fragment, and any regenerated TRO sidecars together.

A certification PR should normally change only:

- `src/policyengine/data/bundle/manifest.json` (+ `{country}.trace.tro.jsonld`)
- `pyproject.toml`
- one Towncrier fragment under `changelog.d/`
- test constants/snapshots that pin certified versions

## Validation semantics

Hard failures (certification refuses): missing national default dataset,
default dataset absent from artifacts, any artifact without a revision pin,
unreachable certified dataset, missing required supplemental release files
(for example Populace-US `us_source_coverage.json`), missing or malformed US
state overlay artifacts when `--regional-manifest-uri` is used, unknown country.

Certification gate: the model version must either exactly match the
build-time model (`compatibility_basis: built_with_model_package`) or be
covered by the publisher's `compatible_model_packages` claim
(`compatibility_basis: legacy_compatible_model_package`, recorded with a
warning — the publisher's claim is made good only by this repo's test
suite passing on the pinned pair). Neither basis means certification is
refused: a new data build or a published compatibility claim is required.

Warnings (recorded, not blocking): artifacts without sha256, and the
publisher-claim basis above.

## Release runbooks

Concrete, fill-in-the-id runbooks that replay a specific certification live
under `docs/engineering/runbooks/`. See
`runbooks/build-m-us-populace-certification.md` for the next US Populace
`sparse-rmloss100` default.

## Legacy paths

Do not hand-edit bundle data releases for normal updates. Countries whose
current data release predates release manifests need a data-producer strategy
before they can be updated through this path.

The retired `policyengine-bundles` flow (candidates → generated bundle →
archive import) is preserved read-only in that repo's history; bundles
4.15.x–4.16.x remain the historical record of earlier certifications.

## Annual national artifact families

A producer can advertise exact annual inputs through release metadata:

```json
"metadata": {
  "dataset_years": {
    "populace_us_2024": {
      "2024": "populace_us_2024",
      "2025": "populace_us_2025"
    }
  }
}
```

Each value names an ordinary `artifacts` entry with an H5 path, explicit revision
and SHA256. Add every supported year through the projection horizon; do not use
path templates or implicit extension for missing years. Keep the source base
release and content identity in producer provenance separately. Certification
validates this mapping and copies it into `data_releases.us.dataset_years`.
It does not invent artifact pins or certify an unpublished candidate.

Annual files use the existing single-year entity tables plus `_time_period`.
The runtime requires that stored year to match the selected manifest year.
`pe.us.ensure_datasets(years=[2025])` fetches only the requested annual file and
loads its native inputs; it does not calculate or uprate those inputs again.
Return keys retain the requested family name, such as
`populace_us_2024_2025`. Explicit annual artifact names work too, with coverage
limited to that artifact's year. Families without this metadata retain engine
extension behavior.

`pe.us.managed_microsimulation(years=[2025, 2030])` permits external calculations
for those two years. Without `years`, the wrapper selects the years in an explicit
`default_calculation_period`, or the current calendar year. With `years` and no
explicit default period, calculations default to the first selected year. The
wrapper checks coverage before downloading any files and preserves the chosen
default after the engine's initialization. External periods outside the selected
years raise `ValueError`, including years available only for internal lookbacks.
Legacy families without annual metadata do not accept `years`; their existing
country-model period behavior remains unchanged.

The country `USMultiYearDataset` receives the selected years and every advertised
earlier year through the last selected year, with no future inputs. This history
prefix supplies actual prior-year income for Medicare IRMAA, state tax provisions,
and recursive employment-income formulas. Selecting an individual annual artifact
also loads its parent family's earlier inputs. Internal formula lookbacks keep
their normal behavior; the wrapper supplies no history before the family's first
year, so earlier lookbacks retain the country's existing assumptions. The loader
checks schema, row counts and IDs across files, and preserves each year's source
URI, revision and digest in `policyengine_bundle["annual_datasets"]`.

The ordinary `Simulation(dataset=ensure_datasets(...)[...])` route uses the same
annual history. `ensure_datasets` records the required source references in the
dataset's JSON metadata without fetching them; `Simulation.run()` fetches earlier
files when needed. Both the baseline and reform use the country multi-year loader,
including its income-response normalization. Regional runs retain the same current
household IDs in every earlier input year. The wrapper rejects missing or changed
history pins, and the output records those references in `annual_input_sources`.

For a 2024–2035 family in calendar year 2026, default construction loads three
files (2024–2026). Selecting 2035 explicitly loads all 12 files. A local candidate
built during this integration measured 1,754,538,463 bytes (1.755 GB) for the
three-year prefix and 5,928,824,315 bytes (5.929 GB) for all 12 files. Its base
file occupied 826,917,837 bytes; each projected file occupied about 463.81 MB.
These measurements describe candidate artifacts; release certification remains a
separate step. `annual_selected_years`, `annual_loaded_years`,
`annual_input_bytes_by_year`, and `annual_input_bytes` record the actual selection
and file sizes. The total describes input storage and the maximum download size;
cached files do not require another download. Memory also includes decoded tables
and engine arrays, so production adoption still needs a population-scale memory
check. The wrapper performs one full entity load per annual file; its preliminary
`_time_period` check reads only that small entry. `ensure_datasets` materializes
only the requested files and does not load this history prefix.

Source caches live beneath `.policyengine/sources/` and include the artifact's
repository, path, revision, content hash and metadata hash. Derived input caches
beneath `.policyengine/derived/` also include the installed model source/version,
core/wrapper versions, SPM selection and requested year. Legacy basename-only
caches cannot establish that identity and are not reused. Loading never rewrites
annual native files; no model-specific derived input file is necessary.
Annual output cache keys also include the selected dataset, frozen history pins,
and runtime identity, even when a caller reuses an explicit simulation ID.

US regional analysis keeps row filters over the annual national dataset.
Positional weight replacement cannot establish annual year/ID alignment, so the
wrapper rejects it for annual inputs. A separate certified alignment contract
would be necessary before supporting such an overlay.
