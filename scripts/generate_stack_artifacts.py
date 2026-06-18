"""Generate pip extras and packaged stack metadata from policyengine-stack.toml."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - for local Python 3.10 users.
    import tomli as tomllib  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parents[1]
STACK_SOURCE = REPO_ROOT / "policyengine-stack.toml"
PYPROJECT = REPO_ROOT / "pyproject.toml"
STACK_MANIFEST = REPO_ROOT / "src" / "policyengine" / "data" / "stack" / "manifest.json"

OPTIONAL_DEPENDENCIES_HEADER = "[project.optional-dependencies]"
NEXT_SECTION_PATTERN = re.compile(r"\n\[tool\.setuptools\]", re.MULTILINE)
FIRST_PARTY_PACKAGE_NAMES = {
    "policyengine",
    "policyengine-core",
    "policyengine-us",
    "policyengine-uk",
    "policyengine-us-data",
    "policyengine-uk-data",
}


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def generated_manifest(stack: Mapping[str, Any]) -> dict[str, Any]:
    packages = {
        key: {
            **value,
            "install_requirement": exact_requirement(value),
        }
        for key, value in stack["packages"].items()
    }
    return {
        "schema_version": int(stack["schema_version"]),
        "stack_version": stack["stack_version"],
        "policyengine_version": stack["policyengine_version"],
        "source": "policyengine-stack.toml",
        "packages": packages,
        "extras": stack["extras"],
        "countries": stack.get("countries", {}),
        "citation": {
            "title": f"PolicyEngine stack {stack['stack_version']}",
            "version": stack["stack_version"],
            "type": "software-stack",
            "publisher": "PolicyEngine",
        },
    }


def manifest_text(stack: Mapping[str, Any]) -> str:
    return json.dumps(generated_manifest(stack), indent=2, sort_keys=True) + "\n"


def update_pyproject_text(pyproject_text: str, stack: Mapping[str, Any]) -> str:
    pyproject = tomllib.loads(pyproject_text)
    optional = pyproject["project"].get("optional-dependencies", {})
    stack_extras = stack["extras"]

    kept_extras: dict[str, list[str]] = {}
    for name, dependencies in optional.items():
        if name == "dev" or name in stack_extras:
            continue
        kept_extras[name] = list(dependencies)

    generated_extras = {
        name: [
            exact_requirement(stack["packages"][package_name])
            for package_name in package_names
        ]
        for name, package_names in stack_extras.items()
    }

    dev_dependencies = [
        dependency
        for dependency in optional.get("dev", [])
        if normalized_requirement_name(dependency) not in FIRST_PARTY_PACKAGE_NAMES
    ]
    for package_name in stack_extras.get("models", []):
        dev_dependencies.append(exact_requirement(stack["packages"][package_name]))

    replacement = format_optional_dependencies(
        {
            **kept_extras,
            **generated_extras,
            "dev": dev_dependencies,
        }
    )
    start = pyproject_text.index(OPTIONAL_DEPENDENCIES_HEADER)
    next_section = NEXT_SECTION_PATTERN.search(pyproject_text, start)
    if next_section is None:
        raise ValueError("Could not find section after project.optional-dependencies.")
    return (
        pyproject_text[:start]
        + replacement
        + pyproject_text[next_section.start() + 1 :]
    )


def exact_requirement(component: Mapping[str, Any]) -> str:
    requirement = f"{component['name']}=={component['version']}"
    markers = component.get("markers")
    if markers:
        requirement += f"; {markers}"
    return requirement


def normalized_requirement_name(dependency: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", dependency)
    if match is None:
        return ""
    return match.group(1).replace("_", "-").lower()


def format_optional_dependencies(extras: Mapping[str, list[str]]) -> str:
    lines = [OPTIONAL_DEPENDENCIES_HEADER]
    for extra_name, dependencies in extras.items():
        lines.append(f"{extra_name} = [")
        for dependency in dependencies:
            lines.append(f'    "{dependency}",')
        lines.append("]")
    return "\n".join(lines) + "\n\n"


def write_or_check(path: Path, content: str, *, check: bool) -> bool:
    if path.exists() and path.read_text() == content:
        return False
    if check:
        print(f"{path.relative_to(REPO_ROOT)} is not up to date.", file=sys.stderr)
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"Updated {path.relative_to(REPO_ROOT)}")
    return True


def generate(*, check: bool = False) -> int:
    stack = load_toml(STACK_SOURCE)
    changed = False
    changed |= write_or_check(STACK_MANIFEST, manifest_text(stack), check=check)
    changed |= write_or_check(
        PYPROJECT,
        update_pyproject_text(PYPROJECT.read_text(), stack),
        check=check,
    )
    return 1 if check and changed else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if generated files are not up to date.",
    )
    args = parser.parse_args()
    return generate(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
