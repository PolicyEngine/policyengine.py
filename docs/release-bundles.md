# Release Bundles

> **Current process.** Certification now runs inside this repository:
> `scripts/bundle.py certify-data` derives the vendored country manifest
> directly from a country's data release manifest (see the
> [data certification](engineering/skills/data-certification.md)
> engineering skill). The intermediate `policyengine-bundles` repository
> flow is retired; its published bundles remain the historical record of
> earlier certifications. The architecture below — country `*-data`
> repos publish immutable manifests, `policyengine.py` certifies — is
> unchanged.

This document defines the intended reproducibility boundary for `policyengine.py`.

The key design decision is:

- country `*-data` repos build and stage immutable data artifacts
- `policyengine.py` is the only component that certifies supported runtime bundles
- `policyengine.py` does not rebuild country data itself

This keeps country-specific data construction in the country data repos while still giving users a single top-level version to cite and pin.

## Installing a certified bundle

Use pip for ordinary library installs:

```bash
pip install policyengine
```

Use the bundle installer when you want the certified package scaffold and the
certified datasets for a cited `policyengine` version:

```bash
uvx --from policyengine==4.19.1 policyengine bundle install 4.19.1
```

When run from `uvx` or `pipx`, the command creates or reuses `.venv`. Inside an
existing virtualenv or conda environment, it installs into that active
environment. It installs the bundled Python packages with pip, downloads the
certified default US and UK datasets into `./data`, and writes a
`./data/.policyengine-bundle-receipt.json` receipt that records the target
Python.
Existing dataset files with the same filename are moved to
`./data/.policyengine-bundle-backups/<timestamp>/`.

Regional datasets may also be certified in the bundle manifest. They are not
eagerly downloaded by `policyengine bundle install`; callers should materialize
the certified regional URI from the manifest when they run a regional
simulation.

Useful variants:

```bash
uvx --from policyengine policyengine bundle install
uvx --from policyengine policyengine bundle install --country uk
uvx --from policyengine policyengine bundle install --no-datasets
uvx --from policyengine policyengine bundle install --yes
```

Check a local environment against a bundle:

```bash
uvx --from policyengine policyengine bundle status --data-dir ./data
uvx --from policyengine policyengine bundle verify 4.19.1 --data-dir ./data
policyengine bundle manifest 4.19.1
```

`status` and `verify` use the receipt's recorded target Python by default. Pass
`--venv` or `--python` only to inspect a different environment explicitly.

## Why this boundary exists

For countries like the UK, the data package is not model-independent. Dataset construction, imputations, and calibration steps call the country model directly. That means a published dataset artifact depends on:

- the country model version used during data construction
- the calibration targets used during data construction
- the raw input data used during data construction

If `policyengine.py` only pins a country model version and a data package version without checking that relationship, the provenance boundary is incomplete.

## Roles

### Country model package

Examples: `policyengine-uk`, `policyengine-us`

The country model package owns:

- policy logic
- variables and parameters
- reforms
- a `data_build_fingerprint` for the subset of model logic that affects data construction

It does not own final runtime bundle certification.

### Country data package

Examples: `populace-data`, `policyengine-uk-data`

The country data package owns:

- data build pipelines
- raw input acquisition
- calibration target snapshots
- expensive dataset construction
- staging immutable build artifacts with provenance

It does not define the final supported runtime bundle exposed to users.

### `policyengine.py`

`policyengine.py` owns:

- runtime bundle certification
- user-facing reproducibility boundaries
- the supported mapping from `policyengine.py` version to country model version and certified data artifact

It does not rebuild microdata artifacts.

Certification runs in this repository:
`src/policyengine/data/bundle/manifest.json` carries the certified
`data_releases.{country}` entry derived directly from the country's published
data release manifest. The entrypoint is:

```bash
python scripts/bundle.py certify-data --country us \
  --manifest-uri "hf://dataset/policyengine/populace-us@<tag>/releases/<tag>/release_manifest.json"
```

US Populace certification uses the Populace release manifest directly:

