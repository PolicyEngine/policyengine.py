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

- **An older local-area release, on an accepted mismatch.** When the national
  cut moves to a new policyengine-uk before a local-area cut on that version
  exists, a reviewer can accept retaining the older regional route. A reason
  and a byte-bound input-surface audit are both required. First audit the
  actual local H5 with the exact target model installed. The audit also needs
  `uv` and access to PyPI (see below):

  ```bash
  .venv/bin/python scripts/audit_regional_input_surface.py \
    --regional-manifest-uri "<the routed local-area release_manifest.json URI>" \
    --artifact "microcosm_uk_2024_25_dense=/local/dense.h5" \
    --model-version 2.147.2 \
    --audited-by "<reviewer>" \
    --limitation "the dense cut's VAT predates the policyengine-uk VAT factor fix (#2187, 2.135.7); the dashboard holds a VAT limit" \
    --output regional-input-surface.json

  .venv/bin/python scripts/bundle.py certify-data --country uk --data-producer populace \
    --manifest-uri "hf://dataset/policyengine/populace-uk-private@<national-cut-tag>/releases/microcosm-uk-2024-25-national/release_manifest.json" \
    --regional-manifest-uri "<the routed local-area release_manifest.json URI>" \
    --accept-regional-model-mismatch "<who accepted it and why>" \
    --regional-input-surface-evidence regional-input-surface.json \
    --model-version 2.147.2
  ```

  The audit compares the entity-table columns the H5 actually stores, in each
  period, with two models: the build model and core the regional manifest
  records (`build.built_with_model_package` and
  `build.built_with_core_package`), and the target. As in Microcosm #1348's
  `tools/certify_uk_cut_in_policyengine_py.py`, the build model is the
  baseline:

  - **Dropped columns** are stored columns the build model defines and the
    target does not. The target's loaders skip them. Certification refuses
    **any dropped column**; there is no override.
  - **Never-modelled columns** are stored columns neither model defines:
    Microcosm's own area codes (among them `constituency_code_oa` and
    `la_code_oa`), build and source ids, clone indices and SPI donor fields.
    No model ever loaded them, so they are recorded, not refused.
  - **Defaulted inputs** are target inputs the file does not store, after the
    target's input aliases, that were not inputs of the build model. Area runs
    default them where the build model did not. Inputs absent under both
    models are not changes.

  The audit reads the build model's variables and inputs in a throwaway
  `uv run --no-project --no-config --default-index https://pypi.org/simple
  --exclude-newer <build.built_at> --with policyengine-uk==<build> --with
  policyengine-core==<core>` environment, so it needs `uv` and access to
  PyPI. `--exclude-newer` is the manifest's build time, so the build model's
  other dependencies resolve as they did then, and every `UV_*` setting
  except the cache, Python-install and connection ones is removed. A regional
  manifest that does not record both build versions has no baseline, and the
  audit refuses it. The evidence binds the regional release identity,
  original manifest bytes, actual H5 bytes, both build versions and the exact
  target model version, and keeps both models' full variable and input lists.

  Certification does not trust those lists. It reads the target model in
  process, so the environment that runs `certify-data` must have the target
  policyengine-uk installed, as the audit's does, and reads the build model
  again with `uv`; any list or input alias that differs refuses. Only the
  stored columns rest on the auditor's word: they cannot be re-read without
  the H5, and the evidence binds them to its SHA-256. Certification then
  recomputes all three lists and refuses missing or mismatched evidence,
  including evidence without `schema_version: 2`, from before the comparison
  was relative to the build model. It records the never-modelled columns,
  every defaulted input and the free-text limitations in the validated
  `regional_certification`, and adds one limitation naming the defaulted
  inputs; the bundle hash binds that record.

  The policyengine-uk 2.147.2 dataset loaders silently skip columns absent
  from the model's variables: both the
  [generic dataset loader](https://github.com/PolicyEngine/policyengine-uk/blob/fe0b99a36bd309a722b19937345e34290cb6dd73/policyengine_uk/simulation.py#L1113-L1127)
  and the
  [UK multi-year loader](https://github.com/PolicyEngine/policyengine-uk/blob/fe0b99a36bd309a722b19937345e34290cb6dd73/policyengine_uk/simulation.py#L1186-L1196)
  use `continue` without warning. A removed or renamed input can therefore
  disappear silently at runtime; the audit must catch that column loss before
  certification.

  The national certificate never widens. Area status remains `uncertified`:
  the certificate still covers the national dataset only (#685). TRACE
  carries the whole regional record, evidence included, separately from the
  national certification. An area run's execution receipt carries a summary
  of it (both model versions, the reason, the three lists and the
  limitations) and `record_sha256`, the digest of the whole record; check it
  with `verify_regional_certification`. A national receipt carries none: its
  `certificate_sha256` already digests the record. The flag remains UK only;
  an empty or invisible reason, a release that already covers the target
  model, or a missing regional release refuses.
  The regional core checks still apply. Re-certifying with
  `--drop-regional-release` removes the regional record, routes and artifact.

  For the Budget route, the audit of dense cut
  `microcosm-uk-2024-25-dense-20261019T000432Z-ee5c2dbe`, built with
  policyengine-uk 2.132.6 and policyengine-core 3.33.3, measured in #699:

  - **83 never-modelled columns**, and **no dropped column** under either
    2.147.2 or 2.151.0. The first version of this audit counted those 83 as
    dropped and refused the cut, even against its own build model.
  - **16 new defaults under 2.147.2:**
    `additional_residential_property_purchased`,
    `defined_benefit_pension_share`, `directly_held_shares`,
    `early_years_school_start_deferred`, `is_full_year_category_a_director`,
    `local_bus_uncapped_single_fare`, `non_residential_property_purchased`,
    `non_residential_property_secured_debt`,
    `other_residential_property_secured_debt`,
    `pension_annual_allowance_taxable_lump_sum_death_benefits`,
    `pension_contributions_via_salary_sacrifice_pre_2015`, `pip_dl_points`,
    `pip_m_points`, `salary_sacrifice_returned_to_income`,
    `unit_and_investment_trusts`, and `war_widows_pension_reported`.
  - **37 new defaults under 2.151.0:** those 16 and 21 more. The 21 include
    the gambling duty inputs, liquid and solid fuel consumption, and bonus
    sacrifice (`pension_contributions_via_bonus_sacrifice`), so area
    breakdowns of those measures use defaults on 2.151.0. Certification
    names every defaulted input in the limitations.
  - Another **123 inputs already defaulted under 2.132.6**. They are absent
    under both models, so they are not changes; the first version listed
    them too, giving 139 defaults under 2.147.2 and 160 under 2.151.0.

  Record the pre-fix VAT limitation shown above for this dense cut.

  After the receipt schema changes, refresh the Budget dashboard's vendored
  `tests/fixtures/w4/execution_receipt.v1.schema.json` from
  `src/policyengine/data/schemas/execution_receipt.v1.schema.json`.

Either way, certification checks that the regional release serves the pinned
model by its own build or compatibility claims (a `--qualified-pair-id` names
the primary release only), checks its core claims as for the primary release
(below), and HEAD-checks every artifact it carries.

### The core

The bundle has one core pin, `packages.policyengine-core`, shared by every
country. A certificate says how it covers it:

- **`core_binding: bundle_pin` (the default, no `--core-version`).** The
  certificate names no core and certifies whatever core the bundle pins, so
  the pin can move with another country without re-certifying this one.
  Certification checks the pin against each release's build-time core and
  core claims, and warns, without refusing, when the pin is outside them.
  `bundle.py check --include-tros --strict-tros` warns the same way when the
  pin later moves outside the claims. Receipts then certify the pin without
  the release's claim; the warning, the certificate and its TRO say so.
- **`core_binding: certified` (`--core-version`).** The certificate names the
  core (`certified_for_core_version`). Certification refuses a core that a
  release neither was built with nor claims, and the strict check refuses a
  pin that differs from the named core, so moving the core needs a
  re-certification first. A qualified exact pair always binds its core.

Use the default unless a release must not run on any other core.

### Re-certifying a routed bundle

Certification rewrites `data_releases.<country>` from the manifests it is
given. While the bundle routes regions (`regional_source_manifest_uri` is set),
a run without `--regional-manifest-uri` is refused; pass the current regional
release again (or its replacement), or `--drop-regional-release` to remove the
routing on purpose. The two flags cannot be combined.

An overlay may never shadow a certified dataset name, so certification removes
any `dataset_overlays.<country>` entry whose name the new release certifies. A
rollback to policyengine-uk-data with `--drop-regional-release`, for example,
removes the enhanced FRS overlays. `bundle.py check` refuses a bundle with an
overlay that shadows a certified name.

Removed overlays do not come back by themselves. Certification warns about
every dataset name that stops resolving. After a certification that stops
certifying a name that must stay loadable (rolling forward after a rollback,
or a ship-together run after a national-first one), re-add its overlay from
the previous bundle, as #685 did for `enhanced_frs_2024_25`, `frs_2024_25` and
their `_tiny` files.

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
weighted national totals only.

Before quoting any other figure from UK data in a PR, apply the UKDS output
rules: no unit-record values, no cells under 10 unweighted cases, no
differencing.

**Recorded exceptions (policyengine.py#685, October 2026).**

- **UC floor.** The Microcosm UK national cut
  `microcosm-uk-2024-25-national-20261019T083323Z-6cba5d71` became the default
  with benefit units at 0.897 of the floor's 6.7m benchmark; spend passed at
  0.959. The floor's benchmarks are not the figures Microcosm calibrates to
  (DWP Stat-Xplore's 6.2m households on Universal Credit in payment, and its own
  OBR spend line). Their definitions are to be settled when the UK data checks
  move to the data pipelines. Until then, a later Microcosm cut with the same
  gap needs the same explicit acceptance in its pull request, recorded here.
- **Comparison gates.** The metrics review and the scorecard replay measure a
  candidate against the previous certified pair, and a change of data line
  moves the totals by design, so they were not run for that switch; its pull
  request compares the two lines' weighted totals instead. The other gates,
  reform responsiveness included, were run on the national cut.
- **Budget-critical inputs: needs review.** `incapacity_benefit_reported` is
  missing from the Microcosm file but was a column of the enhanced FRS. The
  enhanced FRS column carries no values (Incapacity Benefit is closed), so
  both datasets give zero. Accepted by María Juaristi in #685.
- **Reform responsiveness: needs review.** The metrics tool's small-cell rule
  withholds a standard reform's figures, so the gate cannot recompute that
  reform's verdict. Accepted by María Juaristi in #685.

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
