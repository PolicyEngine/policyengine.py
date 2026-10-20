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
  --manifest-uri "hf://dataset/policyengine/populace-uk-private@<cut-tag>/releases/<release-id>/release_manifest.json"
```

Pin the cut tag (`@<cut-tag>`), never `main`: each cut of a Microcosm release
line rewrites that line's `releases/<release-id>/` directory, for example
`releases/microcosm-uk-2024-25-national/`. Microcosm records the line name as
`build.build_id` on every cut and the cut in `build.cut_tag`; certification
uses the cut tag as the build id (`data_releases.<country>.version`, the
certification's `data_build_id` and the changelog fragment name), so two cuts
of one line never look identical.

### Builds in their own release folders

Once Microcosm publishes each build in its own folder,
`releases/<release>/<build>/`, a build is never changed after publishing and
gets no Hugging Face tag. The repository's root `releases.json` records which
build of each release is current. That build's `release_manifest.json` names
its `release` and `build` as strings, for example
`microcosm-uk-2024-25-national` and
`uk-frs-calibration-attempt-20261019T083323Z-6cba5d71`. Certify the build from
its own folder, at the commit that published it:

```bash
python scripts/bundle.py certify-data --country uk --data-producer populace \
  --manifest-uri "hf://dataset/policyengine/populace-uk-private@<commit>/releases/<release>/<build>/release_manifest.json"
```

- The URI must be the build's own folder: a manifest that names another
  release or build than the folder it was read from is refused.
- The repository's `releases.json` at `main` must list the build and must not
  mark it withdrawn, or certification refuses it. A local-area release passed
  with `--regional-manifest-uri` is checked the same way. Which build is
  `current` doesn't matter: a certificate pins one build.
- The whole record must also be one the release writer's parser
  (microcosm-emitter's `ReleasesRecord.parse`) accepts, or certification
  refuses it. .py repeats the writer's rules: exactly the keys the writer
  writes, at every level; `schema_version` 1; safe release and build names and
  valid roles; a non-empty `published_at` and a boolean `withdrawn` on every
  build; a `default` that is null or a listed release; a `current` that is null
  or a listed build that isn't withdrawn; and at most 4 MiB.
- The build's own files are pinned at `releases/<release>/<build>/<file>` and
  at the URI's revision, whatever revision their manifest entries name. Each
  one's `path` must be a bare file name, alone or after the folder, as the
  release writer publishes it; a nested path, a `.` or `..` segment or a
  backslash is refused. Artifacts from other repositories keep their own pins.
- The certificate names the build by `build`
  (`data_releases.<country>.version`, the certification's `data_build_id` and
  the changelog fragment name), so two builds of one release never match.
- At import, a remote manifest that names another release or build than the
  bundle's pinned folder is refused, even when the bundle carries a
  certificate. Import doesn't read `releases.json`: a build withdrawn after it
  was certified keeps loading in every installed .py release whose bundle pins
  it. Certifying again changes only the .py releases published afterwards.

Manifests published before this layout, whose `build` is an object, are
certified as described above.

### UK constituency and local-authority regions

UK constituency and local-authority regions row-filter the dataset a regional
release routes them to (`region_datasets.constituency` and
`region_datasets.local_authority`), and the national dataset when nothing is
routed. policyengine-sim-api accepts a UK default without area codes
(`constituency_code_oa`, `la_code_oa`) only when both are routed. Certify a
Microcosm national release with one of:

- **A Microcosm local-area release (ship together).** The release declares
  `dataset_role: non_default_local_area`, as for the US below.

  ```bash
  python scripts/bundle.py certify-data --country uk --data-producer populace \
    --manifest-uri "hf://dataset/policyengine/populace-uk-private@<national-cut-tag>/releases/microcosm-uk-2024-25-national/release_manifest.json" \
    --regional-manifest-uri "hf://dataset/policyengine/populace-uk-private@<local-cut-tag>/releases/<local-release-id>/release_manifest.json" \
    --model-version "<policyengine-uk-version>"
  ```

  This records `regional_release_kind: local_area`, and the default UK region
  registry then includes all 650 constituencies and 361 local authorities.

- **The enhanced FRS (national first).** When the national release is ready
  before a local one, route the area regions to a certified policyengine-uk-data
  release whose households carry area codes:

  ```bash
  python scripts/bundle.py certify-data --country uk --data-producer populace \
    --manifest-uri "hf://dataset/policyengine/populace-uk-private@<national-cut-tag>/releases/microcosm-uk-2024-25-national/release_manifest.json" \
    --regional-manifest-uri "hf://model/policyengine/policyengine-uk-data-private@<revision>/releases/<version>/release_manifest.json" \
    --regional-release-kind area_coded_national \
    --model-version "<policyengine-uk-version>"
  ```

  Certification carries that release's national dataset
  (`enhanced_frs_2024_25`) and its `weights` artifacts (the constituency and
  local-authority matrices and `local_geography_weights`) at their own repo
  and revision, records `regional_release_kind: area_coded_national`, and
  leaves area regions out of the default registry: the API keeps serving them
  from the matrices. The enhanced FRS release must itself claim the pinned
  policyengine-uk version (built with it or listed in
  `compatible_model_packages`); otherwise policyengine-uk-data must publish a
  claim first. Its `frs_2024_25` is not carried, so keep it loadable with a
  `dataset_overlays.uk` entry.

Either way, certification checks that the regional release serves the pinned
model, and the pinned core when `--core-version` is given, by its own build or
compatibility claims (a `--qualified-pair-id` names the primary release only),
and HEAD-checks every artifact it carries.

### Re-certifying a routed bundle

Certification rewrites `data_releases.<country>` from the manifests it is
given. While the bundle routes regions (`regional_source_manifest_uri` is set),
a run without `--regional-manifest-uri` is refused; pass the current regional
release again (or its replacement), or `--drop-regional-release` to remove the
routing on purpose. The two flags cannot be combined.

### US

For US Populace certification, certify the Populace release manifest directly:

```bash
python scripts/bundle.py certify-data --country us --data-producer populace \
  --manifest-uri "hf://dataset/policyengine/populace-us@<tag>/releases/<tag>/release_manifest.json" \
  --regional-manifest-uri "hf://dataset/policyengine/populace-us@<local-area-tag>/releases/<local-area-tag>/release_manifest.json" \
  --model-version "<policyengine-us-version>"