```bash
python scripts/bundle.py certify-data --country us --data-producer populace \
  --manifest-uri "hf://dataset/policyengine/populace-us@<tag>/releases/<tag>/release_manifest.json" \
  --model-version "<policyengine-us-version>"
```

That produces one US bundle manifest entry containing the Populace national
default dataset. State and congressional-district regions are runtime row
filters over that national dataset, so derived `states/*.h5` or
`districts/*.h5` files are not vendored into `data_releases.us.datasets`.

### Non-default dataset overlays

`certify_data_release` rewrites `data_releases.{country}` wholesale from the
certified release manifest, so that block only ever holds datasets from the
certified release. A staged artifact published in its own release — one that is
deliberately not the certified default — is registered instead under the
sibling `dataset_overlays.{country}` map:

```json
"dataset_overlays": {
  "us": {
    "populace_us_2024_acs_local": {
      "path": "populace_us_2024_acs_local.h5",
      "repo_id": "policyengine/populace-us",
      "revision": "populace-us-2024-buildl-acs-local-...",
      "sha256": "..."
    }
  }
}
```

`get_release_manifest` merges overlays into the resolvable dataset registry, so
`resolve_dataset_reference` and `managed_microsimulation` load them by name at
their own pinned, sha-verified revision. Overlays are strictly additive: an
overlay may not shadow the certified default or any certified dataset, so
default resolution is untouched. Because certification only rewrites
`data_releases`, overlays survive re-certification without any manual
re-add step.

Earlier releases (policyengine 4.15.x–4.16.x) were certified through the
`PolicyEngine/policyengine-bundles` archive flow; those bundles remain the
historical record of their certifications.

## Two manifest layers

The architecture has two manifest layers with different responsibilities.

### 1. Data build manifest

Published by the country `*-data` repo.

This answers:

- what bytes were produced
- how they were produced
- which exact model and targets produced them

Suggested schema:

```json
{
  "schema_version": 1,
  "country_id": "uk",
  "data_package": {
    "name": "policyengine-uk-data",
    "version": "1.41.0"
  },
  "build": {
    "build_id": "uk-data-2026-04-12T12-30-00Z",
    "git_sha": "abc123",
    "built_at": "2026-04-12T12:30:00Z",
    "built_with_model_package": {
      "name": "policyengine-uk",
      "version": "2.81.0",
      "git_sha": "def456",
      "data_build_fingerprint": "sha256:..."
    },
    "calibration_targets": {
      "snapshot_id": "2026-04-10",
      "sha256": "sha256:..."
    },
    "raw_inputs": [
      {
        "name": "frs_2023_24",
        "sha256": "sha256:..."
      }
    ],
    "build_environment": {
      "python_version": "3.13.3",
      "lockfile_sha256": "sha256:..."
    }
  },
  "default_datasets": {
    "national": "enhanced_frs_2023_24",
    "baseline": "frs_2023_24"
  },
  "artifacts": {
    "enhanced_frs_2023_24": {
      "kind": "microdata",
      "repo_id": "policyengine/policyengine-uk-data-private",
      "path": "builds/uk-data-2026-04-12T12-30-00Z/enhanced_frs_2023_24.h5",
      "revision": "uk-data-2026-04-12T12-30-00Z",
      "sha256": "sha256:...",
      "size_bytes": 123456789
    }
  }
}
```

Notes:

- `build_id` must be immutable.
- build artifacts should be staged under a build-specific path or revision, not a floating release tag.
- the build manifest is the authoritative provenance record for the artifact bytes.

### 2. Certified runtime bundle manifest

Published by `policyengine.py`.

This answers:

- which model and data artifact are supported together at runtime
- which exact dataset should be used by default
- which artifact checksum and provenance should be surfaced to users

Suggested schema:

