.PHONY: docs docs-serve

MYSTMD_VERSION ?= 1.8.3
MYST_CMD = npx --yes mystmd@$(MYSTMD_VERSION)

all: build-package

docs:
	cd docs && $(MYST_CMD) build --html

docs-serve:
	cd docs && $(MYST_CMD) start

install:
	uv pip install -e ".[dev]"

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
