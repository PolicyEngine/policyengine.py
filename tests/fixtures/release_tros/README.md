# Historical public TRACE inputs

These are existing published inputs used to exercise the real repository TRO
generator. They do not certify a new canonical SPM release.

- `manifest.json` and `us.trace.tro.jsonld`: copied byte for byte from
  PolicyEngine/policyengine.py commit
  `3c3b4f6442f4a5adc47274734d71a6ca10103b43`, under
  `src/policyengine/data/bundle/`.
- `us-release_manifest.json`: published Populace release
  `populace-us-2024-buildp-sparse-rmloss100-cae8640-20260728T011454Z`, at
  `https://huggingface.co/datasets/policyengine/populace-us/resolve/populace-us-2024-buildp-sparse-rmloss100-cae8640-20260728T011454Z/releases/populace-us-2024-buildp-sparse-rmloss100-cae8640-20260728T011454Z/release_manifest.json`.
  Its raw SHA256 is
  `dd949ba3c4c7a56aff8442c6db5a031d2c84c3da59f5d14832f468c358604506`,
  matching the reviewed sidecar's data-release-manifest artifact.
- `country-models.lock.toml`: the complete, unchanged `policyengine-us` and
  `policyengine-uk` package blocks extracted from `uv.lock` at the same wrapper
  commit. These bind the certified model names, versions, wheel URLs and hashes
  to the actual reviewed installation artifacts. This excerpt is used only by
  the TRO tests; the separate lock tests resolve a complete project with uv.

The UK private data manifest is not vendored here. Release CI authenticates it
from the pinned Hugging Face revision using the repository's existing secret.