```json
{
  "schema_version": 1,
  "policyengine_version": "3.5.0",
  "bundle_id": "uk-3.5.0",
  "published_at": "2026-04-12T13:00:00Z",
  "country_id": "uk",
  "model_package": {
    "name": "policyengine-uk",
    "version": "2.81.1"
  },
  "certified_data_artifact": {
    "data_package": {
      "name": "policyengine-uk-data",
      "version": "1.41.0"
    },
    "build_id": "uk-data-2026-04-12T12-30-00Z",
    "dataset": "enhanced_frs_2023_24",
    "uri": "hf://policyengine/policyengine-uk-data-private/builds/uk-data-2026-04-12T12-30-00Z/enhanced_frs_2023_24.h5@uk-data-2026-04-12T12-30-00Z",
    "sha256": "sha256:..."
  },
  "certification": {
    "compatibility_basis": "matching_data_build_fingerprint",
    "built_with_model_version": "2.81.0",
    "certified_for_model_version": "2.81.1",
    "data_build_fingerprint": "sha256:...",
    "certified_by": "policyengine.py release workflow"
  },
  "default_dataset": "enhanced_frs_2023_24",
  "region_artifacts": {
    "national": {
      "dataset": "enhanced_frs_2023_24"
    }
  }
}
```

Notes:

- this is the user-facing reproducibility boundary
- apps and APIs should surface this bundle, not only country package versions
- a bundle may reuse a previously staged data artifact if compatibility is explicitly certified

## TRACE export

The internal build manifest and certified runtime bundle remain the operational source of
truth.

TRACE sits on top of those manifests as a standards-based export layer.

### What gets exported

`policyengine.py` emits a certified-bundle TRO for each supported country. The
composition pins four artifacts by sha256:

- the bundled country release manifest shipped in `policyengine.py`
- the country data release manifest resolved for the certified data package version
- the certified dataset artifact
- the country model wheel published to PyPI (hash read from the bundled manifest
  when present, otherwise fetched from the PyPI JSON API at emit time)

TROs use the public TROv vocabulary at
`https://w3id.org/trace/trov/0.1#`. Every artifact location in the TRO
is a dereferenceable HTTPS URI or a local path relative to the shipped
wheel. Certification metadata is carried as structured `pe:*` fields on
the `trov:TransparentResearchPerformance` node so downstream tooling can
read `pe:certifiedForModelVersion`, `pe:compatibilityBasis`,
`pe:builtWithModelVersion`, `pe:dataBuildFingerprint`, and `pe:dataBuildId`
without parsing prose. Every TRO also carries `pe:emittedIn` set to
`"github-actions"` or `"local"`; CI-emitted TROs additionally carry
`pe:ciRunUrl` and `pe:ciGitSha`.

Country `*-data` repos should also emit a matching `trace.tro.jsonld` per
data release covering the release manifest and every staged artifact hash.
That is a country-data concern and lives in those repos.

#### Emitting a bundle TRO

From Python:

```python
from policyengine.provenance.manifest import get_data_release_manifest, get_release_manifest
from policyengine.provenance.trace import build_trace_tro_from_release_bundle, serialize_trace_tro

country = get_release_manifest("us")
tro = build_trace_tro_from_release_bundle(country, get_data_release_manifest("us"))
Path("us.trace.tro.jsonld").write_bytes(serialize_trace_tro(tro))
```

From the CLI:

```
policyengine trace-tro us --out us.trace.tro.jsonld
```

At release time, `scripts/generate_trace_tros.py` regenerates the bundled
`data/bundle/{country}.trace.tro.jsonld` files, and the
`Versioning` CI job commits them alongside the changelog so every published
wheel ships with the matching TRO.

#### Emitting a per-simulation TRO

```python
from policyengine.results import write_results_with_trace_tro

write_results_with_trace_tro(
    results,                                # ResultsJson instance
    "results.json",                         # where to write results
    bundle_tro=bundle_tro,                  # loaded from the shipped bundle
    reform_payload={"salt_cap": 0},
    bundle_tro_url=(
        "https://raw.githubusercontent.com/PolicyEngine/policyengine.py/"
        "v3.4.5/src/policyengine/data/bundle/us.trace.tro.jsonld"
    ),
)
```

The `bundle_tro_url` is recorded on the performance node as
`pe:bundleTroUrl`. A verifier can fetch that URL, recompute its sha256,
and confirm it matches the `bundle_tro` artifact hash in the simulation
TRO's composition. Without this anchor, the bundle reference is only as
trustworthy as whoever produced the JSON.

#### Validating a received TRO

Structural validation:

