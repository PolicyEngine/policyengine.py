.PHONY: docs docs-serve docs-generate-reference

all: build-package

docs:
	quarto render docs

docs-serve:
	quarto preview docs

# Regenerate the auto-generated variable / program reference under docs/reference/.
# Run once per country model release; commits the refreshed pages alongside code.
docs-generate-reference:
	python docs/_generator/build_reference.py --country us --out docs/reference/us
	python docs/_generator/build_reference.py --country uk --out docs/reference/uk

install:
	uv pip install -e .[dev]

format:
	ruff format .

clean:
	find . -not -path "./.venv/*" -type d -name "__pycache__" -exec rm -rf {} +
	find . -not -path "./.venv/*" -type d -name "_build" -exec rm -rf {} +
	find . -not -path "./.venv/*" -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -not -path "./.venv/*" -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -not -path "./.venv/*" -type d -name "*.egg-info" -exec rm -rf {} +
	find . -not -path "./.venv/*" -type f -name "*.pyc" -delete
	find . -not -path "./.venv/*" -type f -name "*.h5" -delete

changelog:
	python .github/bump_version.py
	towncrier build --yes --version $$(python -c "import re; print(re.search(r'version = \"(.+?)\"', open('pyproject.toml').read()).group(1))")
build-package:
	python -m build

test:
	pytest tests --cov=policyengine --cov-report=term-missing
