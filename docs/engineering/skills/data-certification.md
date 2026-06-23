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
(for example Populace-US `us_source_coverage.json`), unknown country.

Certification gate: the model version must either exactly match the
build-time model (`compatibility_basis: built_with_model_package`) or be
covered by the publisher's `compatible_model_packages` claim
(`compatibility_basis: compatible_model_packages`, recorded with a
warning — the publisher's claim is made good only by this repo's test
suite passing on the pinned pair). Neither basis means certification is
refused: a new data build or a published compatibility claim is required.

Warnings (recorded, not blocking): artifacts without sha256, and the
publisher-claim basis above.

## Legacy paths

Do not hand-edit bundle data releases for normal updates. Countries whose
current data release predates release manifests need a data-producer strategy
before they can be updated through this path.

The retired `policyengine-bundles` flow (candidates → generated bundle →
archive import) is preserved read-only in that repo's history; bundles
4.15.x–4.16.x remain the historical record of earlier certifications.
