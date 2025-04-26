all: build-package

documentation:
	jb clean docs
	jb build docs
	python docs/add_plotly_to_book.py docs/

install:
	pip install -e .[dev]

format:
	black . -l 79

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