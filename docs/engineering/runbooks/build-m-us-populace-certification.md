# Build M US Populace certification runbook

Fill-in-the-id runbook for certifying the next US Populace default
(`sparse-rmloss100` lineage: Build I → J → **M**) into the
`policyengine.py` bundle. It replays the exact steps that landed
[#470](https://github.com/PolicyEngine/policyengine.py/pull/470) (the Build J
certification), parameterized for the Build M release id. Read the
[data certification](../skills/data-certification.md) skill first for the
validation semantics; this file is the concrete checklist.

## When to use

A new US Populace `sparse-rmloss100` release has been published to
`policyengine/populace-us` and is ready to become the certified default. You
have the release id, the release manifest is reachable, and the model version
it was built with is known.

## Prerequisites

- A clean worktree branched from current `origin/main`
  (`git fetch origin && git checkout -b certify-us-buildm origin/main`).
- Network access: certification fetches the release manifest and PyPI wheel
  metadata and runs reachability `HEAD` checks against Hugging Face.
- `HUGGING_FACE_TOKEN` (or `HF_TOKEN`) exported — required to regenerate the
  UK TRO in the `--include-tros` step and to run the UK data-release fetch in
  the test suite. The US populace repo is public.

## Fill in these three values

```
BUILD_M_RELEASE_ID = populace-us-2024-buildm-sparse-rmloss100-<sha>-<timestamp>Z
MODEL_VERSION      = 1.764.6      # policyengine-us Build M was built with
CURRENT_RELEASE_ID = populace-us-2024-buildj-sparse-rmloss100-75d5add-20260710T094201Z
```

`CURRENT_RELEASE_ID` is the outgoing default (Build J) — the string you are
replacing in the pinned test constants. `MODEL_VERSION` stays `1.764.6` unless
Build M was built against a newer `policyengine-us`; if it was, see step 4.

## Step 1 — certify the release

```bash
python scripts/certify_data_release.py \
  --country us \
  --data-producer populace \
  --model-version "$MODEL_VERSION" \
  --manifest-uri "hf://dataset/policyengine/populace-us@$BUILD_M_RELEASE_ID/releases/$BUILD_M_RELEASE_ID/release_manifest.json"
```

This one command:

- rewrites `data_releases.us` in `src/policyengine/data/bundle/manifest.json`
  from the Build M release manifest (default dataset, per-artifact
  repo/revision/sha256 pins, certified artifact, certification block);
- runs `generate(check=False)`, which re-normalizes `manifest.json` and
  updates `pyproject.toml` **only if the model pins moved**;
- writes the changelog fragment
  `changelog.d/certify-us-$BUILD_M_RELEASE_ID.changed.md`.

## Step 2 — regenerate the US TRO sidecar

The certify step does not touch TRO sidecars. Rebind them so
`src/policyengine/data/bundle/us.trace.tro.jsonld` records the new
`manifest.json` sha256 (the `bundle_manifest` artifact hash is asserted by
`tests/test_certify_data_release.py::TestVendoredSidecarBinding`):

```bash
HUGGING_FACE_TOKEN="$HUGGING_FACE_TOKEN" python scripts/bundle.py generate --include-tros
```

Only `us.trace.tro.jsonld` should change (UK regenerates identically because
only US was certified). If UK cannot be reached, the run writes a *limited* UK
TRO — do not commit a degraded `uk.trace.tro.jsonld`; `git checkout` it and
rerun with a valid token.

## Step 3 — update the pinned test constants

Three files hard-code the certified release id. Replace `CURRENT_RELEASE_ID`
with `BUILD_M_RELEASE_ID` in each (this is the whole of #470's test diff):

- `tests/test_release_manifests.py` — `US_DATA_RELEASE_ID`.
- `tests/test_models.py` — the `us_latest.default_dataset_uri` `@<id>`
  assertion.
- `tests/test_us_regions.py` — the national `dataset_path` `@<id>` assertion.

## Step 4 — only if the model version changed

Build J → M on the same `policyengine-us` needs nothing here (this is the
common case; #470 left `pyproject.toml` and the snapshots untouched). If Build
M was built against a newer `policyengine-us`:

- `pyproject.toml` model pins are already rewritten by step 1's `generate`;
  commit them.
- Update `US_MODEL_VERSION` and `US_BUILT_WITH_MODEL_VERSION` in
  `tests/test_release_manifests.py`.
- Refresh the household snapshots:
  `PE_UPDATE_SNAPSHOTS=1 pytest tests/test_household_calculator_snapshot.py`
  and commit `tests/fixtures/household_calculator_snapshots/`.

## Step 5 — verify the local-area overlay survived

Certification rewrites only `data_releases.us`, so the non-default
`dataset_overlays.us.populace_us_2024_acs_local` entry (see
[Non-default dataset overlays](../../release-bundles.md#non-default-dataset-overlays))
must still be present and resolvable. No manual re-add is needed — confirm it:

```bash
python -c "import json; b=json.load(open('src/policyengine/data/bundle/manifest.json')); assert 'populace_us_2024_acs_local' in b['dataset_overlays']['us'], 'overlay lost'; print('overlay preserved')"
pytest tests/test_release_manifests.py -k "local_area or DatasetOverlays" -q
```

## Step 6 — check, format, lint, test

```bash
python scripts/bundle.py check          # must exit 0
make format
make lint
make test                               # needs HUGGING_FACE_TOKEN for UK
```

## Step 7 — commit exactly these files

Matches #470's file set (add `pyproject.toml` and the snapshot dir only when
step 4 applied):

- `src/policyengine/data/bundle/manifest.json`
- `src/policyengine/data/bundle/us.trace.tro.jsonld`
- `changelog.d/certify-us-$BUILD_M_RELEASE_ID.changed.md`
- `tests/test_release_manifests.py`
- `tests/test_models.py`
- `tests/test_us_regions.py`

## Step 8 — open the PR

Follow [github-prs](../skills/github-prs.md): open/find the issue, put
`Fixes #ISSUE` first, push to the canonical repo, and open a **draft** PR. The
certify step already wrote the changelog fragment, so the changelog check
passes.

## Verified against #470

Every step above is checked against the merged Build J certification (#470),
whose diff was exactly: `manifest.json`, `us.trace.tro.jsonld`, the three test
constants, and the auto-written changelog fragment — with `pyproject.toml` and
the snapshots untouched because `policyengine-us` stayed `1.764.6`.
