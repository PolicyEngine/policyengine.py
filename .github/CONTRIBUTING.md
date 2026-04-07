# Contributing

Thanks for contributing to PolicyEngine.py.

## Ways to contribute

- Open an issue for bugs, documentation gaps, or feature requests.
- Submit a pull request for code, tests, documentation, or examples.
- If you are unsure where to start, open an issue describing the workflow or analysis problem you want to improve.

## Development setup

```bash
git clone https://github.com/PolicyEngine/policyengine.py.git
cd policyengine.py
uv pip install -e .[dev]
```

This installs the package, both country models, and the development tools used in CI.

## Running checks

Before opening a pull request, run the checks relevant to your change:

```bash
make format
ruff check .
mypy src/policyengine
make test
```

Documentation changes can be checked with:

```bash
cd docs
myst build --html
```

Tests that download representative datasets require a `HUGGING_FACE_TOKEN`:

```bash
export HUGGING_FACE_TOKEN=hf_...
```

## Changelog fragments

Pull requests that change user-facing behaviour should include a changelog fragment in `changelog.d/`:

```bash
echo "Describe the change." > changelog.d/my-change.fixed
```

Valid fragment types are `breaking`, `added`, `changed`, `fixed`, and `removed`.

## Pull requests

- Keep pull requests focused and explain the user-facing impact.
- Add or update tests when behaviour changes.
- Update documentation and examples when the public workflow changes.

## Getting help

- Use GitHub issues for bugs, regressions, and feature requests.
- For questions that do not fit a public issue, contact `hello@policyengine.org`.
