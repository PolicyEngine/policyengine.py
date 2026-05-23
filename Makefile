.PHONY: all build-package changelog clean docs docs-serve docs-generate-reference docs-reference-smoke format install lint push-pr-branch test

all: build-package

docs:
	quarto render docs

docs-generate-reference:
	uv run --extra us python docs/_generator/build_reference.py --country us --out docs/_generated/reference/us

docs-reference-smoke:
	rm -rf /tmp/policyengine-reference-smoke
	uv run --extra us python docs/_generator/build_reference.py --country us --filter chip --out /tmp/policyengine-reference-smoke/us
	quarto render /tmp/policyengine-reference-smoke/us/index.qmd --output-dir /tmp/policyengine-reference-smoke/rendered/root
	quarto render /tmp/policyengine-reference-smoke/us/programs.qmd --output-dir /tmp/policyengine-reference-smoke/rendered/program-index
	quarto render /tmp/policyengine-reference-smoke/us/programs/chip.qmd --output-dir /tmp/policyengine-reference-smoke/rendered/program
	quarto render /tmp/policyengine-reference-smoke/us/gov/hhs/chip/chip.qmd --output-dir /tmp/policyengine-reference-smoke/rendered/variable

docs-serve:
	quarto preview docs

install:
	uv pip install -e ".[dev]"

format:
	ruff format .

lint:
	ruff format --check .
	ruff check .

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

BRANCH := $(shell git branch --show-current)

push-pr-branch:
	@if [ "$(BRANCH)" = "main" ]; then \
		echo "Refusing to push main as a PR branch."; \
		exit 1; \
	fi
	@REMOTE_URL=$$(git remote get-url origin 2>/dev/null || true); \
	if [ -z "$$REMOTE_URL" ]; then \
		echo "Missing origin remote. Add PolicyEngine/policyengine.py as origin before opening PRs."; \
		exit 1; \
	fi; \
	case "$$REMOTE_URL" in \
		*PolicyEngine/policyengine.py*) ;; \
		*) echo "Refusing to push: origin ($$REMOTE_URL) is not PolicyEngine/policyengine.py."; exit 1 ;; \
	esac
	@git push -u origin HEAD:$(BRANCH)
	@echo "Create the PR with: gh pr create --draft --repo PolicyEngine/policyengine.py --head $(BRANCH) --base main"
