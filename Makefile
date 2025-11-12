.PHONY: docs

all: build-package

docs:
	cd docs && jupyter book start

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
	build-changelog changelog.yaml --output changelog.yaml --update-last-date --start-from 1.0.0 --append-file changelog_entry.yaml
	build-changelog changelog.yaml --org PolicyEngine --repo policyengine.py --output CHANGELOG.md --template .github/changelog_template.md
	bump-version changelog.yaml pyproject.toml
	rm changelog_entry.yaml || true
	touch changelog_entry.yaml

build-package:
	python -m build

test:
	pytest tests