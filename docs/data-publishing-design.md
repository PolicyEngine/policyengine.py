---
title: Storage substrate for microdata artifacts (design sketch)
---

# Storage substrate for microdata artifacts — design sketch

> **Status.** Design sketch, not accepted. Two independent reviews
> (general-purpose stress test + codex review) reshaped scope.
> [Release bundles](release-bundles.md) remains the authoritative
> doc for the user-facing certification + citation surface, and
> this sketch **does not** propose replacing that surface.

## Scope (read this first)

Codex's review caught an important conflation in an earlier draft:
there are two separable systems in play, and the earlier sketch
quietly merged them.

| System | Concern | Authoritative home |
|---|---|---|
| **Certified release bundle** | What `policyengine.py 4.x` users get when they cite a paper | [release-bundles.md](release-bundles.md) — unchanged |
| **Storage substrate** | Where the artifact bytes actually live, how they're fetched, how stale caches invalidate | This doc |

The earlier draft described a single unified system and pitched it
as "replace PyPI + HF + GitHub + release manifests." That was
overreach. Release bundles are a **scientific citation surface**
(with certification, staged promotion, compatibility rules, and
formal replicability guarantees that a reviewer 5 years from now
can audit). A storage substrate is an operational concern
underneath. Conflating them means the certification story weakens
when it should strengthen, and a separate certification layer
reappears on top within 2 years (codex: 60–85% probability).

**This doc is scoped to the storage layer only.** Release bundles
continue to own certification, citation, promotion, and the
reproducibility guarantee. The storage substrate is a cleaner
cache/mirror/distribution primitive *beneath* release bundles.

## Motivating pains (and what's actually on the critical path)

Two concrete frictions pushed this sketch forward:

