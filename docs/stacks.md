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
uvx --from policyengine==4.19.1 policyengine bundle install 4.19.1 --venv .venv
```

With no version pin, `uvx` uses the newest published `policyengine` release:

```bash
uvx --from policyengine policyengine bundle install --venv .venv
```

The installer creates or reuses the target virtual environment, installs the
exact bundled package scaffold with pip, downloads certified US and UK datasets
into `./data`, moves replaced dataset files into
`./data/.policyengine-bundle-backups/<timestamp>/`, and writes a
`./data/.policyengine-bundle.json` receipt.

Country-specific and package-only installs are supported:

```bash
uvx --from policyengine policyengine bundle install --venv .venv --country uk
uvx --from policyengine policyengine bundle install --venv .venv --no-datasets
```

Use `--yes` for CI/CD. Without `--yes`, dataset downloads ask for confirmation.

The bundle source of truth is `policyengine-stack.toml`. Generated artifacts are:

- `pyproject.toml` extras
- `src/policyengine/data/stack/manifest.json`
- GitHub release assets exported from the packaged manifest

Inspect or verify a local setup with:

```bash
policyengine bundle status --data-dir ./data
policyengine bundle verify 4.19.1 --data-dir ./data
policyengine bundle manifest 4.19.1
```

## Stack-only PRs

Run:

```bash
python scripts/prepare_stack_update.py \
  --core 3.27.0 \
  --us 1.730.0 \
  --uk 2.91.0 \
  --us-data 1.118.0 \
  --uk-data 1.45.0
```

This updates bundle metadata and creates a patch changelog fragment. Do not bump
the `policyengine` version manually in the PR; the existing release workflow
bumps the package and bundle versions together after merge.

CI checks generated artifacts, installs `.[models]`, runs `pip check`, and
verifies the packaged bundle metadata with lightweight URI checks. Dataset
downloads are handled by `policyengine bundle install`, so certified UK data can
be pinned by manifest version and downloaded from Hugging Face even when the
matching `policyengine-uk-data` package is not published to PyPI.
