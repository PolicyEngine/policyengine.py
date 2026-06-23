"""Prepare a PR that only updates package pins in the PolicyEngine bundle."""

from __future__ import annotations

import argparse
from typing import Any, Mapping

from generate_bundle_artifacts import (
    BUNDLE_SOURCE,
    generate,
    load_bundle_source,
    write_bundle_source,
)

PACKAGE_ARGS = {
    "core": "policyengine-core",
    "us": "policyengine-us",
    "uk": "policyengine-uk",
    "us_data": "policyengine-us-data",
}


def write_changelog(message: str, fragment_name: str) -> None:
    changelog_dir = BUNDLE_SOURCE.parent / "changelog.d"
    changelog_dir.mkdir(exist_ok=True)
    path = changelog_dir / fragment_name
    path.write_text(message.strip() + "\n")
    print(f"Updated {path.relative_to(BUNDLE_SOURCE.parent)}")


def update_package_pins(bundle: Mapping[str, Any], args: argparse.Namespace) -> dict:
    updated = dict(bundle)
    packages = {key: dict(value) for key, value in bundle["packages"].items()}
    updated["packages"] = packages
    for arg_name, package_key in PACKAGE_ARGS.items():
        version = getattr(args, arg_name)
        if version:
            packages[package_key]["version"] = version
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a package-pin-only PolicyEngine bundle PR."
    )
    for arg_name, package_key in PACKAGE_ARGS.items():
        parser.add_argument(
            f"--{arg_name.replace('_', '-')}",
            dest=arg_name,
            help=f"Exact version for {package_key}.",
        )
    parser.add_argument(
        "--changelog",
        default="Update the certified PolicyEngine bundle pins.",
        help="Patch changelog text to include with the bundle update.",
    )
    parser.add_argument(
        "--fragment-name",
        default="bundle-update.fixed.md",
        help="Changelog fragment filename under changelog.d/.",
    )
    args = parser.parse_args(argv)

    bundle = update_package_pins(load_bundle_source(), args)
    write_bundle_source(bundle)
    print(f"Updated {BUNDLE_SOURCE.relative_to(BUNDLE_SOURCE.parent)}")
    generate(check=False)
    write_changelog(args.changelog, args.fragment_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
