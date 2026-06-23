"""PolicyEngine bundle maintenance entry point.

This script is the operator-facing wrapper around the lower-level bundle
maintenance scripts. It keeps the main workflows discoverable for humans and
AI agents while preserving the smaller implementation modules underneath.

Examples:

    python scripts/bundle.py update-packages --us 1.730.0 --uk 2.91.0
    python scripts/bundle.py certify-data --country uk --manifest-uri hf://...
    python scripts/bundle.py generate
    python scripts/bundle.py generate --include-tros
    python scripts/bundle.py check
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))


def _certify_data(args: argparse.Namespace) -> int:
    from certify_data_release import main as certify_data_release_main

    argv = [
        "--country",
        args.country,
        "--manifest-uri",
        args.manifest_uri,
    ]
    if args.data_producer:
        argv.extend(["--data-producer", args.data_producer])
    if args.model_version:
        argv.extend(["--model-version", args.model_version])
    if args.no_generate:
        argv.append("--no-generate")
    if args.no_changelog:
        argv.append("--no-changelog")
    if args.skip_artifact_check:
        argv.append("--skip-artifact-check")
    return certify_data_release_main(argv)


def _update_packages(args: argparse.Namespace) -> int:
    from prepare_package_bundle_update import main as prepare_package_bundle_update_main

    argv: list[str] = []
    for option in ("core", "us", "uk", "us_data"):
        value = getattr(args, option)
        if value:
            argv.extend([f"--{option.replace('_', '-')}", value])
    if args.changelog:
        argv.extend(["--changelog", args.changelog])
    if args.fragment_name:
        argv.extend(["--fragment-name", args.fragment_name])
    return prepare_package_bundle_update_main(argv)


def _generate(args: argparse.Namespace) -> int:
    from generate_bundle_artifacts import generate

    result = generate(check=False)
    if not args.include_tros:
        return result
    return _generate_tros()


def _check(args: argparse.Namespace) -> int:
    from generate_bundle_artifacts import generate

    result = generate(check=True)
    if not args.include_tros:
        return result
    return result or _check_tros()


def _generate_tros() -> int:
    os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
    from generate_trace_tros import regenerate_all

    written, regressions = regenerate_all()
    for path in written:
        print(f"wrote {path}")
    for country_id, tro_path, reason in regressions:
        print(
            f"error: {country_id} already has {tro_path.name} but regeneration "
            f"failed: {reason}",
            file=sys.stderr,
        )
    if regressions:
        return 1
    if not written:
        print("no countries could be regenerated (all skipped)", file=sys.stderr)
    return 0


def _check_tros() -> int:
    os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
    from generate_trace_tros import generated_tros

    changed = False
    for path, payload in generated_tros():
        if path.exists() and path.read_bytes() == payload:
            continue
        print(
            f"{path.relative_to(REPO_ROOT)} is not up to date.",
            file=sys.stderr,
        )
        changed = True
    return 1 if changed else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Maintain PolicyEngine bundle metadata and derived artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    certify = subparsers.add_parser(
        "certify-data",
        help="Certify a country data release into the bundle manifest.",
    )
    certify.add_argument("--country", required=True, choices=["us", "uk"])
    certify.add_argument(
        "--data-producer",
        choices=["legacy", "populace"],
        help="Data-producer strategy. Defaults to the certification script default.",
    )
    certify.add_argument(
        "--manifest-uri",
        required=True,
        help="hf://dataset/<repo_id>@<revision>/<path-to-release_manifest.json>",
    )
    certify.add_argument(
        "--model-version",
        help="Model package version to certify for. Defaults to installed metadata.",
    )
    certify.add_argument(
        "--no-generate",
        action="store_true",
        help="Do not regenerate pyproject.toml and derived bundle metadata.",
    )
    certify.add_argument(
        "--no-changelog",
        action="store_true",
        help="Do not write a Towncrier changelog fragment.",
    )
    certify.add_argument(
        "--skip-artifact-check",
        action="store_true",
        help="Skip the certified dataset reachability check.",
    )
    certify.set_defaults(func=_certify_data)

    packages = subparsers.add_parser(
        "update-packages",
        help="Update package pins in the bundle manifest.",
    )
    packages.add_argument("--core", help="Exact version for policyengine-core.")
    packages.add_argument("--us", help="Exact version for policyengine-us.")
    packages.add_argument("--uk", help="Exact version for policyengine-uk.")
    packages.add_argument(
        "--us-data",
        dest="us_data",
        help="Exact version for policyengine-us-data.",
    )
    packages.add_argument(
        "--changelog",
        default="Update the certified PolicyEngine bundle pins.",
        help="Patch changelog text to include with the bundle update.",
    )
    packages.add_argument(
        "--fragment-name",
        default="bundle-update.fixed.md",
        help="Changelog fragment filename under changelog.d/.",
    )
    packages.set_defaults(func=_update_packages)

    generate = subparsers.add_parser(
        "generate",
        help="Regenerate derived bundle artifacts.",
    )
    generate.add_argument(
        "--include-tros",
        action="store_true",
        help=(
            "Also regenerate TRACE TRO sidecars. Private data releases require "
            "HUGGING_FACE_TOKEN or HF_TOKEN."
        ),
    )
    generate.set_defaults(func=_generate)

    check = subparsers.add_parser(
        "check",
        help="Check derived bundle metadata.",
    )
    check.add_argument(
        "--include-tros",
        action="store_true",
        help=(
            "Also check TRACE TRO sidecars. Private data releases require "
            "HUGGING_FACE_TOKEN or HF_TOKEN."
        ),
    )
    check.set_defaults(func=_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
