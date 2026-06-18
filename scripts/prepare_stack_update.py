"""Prepare a PR that only updates the pip-native PolicyEngine stack."""

from __future__ import annotations

import argparse
from typing import Any, Mapping

from generate_stack_artifacts import REPO_ROOT, STACK_SOURCE, generate, load_toml

PACKAGE_ARGS = {
    "core": "policyengine-core",
    "us": "policyengine-us",
    "uk": "policyengine-uk",
    "us_data": "policyengine-us-data",
    "uk_data": "policyengine-uk-data",
}


def write_stack_source(stack: Mapping[str, Any]) -> None:
    lines: list[str] = [
        f"schema_version = {stack['schema_version']}",
        f'stack_version = "{stack["stack_version"]}"',
        f'policyengine_version = "{stack["policyengine_version"]}"',
        "",
    ]
    for package_key, package in stack["packages"].items():
        lines.append(f"[packages.{package_key}]")
        for key, value in package.items():
            lines.append(_toml_assignment(key, value))
        lines.append("")
    lines.append("[extras]")
    for extra, packages in stack["extras"].items():
        values = ", ".join(f'"{package}"' for package in packages)
        lines.append(f"{extra} = [{values}]")
    lines.append("")
    for country, metadata in stack.get("countries", {}).items():
        lines.append(f"[countries.{country}]")
        for key, value in metadata.items():
            lines.append(_toml_assignment(key, value))
        lines.append("")
    STACK_SOURCE.write_text("\n".join(lines).rstrip() + "\n")
    print(f"Updated {STACK_SOURCE.relative_to(REPO_ROOT)}")


def _toml_assignment(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return f"{key} = {str(value).lower()}"
    return f'{key} = "{value}"'


def write_changelog(message: str, fragment_name: str) -> None:
    changelog_dir = REPO_ROOT / "changelog.d"
    changelog_dir.mkdir(exist_ok=True)
    path = changelog_dir / fragment_name
    path.write_text(message.strip() + "\n")
    print(f"Updated {path.relative_to(REPO_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a stack-only PolicyEngine PR."
    )
    for arg_name, package_key in PACKAGE_ARGS.items():
        parser.add_argument(
            f"--{arg_name.replace('_', '-')}",
            dest=arg_name,
            help=f"Exact version for {package_key}.",
        )
    parser.add_argument(
        "--changelog",
        default="Update the certified PolicyEngine stack pins.",
        help="Patch changelog text to include with the stack update.",
    )
    parser.add_argument(
        "--fragment-name",
        default="stack-update.fixed.md",
        help="Changelog fragment filename under changelog.d/.",
    )
    args = parser.parse_args()

    stack = load_toml(STACK_SOURCE)
    packages = {key: dict(value) for key, value in stack["packages"].items()}
    stack = {**stack, "packages": packages}
    for arg_name, package_key in PACKAGE_ARGS.items():
        version = getattr(args, arg_name)
        if version:
            packages[package_key]["version"] = version
    write_stack_source(stack)
    generate(check=False)
    write_changelog(args.changelog, args.fragment_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
