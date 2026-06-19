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

CI checks generated artifacts, installs `.[models]`, and verifies the packaged
stack metadata with lightweight URI checks. Full data
package installation is available through `policyengine[full]`; this includes
both `policyengine-us-data` and `policyengine-uk-data` when their package
versions are installable for the target Python/platform. Dataset artifact
versions and release manifest URIs are recorded separately in the stack manifest
for citation and verification.
