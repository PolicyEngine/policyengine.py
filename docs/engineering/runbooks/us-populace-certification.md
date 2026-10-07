# US Populace certification runbook

Use this runbook to certify a new national US Populace release together with
the shared ACS-local release used for state and congressional-district
simulations. Read the [data certification](../skills/data-certification.md)
skill first for validation semantics.

## When to use

Both release manifests have been published to `policyengine/populace-us`, and
the model version used by the national release is known. The national release
will remain the default dataset; the local-area release will remain
non-default and be selected only for supported regional runs.

## Prerequisites

- A clean worktree branched from current `origin/main`.
- Network access: certification fetches the release manifest and PyPI wheel
  metadata and runs reachability `HEAD` checks against Hugging Face.
- `HUGGING_FACE_TOKEN` (or `HF_TOKEN`) exported — required to regenerate the
  UK TRO in the `--include-tros` step and to run the UK data-release fetch in
  the test suite. The US populace repo is public.

## Step 1 — identify the releases

Set values from the two published release manifests rather than copying an
older certification:

```
NATIONAL_RELEASE_ID = populace-us-2024-<national-build>-<sha>-<timestamp>Z
LOCAL_AREA_RELEASE_ID = populace-us-2024-<local-build>-<sha>-<timestamp>Z
MODEL_VERSION = <policyengine-us version declared by the national release>
```

The local-area manifest must declare `dataset_role: non_default_local_area`,
`is_default: false`, no default datasets, and exactly one pinned H5 microdata
artifact.

## Step 2 — certify both releases

```bash
python scripts/bundle.py certify-data \
  --country us \
  --data-producer populace \
  --model-version "$MODEL_VERSION" \
  --manifest-uri "hf://dataset/policyengine/populace-us@$NATIONAL_RELEASE_ID/releases/$NATIONAL_RELEASE_ID/release_manifest.json" \
  --regional-manifest-uri "hf://dataset/policyengine/populace-us@$LOCAL_AREA_RELEASE_ID/releases/$LOCAL_AREA_RELEASE_ID/release_manifest.json"
```

This one command:

- rewrites `data_releases.us` in `src/policyengine/data/bundle/manifest.json`
  from the national release manifest (default dataset, per-artifact
  repo/revision/sha256 pins, certified artifact, certification block);
- runs `generate(check=False)`, which re-normalizes `manifest.json` and
  updates `pyproject.toml` **only if the model pins moved**;
- writes the changelog fragment
  `changelog.d/certify-us-$NATIONAL_RELEASE_ID.changed.md`.

## Step 3 — regenerate TRACE sidecars

The certify step does not touch TRACE sidecars. Regenerate them so they record
the new bundle-manifest SHA-256:

```bash
HUGGING_FACE_TOKEN="$HUGGING_FACE_TOKEN" python scripts/bundle.py generate --include-tros
```

Both country sidecars contain the bundle-manifest hash, so both may change when
the bundle changes. If UK cannot be reached, the run writes a *limited* UK
sidecar; do not commit that degraded output.

## Step 4 — update pinned expectations

Update tests that intentionally pin the outgoing national release, local-area
release, model version, or artifact hashes. Derive every replacement from the
new manifests; do not copy identifiers from this runbook.

If the model version changed, refresh the household snapshots with:

```bash
PE_UPDATE_SNAPSHOTS=1 pytest tests/test_household_calculator_snapshot.py
```

## Step 5 — certify and verify the local-area release

The certification command passes the immutable ACS-local release manifest with
`--regional-manifest-uri`. Confirm all of the following:

- `default_dataset` remains the national Populace dataset;
- the local-area artifact appears in `data_releases.us.datasets` with its
  repository type, immutable revision, and SHA-256;
- `region_datasets.national` selects the national artifact;
- `region_datasets.state` and `region_datasets.congressional_district` select
  the shared local-area artifact;
- no derived `states/*.h5` or `districts/*.h5` artifacts are runtime inputs.

```bash
pytest tests/test_certify_data_release.py \
  tests/test_release_manifests.py \
  tests/test_us_regions.py \
  -q
```

## Step 6 — check, format, lint, test

```bash
python scripts/bundle.py check          # must exit 0
make format
make lint
make test                               # needs HUGGING_FACE_TOKEN for UK
```

## Step 7 — inspect and commit the generated changes

The expected diff normally includes the bundle manifest, TRACE sidecars, one
Towncrier fragment, and pinned test expectations. Include package pins and
snapshots only when the certified model version changed. Investigate any other
generated difference before committing it.

## Step 8 — open the PR

Follow [github-prs](../skills/github-prs.md): open/find the issue, put
`Fixes #ISSUE` first, push to the canonical repo, and open a **draft** PR. The
certify step already wrote the changelog fragment, so the changelog check
passes.