1. **HF model-vs-dataset repo confusion** (hit in #310): the refresh
   helper assumed `huggingface.co/datasets/...` paths; the actual
   microdata lives at `huggingface.co/...` (model-type repo).
2. **"Is our data out of date?"** is a manual audit today because
   no automated job compares the current country-model sha256
   against what the certified artifact was built with.

**Neither requires the sketch below.** A one-time HF repo-type
migration (or a smarter URL resolver, already done in
`bundle._hf_dataset_sha256`) fixes #1. A ~50-line CI job diffing the
bundled release manifest's `certified_for_model_version` against
`importlib.metadata.version("policyengine-us")` fixes #2. Both are
~days of work, not weeks.

The value proposition below is architectural, not bug-fix.

## What the storage substrate would provide

Four concrete properties the current HF + PyPI + GitHub Releases
pairing does not:

1. **Cheap schema introspection.** A 2 KB sidecar manifest per
   artifact records the column set, dtypes, entity mapping, weight
   column, and row counts — so agents and tooling can learn the
   shape of a dataset without streaming 100 MB.
2. **Content-addressed cache keys.** Local caches keyed on the
   artifact's output-byte sha256 (not a mutable HF tag) can't go
   stale after a retag. `pe.us.ensure_datasets(...)` always returns
   the bytes the release bundle pinned, or nothing.
3. **Operational channels.** Small JSON pointers at
   `channels/{country}/{name}.json` let CI dashboards and bleeding-
   edge developers subscribe to updates without cutting a new
   `policyengine.py` release. **These are operational aliases, not
   a scientific citation surface** — release bundles remain the
   thing papers cite.
4. **Simpler refresh mechanics.** `refresh_release_bundle(country,
   ...)` becomes "fetch channel → read manifest → write the
   certified release manifest" with no sha256 juggling.

Notably absent from that list compared to earlier drafts: **no
claim of org-independent build identity**, **no claim of
retagging-impossible certification**, **no claim of replacing the
release bundle**. Those were overreach.

## Identity: output-hash, not input-hash

The earlier draft framed the primary identifier as
`build_id = sha256(inputs)` — "two orgs rebuilding from the same
recipe get the same ID without exchanging files." Codex's review is
correct that this is weaker than it sounded:

- `data_vintage: "cps_asec_2024"` is a **label**, not a raw-bytes
  hash. Two orgs honestly using "CPS ASEC 2024" can have different
  source bytes. The current [release-bundles.md](release-bundles.md)
  schema already records raw-input hashes — a regression from that
  would be real.
- `built_at` / `built_by` fields in the manifest break bitwise
  identity across org rebuilds even when the payload is identical.
- Genuine bit-level determinism across orgs (libc, CPU microcode,
  torch seeds, dict iteration, pandas groupby order) is a
  multi-month project, not a v1 flag.

The revised proposal: the primary identifier is
**`artifact_sha256` = sha256 of the output bytes**. Input digest is
recorded *in* the manifest as a derived queryable field
(`inputs.composite_digest`), not the primary key. That matches how
OCI/Nix work in the parts that actually deliver: content-addressed
at the *output*, with provenance recorded alongside.

Storage layout becomes:

```
s3://policyengine-data/
  {country}/
    {artifact_sha256_prefix}/{artifact_sha256}.parquet
    {artifact_sha256_prefix}/{artifact_sha256}.manifest.json
  channels/
    {country}/
      latest.json         # { "artifact_sha256": "…" }
      next.json           # staging; feeds into release-bundles promotion
```

The `channels/` tree intentionally drops `stable` and `lts-*` —
those carry semantics ("what should researchers treat as
authoritative?") that belong to the release bundle, not the storage
substrate. At the storage layer we only need "operationally newest"
(`latest`) and "nominated-for-certification" (`next`).

## Channel semantics (deliberately narrow)

| Channel | Purpose | Updated by |
|---|---|---|
| `latest` | Output of the most recent successful CI build. May be broken, uncalibrated, experimental. | CI on every `policyengine-{country}-data` main-branch merge |
| `next` | Staging artifact that has passed validation and is nominated for the next release bundle. | Manual promotion from `latest` after review |

"Certified" / "stable" stay on the release-bundle side. This
avoids the codex failure mode where "stable" silently means four
different things to four different audiences.

## The release-bundle boundary (what doesn't change)

[release-bundles.md](release-bundles.md) remains authoritative:

- The certification process (who signs off, what validations, what
  compatibility checks) — unchanged.
- `src/policyengine/data/release_manifests/{country}.json` remains
  the shipped record of what a given `policyengine.py` release
  guarantees.
- The staged `provisional → certified → retired` lifecycle —
  unchanged.
- `*.trace.tro.jsonld` sidecars — unchanged (shorter to build
  because inputs are already in the storage manifest, but the
  emitted TRO has the same shape and `trov:` / `pe:` fields).
- The replicability guarantee wording — unchanged.

The storage substrate is an *implementation detail* that the
certification process pulls from. When a release bundle is
certified, it promotes an artifact from `channels/next` to a
concrete `artifact_sha256` pin in the country release manifest.
After that, the release manifest is what papers cite; the storage
channel is just the cache.

## Consumer resolver (what `pe.py` changes)

Minimal. The existing `pe.us.ensure_datasets` takes a URI today:

```python
pe.us.ensure_datasets(
    datasets=["hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"],
    years=[2026],
)
```

Under the substrate, the URI scheme gains a new prefix:

```python
# The release manifest pins a specific artifact:
pe.us.ensure_datasets(
    datasets=["pe-data://us/enhanced_cps_2024@sha256:4e92b340…"],
    years=[2026],
)

# A developer asking for operational newest:
pe.us.ensure_datasets(
    datasets=["pe-data://us/enhanced_cps_2024@latest"],  # resolves via channel
    years=[2026],
)
```

The HF scheme stays supported indefinitely for backward compat —
the substrate is additive. Local cache keyed on `artifact_sha256`.

## Unresolved risks (carried forward from prior reviews)

### UK Data Service audit trail

Today HF logs who pulls a private-gated tag via auth token. Under
the sketch, auth happens at the bucket but identity resolves
through two hops (channel JSON → manifest + payload), and object-
store access logs record GETs against opaque `artifact_sha256`
paths, not "user X downloaded UK enhanced FRS derived from
FRS 2023-24".

**Decision needed**: gate the *manifest* fetch, not just the
payload, so the resolver hit is auditable; maintain a per-country
access log keyed on manifest content. Without this, UK support
regresses vs. today.

### Silent-promote attack

An adversary with bucket write access rewrites
`channels/us/latest.json` to point at an artifact with a manifest
that has a quietly wrong `inputs.composite_digest`. sha256
verification only protects payload-vs-manifest integrity; it
doesn't authenticate the channel pointer itself. Today's PyPI/HF
platforms have account auth auditing on tag pushes that the
sketch does not.

**Decision needed**: before any *release-bundle* certification can
pull from a channel, the channel JSON must be signed with a key
pinned in `pe.py`. Channels can stay unsigned for the
operational-`latest` use case (the certification step verifies),
but the nomination → certification boundary must validate a
signature.

### Non-deterministic builds (storage-layer version)

With output-hash identity (not input-hash), two CI runs from the
same inputs producing slightly different bytes produce two
different `artifact_sha256` values. They don't collide. This is
actually cleaner than the recipe-addressed framing: the storage
layer doesn't need to promise determinism. The release-bundle
certification step is where determinism matters, and it's already
responsible for picking one specific artifact to pin.

### Licence revocation vs "immutable forever"

The earlier sketch called storage "immutable forever." In practice,
Census / ONS / DWP can yank redistribution rights, and we must be
able to respond. The storage substrate must support tombstoning:
an `artifact_sha256` resolves to a manifest with
`status: "revoked"` and no payload. Release bundles that pinned
the revoked artifact get marked as "unreproducible: licence
revoked" in the certification registry (a new release-bundle
concept, not this sketch's).

### Cross-cloud replication

Payloads mirror trivially — sha256 verifies. Channels don't (a
single authoritative URL). An EU partner wanting their own mirror
runs their own channel namespace. The substrate should not promise
one-click cross-cloud channels; it should promise one-click
payload mirrors and make channel namespacing explicit.

## Relationship to `release-bundles.md` (and what stays load-bearing)

The old-design's central claim was "this could replace release
bundles." It cannot, and it shouldn't try. Release bundles carry
the certification contract with external stakeholders:

- The UK Data Service licence negotiation hangs off the fact that
  `policyengine.py` releases are the thing that's audited,
  reviewed, and approved. The storage substrate changes the
  *mechanism* of how bytes reach users, not the *contract* about
  what's been certified.
- Academic replication reviewers need something at citation time
  that is `vN.M.P`-shaped, not `sha256:…`-shaped. Release bundle
  versions fill that role.
- "Is this the PolicyEngine release?" has a legal/regulatory
  answer that release bundles track. The storage substrate does
  not attempt that.

**The load-bearing sentence of this sketch**: *"When a release
bundle is certified, it promotes an artifact from `channels/next`
to a concrete `artifact_sha256` pin in the country release
manifest. After that, the release manifest is what papers cite;
the storage channel is just the cache."*

## What this fixes that today's HF/PyPI pairing doesn't

Narrow list, honestly scoped:

| Pain | Today | Under substrate |
|---|---|---|
| "Did a retag silently change the artifact?" | Possible, HF tags are mutable | Impossible: cache keyed on output sha256 |
| "What's the schema of `enhanced_cps_2024`?" | Download 100 MB, open with h5py | Fetch 2 KB manifest |
| "Where's model-vs-dataset repo type?" | Tripped up `bundle._hf_dataset_sha256` (#310) | No such distinction |
| "How does an EU partner mirror the payload bytes?" | Coordinate with HF, PyPI, release cadence | Re-upload bytes to their bucket; sha256 verifies |

What it doesn't fix, which the earlier draft overclaimed:
- "Bump stable to the newest data" — that's a release-bundle
  certification decision and stays manual.
- "Reproduce a paper from 5 years ago" — depends on the release
  bundle being preserved, which is a release-bundle concern.
- "Two orgs can independently produce the same build" — bit-level
  determinism is out of scope; the substrate just doesn't pretend
  otherwise.

## Migration cost (realistic)

Revised after the stress tests:

| Work item | Estimate |
|---|---|
| Bucket + manifest schema + one US build end-to-end | 1–2 weeks |
| Consumer resolver in `pe.py` (`pe-data://` URI scheme, cache, sha256 verify) | 1 week |
| UK gating with auditable manifest hits | 1–2 weeks |
| Channel signing + trust-root rollover story (for `next` → certification) | 2–3 weeks |
| Tombstone + release-bundle "unreproducible" state | 1–2 weeks |
| Retire the legacy HF resolver path (after 2–3 `pe.py` releases) | 1 week |

**Total: 7–11 engineer-weeks.** With two engineers + agents running
in parallel on independent tracks, ~5–7 calendar weeks is
realistic. Not a v4.x stretch; candidate for v5 if pursued at all.

## Whether to pursue

Honest read from both stress tests combined:

- **Keep the storage substrate idea.** Output-hash-addressed
  storage + a schema-sidecar manifest + a `pe-data://` URI scheme
  is a real improvement over HF for our use case, independent of
  everything else.
- **Drop the "replace release bundles" framing entirely.** That
  was the codex review's main correction, and it holds.
- **Don't build it to fix #310 or "is our data stale?"** Both have
  cheap, targeted fixes already within reach.
- **If the UK Data Service relationship is going to get stricter**
  (an external trigger, not an internal one), revisit. A
  substrate with first-class audit is defensible in a way that the
  current HF private-repo setup is not.

## Open questions (narrowed)

- Object store: GCS or S3? (Lean: GCS — build pipelines already
  run on GCP.)
- Payload format for new builds: parquet or HDF5? (Lean: parquet
  for new, keep HDF5 for the Enhanced CPS legacy until consumers
  migrate.)
- Should the manifest schema have a `schema_version` and a formal
  migration policy? (Lean: yes, borrow from PEP 621 style
  pragmatic evolution.)