```

US state and congressional-district regions are row filters over one shared,
certified ACS-local Populace dataset. Its release manifest must declare
`dataset_role: non_default_local_area`, `is_default: false`, no default
datasets, and exactly one pinned H5 microdata artifact. Certification writes:

```json
"region_datasets": {
  "national": {"path_template": "populace_us_2024.h5"},
  "state": {"path_template": "populace_us_2024_acs_local.h5"},
  "congressional_district": {"path_template": "populace_us_2024_acs_local.h5"}
}
```

The ACS-local artifact is a second entry in `data_releases.us.datasets`; it is
not a dataset overlay and it never replaces the national `default_dataset`.

If the Populace release publishes derived `states/*.h5` or `districts/*.h5`
files for compatibility checks, certification omits them from the runtime
bundle. The country-wide default and ACS-local dataset are each single shared
files; region registries select one and then filter its rows.

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
(for example Populace-US `us_source_coverage.json`), a malformed shared
local-area release, area-coded national release or legacy per-state artifacts
when `--regional-manifest-uri` is used, a regional release that does not serve
the pinned model version, an unreachable regional artifact, a re-certification
that would silently drop regional routing, unknown country.

Certification gate: the model version must either exactly match the
build-time model (`compatibility_basis: built_with_model_package`) or be
covered by the publisher's `compatible_model_packages` claim
(`compatibility_basis: legacy_compatible_model_package`, recorded with a
warning — the publisher's claim is made good only by this repo's test
suite passing on the pinned pair). Neither basis means certification is
refused: a new data build or a published compatibility claim is required.

Warnings (recorded, not blocking): artifacts without sha256, and the
publisher-claim basis above.

## Acceptance evidence for a UK default switch

A PR that changes the UK default dataset carries, besides the UK candidate
qualification gates, the Universal Credit coverage floor from #491: benefit
units with Universal Credit and Universal Credit spend in Great Britain within
10% of DWP's and the OBR's figures.

```bash
python scripts/check_uk_uc_floor.py --dataset <candidate .h5 or bundle dataset name> \
  --year 2025 --output uc_floor.json
```

The benchmarks and their sources are in
`src/policyengine/data/qualification/uk_uc_floor.json`. The receipt holds
weighted national totals only. Before quoting any other figure from UK data
in a PR, apply the UKDS output rules: no unit-record values, no cells under
10 unweighted cases, no differencing.

## Release runbooks

Concrete, fill-in-the-id runbooks that replay a specific certification live
under `docs/engineering/runbooks/`. See
`runbooks/build-m-us-populace-certification.md` for the reusable US national
and local-area certification procedure. The historical filename is retained
so existing links remain valid.

## Legacy paths

Do not hand-edit bundle data releases for normal updates. Countries whose
current data release predates release manifests need a data-producer strategy
before they can be updated through this path.

The retired `policyengine-bundles` flow (candidates → generated bundle →
archive import) is preserved read-only in that repo's history; bundles
4.15.x–4.16.x remain the historical record of earlier certifications.