```
policyengine trace-tro-validate path/to/tro.jsonld
```

The shipped schema at `policyengine/data/schemas/trace_tro.schema.json`
checks structural fields, canonical hex-encoded sha256s, the required
`pe:emittedIn`, and that `trov:hasLocation` uses HTTPS (or the
well-known local paths `results.json`, `reform.json`,
`bundle.trace.tro.jsonld`). The same schema is exercised in the test
suite against generated TROs.

Content validation (the verifier workflow a replication reviewer
should run):

```python
import hashlib, json, requests
from policyengine.provenance.trace import canonical_json_bytes

sim_tro = json.load(open("results.trace.tro.jsonld"))
perf = sim_tro["@graph"][0]["trov:hasPerformance"]

# 1. Fetch the bundle TRO from its pinned URL and recompute its hash.
bundle_bytes = requests.get(perf["pe:bundleTroUrl"]).content
bundle_hash = hashlib.sha256(canonical_json_bytes(json.loads(bundle_bytes))).hexdigest()

# 2. Compare against the hash recorded in the simulation TRO's composition.
recorded = next(
    a["trov:sha256"]
    for a in sim_tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
    if a["@id"].endswith("bundle_tro")
)
assert bundle_hash == recorded, "bundle_tro_url content does not match sim TRO"

# 3. Confirm the fingerprint recorded on the performance matches the
#    fingerprint inside the fetched bundle.
bundle = json.loads(bundle_bytes)
bundle_fp = bundle["@graph"][0]["trov:hasComposition"]["trov:hasFingerprint"]["trov:sha256"]
assert perf["pe:bundleFingerprint"] == bundle_fp
```

A sim TRO with a swapped `bundle_tro` dict but a truthful
`pe:bundleTroUrl` will fail step 2; a sim TRO with both swapped will
fail step 3.

#### Known limitations

- TROs are emitted unsigned. A signed attestation (sigstore or in-toto)
  is a future addition that will bind TROs to a trusted-system key.
- The bundle composition does not yet pin a transitive lockfile
  (`uv.lock`/`poetry.lock`), a Python interpreter version, or an OS. AEA
  reviewers may demand these; the schema is extensible.
- The model wheel is hashed by PyPI's published sha256. If a wheel is
  yanked and re-uploaded under the same version, the hash will change
  and the TRO becomes invalid — which is the correct behaviour.
- Country data packages whose data release manifest is private require
  `HUGGING_FACE_TOKEN` at emit time. The regeneration script skips
  countries whose data release manifest is unreachable so a partial run
  does not block other countries.

### Preservation mirroring (Zenodo)

Hugging Face hosts the primary artifacts but publishes no preservation
commitment — its DOIs are short URLs that are deleted with the repo.
Zenodo publishes a preservation policy and mints real DOIs, so every
certified release's *certification record* (the bundle manifest, the
bundle TRO, and the data release manifest) should also live there:

```bash
ZENODO_TOKEN=... policyengine zenodo-mirror us            # draft deposit
ZENODO_TOKEN=... policyengine zenodo-mirror us --publish  # mint the DOI
policyengine zenodo-mirror us --sandbox                   # rehearsal
```

The deposit output includes `PreservationMirror` entries (host, URL,
DOI, sha256, timestamp) ready to merge into the data release manifest's
`preservation_mirrors`/`preservation_dois` fields, which the bundle TRO
then naturally carries on the next regeneration.

Two deliberate safety properties:

- **Licence gate.** `--include-dataset` deposits the dataset bytes too,
  but only when the source Hugging Face repo is publicly readable. A
  private source repo (the UK microdata, under UK Data Service licence)
  is refused unconditionally — the certification record still mirrors,
  because the manifests and TRO contain only hashes and version pins,
  which is exactly what makes a future copy of restricted data
  verifiable without redistributing it.
- **Deliberate publishing.** Deposits are drafts by default and carry
  no licence unless `--license` is passed; minting the DOI is an
  explicit `--publish`.

Tokens come from `ZENODO_TOKEN` (create one under Zenodo →
Applications → Personal access tokens, with `deposit:write` and
`deposit:actions` scopes).

