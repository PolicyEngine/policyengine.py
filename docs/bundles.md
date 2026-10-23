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

Country-specific, package-only, and dataset-only installs are supported:

```bash
uvx --from policyengine policyengine bundle install --country uk
uvx --from policyengine policyengine bundle install --no-datasets
uvx --from policyengine policyengine bundle install --no-packages --yes
```

Use `--yes` for CI/CD. Without `--yes`, dataset downloads ask for confirmation.
Use `--no-packages` when a lockfile or another package manager owns the Python
environment. It downloads and verifies the selected certified datasets and
writes the bundle receipt without resolving Python, creating a virtual
environment, or installing packages. Dataset-only receipts omit
`target_python`; `bundle status` therefore inspects its current interpreter
unless `--python` or `--venv` is supplied explicitly.

The canonical bundle manifest is `src/policyengine/data/bundle/manifest.json`.
Derived artifacts are:

- `pyproject.toml` extras
- `src/policyengine/data/bundle/{country}.trace.tro.jsonld`
- GitHub release assets exported from the bundle manifest

The US model in this bundle uses the SPM calculator 1.0.0 API. The manifest pins
`spm-calculator==1.0.0` as a US runtime dependency, and the generated `us`,
`models` and `dev` extras carry that pin. The model formulas and certified
dataset artifacts remain unchanged.

Previously published versions cannot acquire a new dependency constraint. To
reproduce the historical 5.3.0 US package set, include the compatible calculator
explicitly:

```bash
uv pip install "policyengine[us]==5.3.0" "spm-calculator==0.3.1"
```

Inspect or verify a local setup with:

```bash
uvx --from policyengine policyengine bundle status --data-dir ./data
uvx --from policyengine policyengine bundle verify 4.19.1 --data-dir ./data
policyengine bundle manifest 4.19.1
```

`status` and `verify` read the receipt and inspect the Python environment that
`install` targeted. Use `--venv` or `--python` only to inspect a different
target explicitly.

## Local release manifests for Budget-day runners

Set `POLICYENGINE_UK_DATA_MANIFEST_FILE` before starting a generation process to
read the UK release manifest from that file. The same setting is available as
`POLICYENGINE_<COUNTRY>_DATA_MANIFEST_FILE` for other bundled countries. When set,
it always selects the local file, avoiding a Hugging Face request and its timeout.
An unset setting preserves the existing fetch and certification behavior.

The trust anchor is the `trov:sha256` on
`composition/1/artifact/data_release_manifest` in the installed country's
`data/bundle/{country}.trace.tro.jsonld`. The file's **raw bytes** must match that
pin. A missing pin, unreadable file, altered bytes, or certification mismatch
stops the process. The model, core, build ID and fingerprint checks still apply;
selecting a local file cannot extend the bundle's certification.

At G0 each morning, while Hugging Face is available, use the exact installed
release that the runner will use and download and verify the manifest before
enabling the setting. Keep the Hugging Face token in `HUGGING_FACE_TOKEN`,
`HF_TOKEN` or `HUGGINGFACE_HUB_TOKEN`:

```bash
env -u POLICYENGINE_UK_DATA_MANIFEST_FILE POLICYENGINE_SKIP_COUNTRY_IMPORTS=1 python - <<'PY'
import hashlib
from pathlib import Path

import requests
from policyengine.provenance.manifest import (
    bundled_data_release_manifest_sha256, get_release_manifest,
    hugging_face_auth_headers, https_release_manifest_uri,
)

expected = bundled_data_release_manifest_sha256("uk")
response = requests.get(
    https_release_manifest_uri(get_release_manifest("uk").data_package),
    headers=hugging_face_auth_headers(), timeout=30,
)
response.raise_for_status()
actual = hashlib.sha256(response.content).hexdigest()
if actual != expected:
    raise RuntimeError(f"Manifest SHA-256: expected {expected}; actual {actual}")
target = Path("data/uk-release-manifest.json")
target.parent.mkdir(parents=True, exist_ok=True)
staged = target.with_suffix(".json.tmp")
staged.write_bytes(response.content)
staged.replace(target)
print(f"Verified {target}: {actual}")
PY
export POLICYENGINE_UK_DATA_MANIFEST_FILE="$PWD/data/uk-release-manifest.json"
```

Start a fresh runner process with that setting and record its receipt at G0.
Runtime certification and TRACE output use a distinct basis ending in
`_local_manifest`, such as `exact_build_model_version_local_manifest`; packaged
execution receipts record it as `runtime.data_certification_basis`. The
receipt's certificate keeps the bundle's published basis so certificate
verification remains reproducible. See [execution receipts](receipts.md).
Refresh and verify the file whenever the installed certified release changes.

For Autumn Budget deployment, ship this support in the same `policyengine`
release as María's weekend Microcosm cut certification. Fetch the manifest for
that released bundle at G0; an earlier cut's manifest will fail its new pin.
Use the normal changelog-fragment release workflow for both changes.

## Bundle-only PRs

Run:

```bash
python scripts/bundle.py update-packages \
  --core 3.27.0 \
  --us 1.730.0 \
  --uk 2.91.0
```

By default a data certificate follows the core pin (`core_binding:
bundle_pin`), so `--core` can move it; `bundle.py check --include-tros
--strict-tros` then warns when a data release does not claim the new core. A
certificate that binds its core (`certify-data --core-version`,
`core_binding: certified`) instead fails that check until the country is
re-certified for the new core. See "The core" in the data certification
skill.

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
  --regional-manifest-uri hf://dataset/policyengine/populace-us@<local-area-release>/releases/<local-area-release>/release_manifest.json \
  --model-version <policyengine-us-version>
```

US state and congressional-district regions scope one certified ACS-local
Populace dataset with row filters. Pass its non-default local-area release
manifest through `--regional-manifest-uri`; certification adds the pinned H5
artifact to `data_releases.us.datasets` and writes both regional path templates
under `data_releases.us.region_datasets`. If a legacy release publishes derived
`states/*.h5` or `districts/*.h5` slices, certification still omits them.

`policyengine bundle install` continues to materialize only each country's
certified national `default_dataset`. Regional runtimes materialize the
additional certified dataset when the selected region declares it.

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
