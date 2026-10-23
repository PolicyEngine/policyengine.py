# Contributing to policyengine

Thank you for your interest in contributing! This page covers how to report problems, get support, and contribute code. For the full development guide (architecture, CI, releases), see [docs/dev.md](docs/dev.md).

## Reporting issues

Please report bugs and request features through [GitHub issues](https://github.com/PolicyEngine/policyengine.py/issues). For bugs, include:

- What you ran (a minimal code snippet is ideal)
- What you expected and what happened instead, including the full traceback
- Your `policyengine` version (`pip show policyengine`) and Python version

## Getting support

- Open a [GitHub issue](https://github.com/PolicyEngine/policyengine.py/issues) with a usage question
- Email [hello@policyengine.org](mailto:hello@policyengine.org)

## Development setup

```bash
git clone https://github.com/PolicyEngine/policyengine.py.git
cd policyengine.py
uv pip install -e ".[dev]"
```

This installs the shared analysis layer, both country model extras, and the dev dependencies used in CI (pytest, ruff, mypy, towncrier).

Tests require a `HUGGING_FACE_TOKEN` environment variable for downloading datasets:

```bash
export HUGGING_FACE_TOKEN=hf_...
make test
```

Common commands:

```bash
make format           # ruff format
make test             # pytest with coverage
make docs             # build static Quarto HTML docs
make docs-serve       # preview the docs locally
```

## Pull requests

1. Fork the repository (or create a branch, if you have write access) and make your changes.
2. Add a changelog fragment describing the change:

   ```bash
   # Fragment types: breaking, added, changed, fixed, removed
   echo "Description of change" > changelog.d/my-branch.fixed.md
   ```

3. Run `make format` and `make test` locally.
4. Open a pull request. CI runs lint/format checks, tests on Python 3.13 and 3.14, and a docs build; all required checks must pass before merge.

On merge, the versioning workflow bumps the version, builds the changelog, and creates a GitHub Release.

## Code of conduct

All participants are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
