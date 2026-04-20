---
title: Microdata publishing (design sketch)
---

# Microdata publishing — design sketch

> **Status:** design sketch, not yet accepted. Written to capture the
> shape of a "from scratch" approach to publishing PolicyEngine
> microdata. [Release bundles](release-bundles.md) remains the
> authoritative doc for what ships today.

Today's stack layers PyPI (country models), PyPI _and_ Hugging Face
(country data), the `policyengine-{us,uk}-data` GitHub repos (build
code), and `policyengine.py` release manifests (sha256 pins) on top
of each other. Refreshing any link in that chain — "bump us-data to
1.78.2" — touches six files across three repos and mixes **identity**
("what dataset is this?") with **distribution** ("where do I download
it?") and **discovery** ("what's the current recommended version?").

This doc sketches what we'd build if we started over, with four
goals:

1. **Replicability**: a reviewer two years from now can reconstruct
   the exact microdata a paper used from the results file alone.
2. **Content-addressed identity**: changing the build produces a new
   ID; old IDs remain resolvable forever. Retagging is impossible.
3. **Cheap schema introspection**: an agent learns the column set
   without downloading a 100 MB file.
4. **Trivial release refresh**: bumping the recommended dataset is
   one object-store write, not a six-file coordinated edit.

## Three concepts, cleanly separated

| Concept | Today | Proposed |
|---|---|---|
| **Identity** (what is this?) | HF tag `1.73.0` (mutable), PyPI `1.73.0` (immutable), sha256 inside `policyengine.py` manifest | `build_id` = sha256 of inputs, stored in the filename |
| **Distribution** (where do I get it?) | HF model-repo `resolve/{tag}/{path}`, PyPI wheel URL, sometimes GitHub Releases | Plain object-store path: `s3://policyengine-data/{country}/{build_id}.parquet` |
| **Discovery** (what's current?) | Implicit in `policyengine.py`'s bundled manifest; must cut a new `.py` release to change | `channels/{country}/{name}.json` pointing at a `build_id`; one PUT to update |

## Layer 1 — Content-addressed artifact store

A flat object-store bucket with **immutable, content-addressed** objects.

```
s3://policyengine-data/
  us/
    {build_id}/
      enhanced_cps_2024.parquet     # the microdata (100 MB)
      manifest.json                 # 2 KB — schema, inputs, digests
      results.json                  # optional: validation aggregates
  uk/
    {build_id}/
      enhanced_frs_2023_24.parquet
      manifest.json
  channels/
    us/
      latest.json                   # { "build_id": "…" }
      stable.json
      lts-2025q2.json
    uk/
      …
```

`build_id` is the **sha256 of the inputs**, not the output — so two
different orgs rebuilding from the same recipe get the same hash
without ever exchanging files. Inputs include:

- data vintage identifier (e.g. CPS ASEC 2024)
- country model package (name + version + wheel sha256)
- calibration script (git sha of `policyengine-us-data`)
- explicit parameter overrides (if any)
- random seed
- Python interpreter + transitive lockfile digest (for bit-level
  reproducibility; optional for v1)

`manifest.json` carries the full input list plus a schema block:

```json
{
  "schema_version": 2,
  "country": "us",
  "build_id": "sha256:…",
  "inputs": {
    "data_vintage": "cps_asec_2024",
    "model_package": {"name": "policyengine-us", "version": "1.653.3", "sha256": "…"},
    "calibration_sha": "2141ee45…",
    "parameter_overrides": {},
    "seed": 42,
    "python": "3.12.8",
    "lockfile_digest": "sha256:…"
  },
  "outputs": {
    "enhanced_cps_2024": {
      "path": "enhanced_cps_2024.parquet",
      "sha256": "4e92b340c3ea…",
      "size_bytes": 111427742,
      "rows": {"person": 192817, "household": 41314, "tax_unit": …},
      "weight_column": "household_weight",
      "schema": [{"name": "age", "dtype": "int32", "entity": "person"}, …]
    }
  },
  "built_at": "2026-04-10T12:00:00Z",
  "built_by": "ci@policyengine-us-data#7f64..."
}
```

Consequences:

- **Schema lookup is cheap.** Listing `channels/us/stable.json` +
  fetching one 2 KB `manifest.json` is enough to learn the column
  set, dtypes, and entity mapping. No 100 MB download.
- **Retagging is impossible.** `build_id` is a content hash; a
  "version 1.73.0 gets silently rebuilt" situation can't occur.
- **Mirrors are trivial.** Any org can serve the same bytes from
  their own CDN or S3; the `build_id` verifies.

## Layer 2 — Release channels

Channels are **tiny JSON pointers** that name a `build_id`:

```json
# s3://policyengine-data/channels/us/stable.json
{
  "channel": "stable",
  "country": "us",
  "build_id": "sha256:4e92b340c3ea…",
  "published_at": "2026-04-20T14:30:00Z",
  "channel_history_sha": "…"
}
```

Channels we'd likely run:

- `latest` — bleeding edge; updated on every us-data merge to main
- `stable` — human-promoted after validation; consumer default
- `lts-{quarter}` — pinned for long-running analyses

Updating a channel = one S3 PUT. No code change, no PyPI release, no
`.py` release. The `pe.py` bundled manifest points at a channel (not
a specific `build_id`) for the default consumer path; analyses that
need reproducibility pin a specific `build_id`.

## Layer 3 — Builder CLI

One command in `policyengine-us-data` (and matching in `-uk-data`):

```bash
policyengine-data build \
    --country us \
    --vintage cps_asec_2024 \
    --model policyengine-us==1.653.3 \
    --calibration enhanced \
    --output-bucket s3://policyengine-data/us/
```

The builder:
1. Resolves inputs, computes `build_id` = sha256(canonical inputs).
2. Checks if `s3://policyengine-data/us/{build_id}/` already exists.
   If so, idempotent: exits 0 without rebuilding.
3. Otherwise runs the pipeline deterministically (fixed seed, fixed
   model version, fixed interpreter).
4. Writes `{build_id}/enhanced_cps_2024.parquet` + `manifest.json`
   atomically.
5. Optionally promotes to a channel (`--promote latest`).

Deterministic output + content-addressed storage means repeated
runs of identical inputs never collide or duplicate.

## Layer 4 — Consumer resolver in `policyengine.py`

The bundled consumer manifest points at a **channel**, not a
`build_id`:

```json
# src/policyengine/data/release_manifests/us.json (proposed v2)
{
  "schema_version": 2,
  "country": "us",
  "model_package": {"name": "policyengine-us", "version": "1.653.3", "sha256": "…"},
  "data_channel": "stable",
  "data_channel_url": "https://data.policyengine.org/channels/us/stable.json"
}
```

The `pe.us.ensure_datasets(channel="stable")` resolver:
1. Fetches `channels/us/stable.json` → `build_id`.
2. Fetches `{build_id}/manifest.json` → artifact list + sha256s.
3. Downloads artifacts, verifying sha256 against the manifest.
4. Caches locally keyed by `build_id` (not channel, so cache is
   content-addressed too).

`ensure_datasets(build_id="sha256:…")` pins explicitly for
reproducibility-critical analyses.

## What this replaces

| Current mechanism | Replaced by |
|---|---|
| HF model-repo tags (`policyengine/policyengine-us-data`) | Content-addressed object storage |
| PyPI `policyengine-us-data` (for version string only) | `build_id` is the identifier |
| Manual sha256 juggling in `policyengine.py` release manifest | Channel JSON → manifest chain |
| `scripts/refresh_release_bundle.py` | Simplified to "fetch channel, validate, commit" |
| "Is the model too new for this data?" (manual reasoning) | CI diffs current model digest against `inputs.model_package.sha256` on the active channel |

## What stays the same

- **Country data repos still own construction.** `policyengine-us-data`
  still calls the country model, still does calibration, still
  gates private source data. The boundary from
  [release-bundles.md](release-bundles.md) stays intact.
- **TRACE TRO sidecars still ship with `policyengine.py`.** The
  `{country}.trace.tro.jsonld` derivation gets shorter (everything
  comes from the channel manifest), but the output is the same
  JSON-LD with the same `trov:` / `pe:` vocabulary.
- **UK privacy boundary** is preserved. The object-store bucket can
  be gated (read-only to authenticated org members) without changing
  the channel/manifest surface; consumer code sees the same
  404-with-auth-required shape as today.

## Migration cost

Rough estimate (1 engineer + an agent):

- **Week 1**: ship the channel/manifest spec; stand up the bucket;
  port one US build through the new pipeline end-to-end.
- **Week 2**: migrate `pe.us.ensure_datasets` to the new resolver;
  ship a fallback to the legacy HF path for 2-3 releases; port the
  TRACE TRO generator.
- **Week 3**: UK. Then retire the legacy HF path.

## Why I'd bother

Three questions that are hard today become one-liners:

1. **"What exactly was the baseline data used for policy 94589?"**
   Read the results file → `build_id` → manifest → rebuild if you
   want. No `git blame` on `policyengine.py`'s release manifest
   history.
2. **"Is our current data out of date?"**
   CI job diffs `inputs.model_package.sha256` on the active channel
   against the current model wheel; posts a PR comment or opens a
   rebuild PR automatically.
3. **"Can I reproduce a 2024 paper's numbers on current data?"**
   `pe.us.ensure_datasets(build_id="sha256:…")`. Always. Even if
   us-data the repo is renamed, deprecated, or moved.

## What it doesn't solve

- **Model drift still requires rebuilds** — only the mechanism
  improves. `policyengine-us 1.653.3` and `policyengine-us 1.700.0`
  will still produce different enhanced CPS files.
- **Calibration is still an open research problem**, independent of
  storage.
- **Cost**. Object-store + egress bandwidth is small money but not
  zero.

## Open questions

- Single bucket shared with `policyengine-core` + dashboards, or
  separate per-country? (Lean: shared, one bucket per namespace.)
- GCS vs S3? (Lean: GCS since the data-build pipelines already run
  on GCP.)
- Parquet vs HDF5 for the payload format? (Lean: parquet for new
  builds; legacy HDF5 for the existing Enhanced CPS until all
  consumers migrate.)
- Channel-history signing — do we want a transparency log so
  `stable` can't be silently retargeted? (Lean: yes, v2.)
