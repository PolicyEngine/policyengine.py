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

There is no intermediate bundle repo. The vendored country manifest at
`src/policyengine/data/release_manifests/{country}.json` is derived directly
from the data release manifest.

## Certifying a release

Open the work on a fresh branch from current `main` (use a clean worktree if
the checkout is dirty).

```bash
python scripts/certify_data_release.py --country us \
  --manifest-uri "hf://dataset/policyengine/populace-us@<tag>/releases/<tag>/release_manifest.json"
```

The script fetches and validates the manifest (every artifact must carry a
revision pin; the certified dataset must be reachable), writes the vendored
country manifest, exact-pins the country model package and raises the core
floor in `pyproject.toml`, regenerates the TRACE TRO sidecar, and writes a
Towncrier changelog fragment.

Private data (UK) requires `HUGGING_FACE_TOKEN` or `HF_TOKEN`.

After running:

- `uv lock` if pins moved, then `uv sync --all-extras`,
- run the full test suite — snapshot drift from a model bump is refreshed
  with `PE_UPDATE_SNAPSHOTS=1 pytest tests/test_household_calculator_snapshot.py`,
- commit the manifest, TRO, `pyproject.toml`, `uv.lock`, and fragment
  together.

A certification PR should normally change only:

- `src/policyengine/data/release_manifests/{country}.json` (+ `.trace.tro.jsonld`)
- `pyproject.toml` / `uv.lock`
- one Towncrier fragment under `changelog.d/`
- test constants/snapshots that pin certified versions

## Validation semantics

Hard failures (certification refuses): missing national default dataset,
default dataset absent from artifacts, any artifact without a revision pin,
unreachable certified dataset, unknown country.

Warnings (recorded, not blocking): artifacts without sha256, certifying a
model version outside the manifest's `compatible_model_packages`. The
warning case is legitimate — the manifest's compatibility list is the data
publisher's claim, while certification is this repo's claim, arbitrated by
the test suite.

## Legacy paths

Countries whose current data release predates release manifests (the UK
enhanced FRS) are refreshed with the legacy single-country tool until their
next release certifies through a manifest:

```bash
python scripts/refresh_release_bundle.py --country uk --model-version 2.89.0
```

Do not hand-edit vendored country manifests for normal updates.

The retired `policyengine-bundles` flow (candidates → generated bundle →
archive import) is preserved read-only in that repo's history; bundles
4.15.x–4.16.x remain the historical record of earlier certifications.
