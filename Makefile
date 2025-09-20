.PHONY: docs

all: build-package

docs:
	cd docs && jupyter book start

install:
	uv pip install -e .[dev]

format:
	ruff format .

clean:
	rm -rf **/__pycache__ _build **/_build .pytest_cache .ruff_cache **/*.egg-info **/*.pyc

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