### What TRACE does not replace

TRACE is not the source of truth for compatibility policy.

In particular, TRACE does not decide:

- whether a new model version can safely reuse an existing data artifact
- how `data_build_fingerprint` is computed
- which staged artifact becomes a supported runtime default

Those decisions still belong to the country data build manifest and the
`policyengine.py` certified runtime bundle.

### Why we still want it

TRACE adds three things our internal manifests do not provide by themselves:

- a standard declaration format for provenance exchange
- a composition fingerprint over the exact artifacts in scope
- a better external surface for papers, audits, and reproducibility reviews

That is why the recommended design is:

- internal manifests for build/certification control
- generated TRACE TROs for standards-based export

## Compatibility rule

The architecture should avoid forcing a new data build for every harmless country model release.

To do that safely, compatibility must be explicit.

### Data build fingerprint

Each country model package should expose a `data_build_fingerprint` that covers the subset of logic that affects dataset construction or calibration.

Examples of inputs to the fingerprint:

- variables used in imputations
- variables used in calibration loss matrices
- parameters referenced during data construction
- uprating or target-computation logic used during the build

Things that should usually not affect the fingerprint:

- runtime-only outputs that are not used in data construction
- UI-oriented metadata
- code paths unrelated to data construction

### Certification rules

`policyengine.py` may certify a staged data artifact for a model version only if one of the following is true:

1. the model version exactly matches the `built_with_model_package.version`
   (`compatibility_basis: built_with_model_package`)
2. the data publisher's `compatible_model_packages` covers the model version
   (`compatibility_basis: compatible_model_packages` — the publisher's claim,
   recorded with a warning and made good by the test suite passing on the
   pinned pair)

If neither is true, certification fails hard and a new data build or a
published compatibility claim is required. A `data_build_fingerprint`
basis (same fingerprint as the build-time model) is a planned third
basis; it requires fingerprint metadata from the installed model package.

## Artifact states

Artifacts should move through explicit states:

- `staged`: built by the country data repo and available for inspection or later certification
- `certified`: referenced by a released `policyengine.py` runtime bundle
- `deprecated`: no longer recommended for new use, but still reproducible

The key point is that `staged` and `certified` are different states. A staged artifact is not automatically part of a supported runtime release.

## UK release workflow

### Case 1: model-only release

1. Cut UK model release candidate `M`.
2. Compute `data_build_fingerprint(M)`.
3. Compare it to the fingerprint recorded in the previously certified data build manifest.
4. If the fingerprint matches, skip the expensive UK data rebuild.
5. Release `policyengine.py` with a new certified runtime bundle that points to the existing staged UK artifact.

### Case 2: data-affecting release

1. Cut UK model release candidate `M`.
2. Compute `data_build_fingerprint(M)`.
3. If the fingerprint changed, build a new UK data artifact in `policyengine-uk-data` against:
   - exact `policyengine-uk==M`
   - exact target snapshot
   - exact raw input hashes
4. Stage the new artifact under a build-specific immutable path or revision.
5. Publish the UK data build manifest.
6. Release `policyengine.py` with a certified runtime bundle that points to the new staged artifact.

## Implementation guidance

The current `release_manifest.json` mechanism in country data repos is a good starting point, but it is not yet enough on its own. The target implementation should add:

- `built_with_model_package.version`
- `built_with_model_package.git_sha`
- `built_with_model_package.data_build_fingerprint`
- calibration target snapshot metadata
- immutable staged artifact paths or revisions

The target implementation in `policyengine.py` should add:

- hard validation of bundle certification rules
- explicit runtime bundle metadata on simulations, APIs, and app responses
- checksum-backed dataset resolution from the certified bundle manifest

## Why not let `policyengine.py` build all country data directly?

Because that would centralise the wrong concerns:

- country-specific private data handling would move into the generic orchestration layer
- country-specific build logic would move into the generic orchestration layer
- expensive build failures would block the top-level runtime package more often
- provenance would still originate in the country data pipeline, so `policyengine.py` would not actually eliminate the need for the country build manifest

`policyengine.py` should be the certification boundary, not the country data build system.
