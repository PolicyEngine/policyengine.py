# Release Bundles

Use this skill when updating or reviewing a `policyengine.py` certified release
bundle for US, UK, or both countries.

## Core Rule

Do not hand-edit bundled release manifests for normal updates. Use the refresh
tooling so model wheels, data artifacts, pyproject pins, and TRACE TROs move
together.

`policyengine.py` may certify a country data artifact for a country model only
when one of these is true:

- the data release was built with the exact target model version
- the target model has the same `data_build_fingerprint` as the model used to
  build the data release

If neither is true, stop and require a new country `*-data` release before
changing the `policyengine.py` bundle.

## Branch And Scope

Start bundle-harness or bundle-refresh implementation work on a new branch from
current `main`:

```bash
git switch main
git pull
git switch -c add-release-bundle-ai-harness
```

If the current checkout is dirty, create a clean worktree instead of stashing or
overwriting unrelated changes.

## Refresh Commands

Refresh one country using latest model version discovery:

```bash
python scripts/refresh_release_bundles.py --country us
python scripts/refresh_release_bundles.py --country uk
```

Refresh one country with an explicit model version:

```bash
python scripts/refresh_release_bundles.py --country us --model-version 1.715.2
python scripts/refresh_release_bundles.py --country uk --model-version 2.89.0
```

Refresh both country bundle segments as one preflighted operation:

```bash
python scripts/refresh_release_bundles.py --country all
```

Use explicit per-country versions in `all` mode when needed:

```bash
python scripts/refresh_release_bundles.py --country all \
  --us-model-version 1.715.2 \
  --uk-model-version 2.89.0
```

The package CLI exposes the same workflow:

```bash
policyengine refresh-release-bundles --country all
```

UK data is private; set `HUGGING_FACE_TOKEN` or `HF_TOKEN` before refreshing UK
bundles.

## Expected Files

A real refresh should normally change only:

- `src/policyengine/data/release_manifests/{country}.json`
- `src/policyengine/data/release_manifests/{country}.trace.tro.jsonld`
- `pyproject.toml`
- `uv.lock`, only if the lockfile is intentionally refreshed
- one Towncrier fragment under `changelog.d/`

Unexpected changes are a reason to stop and inspect the diff.

## Testing

For release-bundle tooling changes, run the focused unit tests without the
shared country-model fixtures:

```bash
POLICYENGINE_SKIP_COUNTRY_IMPORTS=1 uv run pytest --noconftest \
  tests/test_bundle_update.py \
  tests/test_bundle_refresh.py
```

For release-manifest or TRACE behavior changes, also run:

```bash
uv run pytest \
  tests/test_release_manifests.py \
  tests/test_trace_tro.py
```

For a real data artifact change, also run and review snapshot diffs:

```bash
PE_UPDATE_SNAPSHOTS=1 uv run pytest tests/test_household_calculator_snapshot.py
```

Before opening a PR, run the standard repository checks from
`repository-guidance.md`.
