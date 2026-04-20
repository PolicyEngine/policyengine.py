---
title: "Provenance and release bundles"
---

Every analysis in PolicyEngine is reproducible to a specific bundle of (package version, country model version, dataset version, calibration state). The `provenance` module formalizes this.

## The bundle

Each `policyengine` release pins:

- The policyengine-core version
- The country model versions (`policyengine-us`, `policyengine-uk`)
- The country-data versions (`policyengine-us-data`, `policyengine-uk-data`)
- Dataset hash (content-addressed — the hashed Enhanced CPS file is a bundle ID)
- Calibration vector IDs

Together these define a **data release manifest** — a published, immutable record of "running this code against this data produces these numbers."

## Checking your bundle

```python
import policyengine as pe

pe.us.model.manifest                 # pinned US manifest for this release
pe.us.model.data_certification       # cert checking installed package vs manifest
```

If the installed country package version doesn't match the pinned manifest, the model warns:

```
UserWarning: Installed policyengine-us version (1.602.0) does not match
the bundled policyengine.py manifest (1.653.3). Calculations will run
against the installed version, but dataset compatibility is not guaranteed.
```

Pin exactly to match a release for strict reproducibility:

```bash
pip install policyengine==4.0.0 policyengine-us==1.653.3 policyengine-us-data==2.12.0
```

## Certifying an analysis

For a published analysis (paper, policy brief, congressional testimony), attach the manifest to your results:

```python
from policyengine.provenance import write_manifest

result = economic_impact_analysis(reform=REFORM, year=2026)
write_manifest(result, path="my_analysis.manifest.json")
```

The manifest captures package versions, dataset hash, reform spec, and a hash of the result. Readers can verify reproducibility by installing the same pinned stack and rerunning.

## Dataset content addressing

Microdata files are content-addressed — the filename includes a SHA hash. `enhanced_cps_2024.h5` at one publish date is a different artifact than at a later date; they live at different Hugging Face paths.

```python
dataset_uri = "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5"
dataset = pe.us.ensure_datasets([dataset_uri])[0]
dataset.content_hash
```

Always cite the full URI (including revision if pinning) in published work.

## Building your own manifest

If you fork and modify the country model or data, publish your own manifest:

```python
from policyengine.provenance import build_manifest

manifest = build_manifest(
    country_code="us",
    model_version="my-fork-1.0.0",
    dataset_hashes={"my_dataset": "sha256:..."},
)
```

Users of your fork install your pinned stack and get your manifest.

## When to care about this

- Publishing numbers (paper, brief, official analysis)
- Regulatory submissions where auditors must reproduce
- Long-running studies where package versions will drift over the analysis window

For day-to-day exploration, version drift between `policyengine` and country packages is tolerable and the warning is informational.
