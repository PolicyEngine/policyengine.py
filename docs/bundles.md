# PolicyEngine bundles

A PolicyEngine bundle is the exact first-party package set and certified
dataset set for a `policyengine` release. The bundle version is the
`policyengine` version.

Regular package installation remains standard pip:

```bash
pip install "policyengine==4.19.1"
pip install "policyengine[us]==4.19.1"
pip install "policyengine[uk]==4.19.1"
```

For a certified model-plus-data install, run the bundle installer as the single
setup command:

```bash
uvx --from policyengine==4.19.1 policyengine bundle install 4.19.1
```

With no version pin, `uvx` uses the newest published `policyengine` release:

```bash
uvx --from policyengine policyengine bundle install
```

When run from `uvx` or `pipx`, the installer creates or reuses `./.venv`.
Inside an existing virtualenv or conda environment, it installs into that active
environment. The installer then installs the
exact bundled package scaffold with pip, downloads certified default US and UK
datasets into `./data`, and writes a `./data/.policyengine-bundle-receipt.json`
receipt that records the target Python.

Dataset pre-download and US and UK calculations share the same verified-download
implementation. For every managed artifact, PolicyEngine.py reads the source
data package name, Hugging Face repository type, immutable revision, and SHA-256
from the bundle. It reuses an existing file only when its hash matches, downloads
and verifies a replacement before atomically replacing an invalid local file,
and records the verified result in the receipt.

The bundle manifest can certify additional regional datasets, such as US state
datasets. Those artifacts are part of the citable bundle manifest, but
`policyengine bundle install` does not eagerly download every regional file.
Runtime callers should use the manifest's regional dataset URI when a regional
simulation needs one.

To materialize a default or named artifact without installing the complete
package scaffold:

```python
from policyengine.provenance import materialize_dataset

result = materialize_dataset("us", "populace_us_2024")
print(result.path)
print(result.bundle_dataset.sha256)
```

`materialize_dataset` returns the selected source URI and local path. For a
bundle-managed input, `bundle_dataset` also contains the selected source
package, repository type, revision, verified SHA-256, and optional metadata
path.
`policyengine-*-data` and `populace-data` artifacts use the repository type
recorded in the bundle. Callers do not infer repository type from the repository
name.

Managed datasets are downloaded from the Hugging Face artifact specified in the
bundle. GCS dataset URIs are unsupported. The separate UK geography lookup files
retain their existing storage implementation.

Country-specific and package-only installs are supported:

```bash
uvx --from policyengine policyengine bundle install --country uk
uvx --from policyengine policyengine bundle install --no-datasets
```

Use `--yes` for CI/CD. Without `--yes`, dataset downloads ask for confirmation.

The canonical bundle manifest is `src/policyengine/data/bundle/manifest.json`.
Derived artifacts are:

- `pyproject.toml` extras
- `src/policyengine/data/bundle/{country}.trace.tro.jsonld`
- GitHub release assets exported from the bundle manifest

Inspect or verify a local setup with:

```bash
uvx --from policyengine policyengine bundle status --data-dir ./data
uvx --from policyengine policyengine bundle verify 4.19.1 --data-dir ./data
policyengine bundle manifest 4.19.1
```

`status` and `verify` read the receipt and inspect the Python environment that
`install` targeted. Use `--venv` or `--python` only to inspect a different
target explicitly.

## Bundle-only PRs

Run:

```bash
python scripts/bundle.py update-packages \
  --core 3.27.0 \
  --us 1.730.0 \
  --uk 2.91.0
```

To certify a new data release from a data-producer manifest, run:

```bash
python scripts/bundle.py certify-data \
  --country uk \
  --data-producer populace \
  --manifest-uri hf://dataset/policyengine/populace-uk-private@<release>/releases/<release>/release_manifest.json
```

For US Populace releases, certify the Populace release manifest directly:

```bash
python scripts/bundle.py certify-data \
  --country us \
  --data-producer populace \
  --manifest-uri hf://dataset/policyengine/populace-us@<release>/releases/<release>/release_manifest.json \
  --model-version <policyengine-us-version>
```

US state and congressional-district regions scope the certified national
Populace dataset with row filters. If a Populace release also publishes derived
`states/*.h5` or `districts/*.h5` area slices, the bundle certification omits
those slices from `data_releases.us.datasets`; they are not runtime dataset
dependencies.

Use `python scripts/bundle.py generate` to regenerate derived bundle metadata,
and `python scripts/bundle.py generate --include-tros` when TRACE TRO sidecars
should also be regenerated. Private data releases require `HUGGING_FACE_TOKEN`
or `HF_TOKEN` for TRO regeneration.

This updates bundle metadata and creates a patch changelog fragment. Do not bump
the `policyengine` version manually in the PR; the existing release workflow
bumps the package and bundle versions together after merge.

CI checks derived bundle metadata, installs the package scaffold from the
bundle manifest, runs `pip check`, and verifies the packaged bundle metadata
with lightweight URI checks. Dataset downloads are handled by
`policyengine bundle install`, so certified UK data can be pinned by manifest
version and downloaded from Hugging Face even when the matching
`policyengine-uk-data` package is not published to PyPI.
