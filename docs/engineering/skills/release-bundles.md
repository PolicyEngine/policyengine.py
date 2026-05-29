# Release Bundles

Use this skill when updating or reviewing a `policyengine.py` certified release
bundle for US, UK, or both countries.

## Core Rules

Open release-bundle implementation work on a fresh branch from current `main`.
If the checkout is dirty, use a clean worktree instead of overwriting unrelated
changes.

Do not hand-edit bundled release manifests for normal updates. Use the existing
single-country refresh script so model wheels, data artifacts, `pyproject.toml`,
and TRACE TROs move together:

```bash
python scripts/refresh_release_bundle.py --country us --model-version 1.715.2
python scripts/refresh_release_bundle.py --country uk --model-version 2.89.0
```

When a new data release is part of the certification, pass it explicitly:

```bash
python scripts/refresh_release_bundle.py --country us \
  --model-version 1.715.2 \
  --data-version 1.115.5
```

There is no supported `all` mode. If a user asks to update both US and UK, run
the single-country workflow for one country, inspect the result, then run it for
the other country.

UK data is private. Set `HUGGING_FACE_TOKEN` or `HF_TOKEN` before refreshing UK
bundles.

## Certification Order

For one country, first attempt full bundle certification with the existing
refresh script and a country data release manifest that supports the target
model by exact build version or matching `data_build_fingerprint`.

If full certification is not possible, the fallback is a country-data release
manifest assertion through `compatible_model_packages`. This fallback must be
created with the country data repo's release-manifest tooling, not by manually
editing the `policyengine.py` bundle. Tell the user clearly that this fallback is
only the data-release publisher claiming compatibility; there is currently no
validation or verification proving that the setup actually works.

For that fallback, use the country data repo's release-manifest builder or
publishing path with `additional_compatible_specifiers` set to the target model
specifier, for example `("==1.715.2",)` for US or `("==2.89.0",)` for UK.
Publish the updated country data release manifest before touching the `.py`
bundle.

After a country-data fallback manifest is published, rerun
`scripts/refresh_release_bundle.py` for that country and point at the updated
data release manifest revision if needed.

## Expected Files

A real `.py` refresh should normally change only:

- `src/policyengine/data/release_manifests/{country}.json`
- `src/policyengine/data/release_manifests/{country}.trace.tro.jsonld`
- `pyproject.toml`
- `uv.lock`, only if the lockfile is intentionally refreshed
- one Towncrier fragment under `changelog.d/`

Unexpected files are a reason to stop and inspect the diff.

## Testing

For release-bundle script or manifest changes, run:

```bash
POLICYENGINE_SKIP_COUNTRY_IMPORTS=1 uv run pytest --noconftest \
  tests/test_bundle_refresh.py

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
