.PHONY: docs docs-serve docs-generate-reference docs-reference-smoke

all: build-package

docs:
	quarto render docs

docs-generate-reference:
	uv run --extra us python docs/_generator/build_reference.py --country us --out docs/_generated/reference/us

docs-reference-smoke:
	rm -rf /tmp/policyengine-reference-smoke
	uv run --extra us python docs/_generator/build_reference.py --country us --filter chip --out /tmp/policyengine-reference-smoke/us
	quarto render /tmp/policyengine-reference-smoke/us/index.qmd --output-dir /tmp/policyengine-reference-smoke/rendered
	quarto render /tmp/policyengine-reference-smoke/us/programs.qmd --output-dir /tmp/policyengine-reference-smoke/rendered
	quarto render $$(find /tmp/policyengine-reference-smoke/us -type f -name "*.qmd" ! -name "index.qmd" ! -name "programs.qmd" | head -n 1) --output-dir /tmp/policyengine-reference-smoke/rendered

docs-serve:
	quarto preview docs

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
