# PolicyEngine stacks

A PolicyEngine stack is the exact first-party package set certified for a
`policyengine` release. Installation is standard pip:

```bash
pip install "policyengine[full]==4.19.1"
pip install "policyengine[us-full]==4.19.1"
pip install "policyengine[models]==4.19.1"
```

The stack source of truth is `policyengine-stack.toml`. Generated artifacts are:

- `pyproject.toml` extras
- `src/policyengine/data/stack/manifest.json`
- GitHub release assets exported from the packaged manifest

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

This updates stack metadata and creates a patch changelog fragment. Do not bump
the `policyengine` version manually in the PR; the existing release workflow
bumps the package and stack versions together after merge.

CI checks generated artifacts, installs `.[models]`, runs `pip check`, and
verifies the packaged stack metadata with lightweight URI checks. Full data
package installation remains available through `policyengine[full]` for data
packages published to a Python package index. The current UK data artifact is
cited in the stack manifest, but `policyengine-uk-data` is not yet published to
PyPI, so the `uk-data` extra is intentionally empty until that changes.
