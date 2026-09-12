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
    if args.regional_manifest_uri:
        argv.extend(["--regional-manifest-uri", args.regional_manifest_uri])
    if args.regional_artifact_prefix:
        argv.extend(["--regional-artifact-prefix", args.regional_artifact_prefix])
    if args.regional_path_template:
        argv.extend(["--regional-path-template", args.regional_path_template])
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
    for option in ("core", "us", "uk"):
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
    return _generate_tros(strict=args.strict_tros)


def _check(args: argparse.Namespace) -> int:
    from generate_bundle_artifacts import (
        generate,
        load_bundle_manifest,
        validate_bundle_measurements,
    )

    validate_bundle_measurements(
        load_bundle_manifest(), require_published_spm=args.published_spm
    )
    result = generate(check=True)
    if not args.include_tros:
        return result
    return result or _check_tros(strict=args.strict_tros)


def _set_spm(args: argparse.Namespace) -> int:
    from generate_bundle_artifacts import (
        generate,
        load_bundle_manifest,
        write_bundle_manifest,
    )
    from spm_bundle import configure_spm, published_calculator_component

    calculator = (
        published_calculator_component(args.calculator_version)
        if args.calculator_version
        else None
    )
    settings = {
        key: getattr(args, key)
        for key in (
            "forecast_content_sha256",
            "scenario",
            "geography_kind",
            "geography_id",
            "county_vintage",
            "as_of",
        )
    }
    write_bundle_manifest(configure_spm(load_bundle_manifest(), settings, calculator))
    return generate(check=False)


def _development_manifest(args: argparse.Namespace) -> int:
    from generate_bundle_artifacts import load_bundle_manifest
    from spm_bundle import write_development_manifest

    write_development_manifest(
        load_bundle_manifest(), args.country_wheel, args.calculator_wheel, args.output
    )
    print(f"Wrote uncertified local development fixture {args.output}")
    return 0


def _generate_tros(*, strict: bool = False) -> int:
    os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
    from generate_trace_tros import regenerate_all

    written, regressions = regenerate_all(strict=strict)
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


def _check_tros(*, strict: bool = False) -> int:
    os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
    from generate_trace_tros import generated_tros

    changed = False
    for path, payload in generated_tros(strict=strict):
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
        "--regional-manifest-uri",
        help=(
            "Optional regional release_manifest.json URI to merge into US "
            "Populace certification."
        ),
    )
    certify.add_argument(
        "--regional-artifact-prefix",
        help="Regional artifact prefix to import. Defaults to states/.",
    )
    certify.add_argument(
        "--regional-path-template",
        help="Region dataset path template to certify.",
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
        help=(
            "Skip reachability checks for the certified dataset and any "
            "vendored/regional artifacts."
        ),
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

    spm = subparsers.add_parser(
        "set-spm", help="Stage SPM defaults and optional verified PyPI calculator pin."
    )
    spm.add_argument("--forecast-content-sha256", required=True)
    spm.add_argument("--scenario", required=True)
    spm.add_argument(
        "--geography-kind", choices=["county", "metro", "national"], default="county"
    )
    spm.add_argument("--geography-id")
    spm.add_argument("--county-vintage", default="2020")
    spm.add_argument("--as-of")
    spm.add_argument(
        "--calculator-version",
        help="Verify actual published wheel bytes before adding the runtime dependency.",
    )
    spm.set_defaults(func=_set_spm)

    development = subparsers.add_parser(
        "development-manifest",
        help="Write an uncertified fixture using actual local wheel metadata.",
    )
    development.add_argument("--country-wheel", required=True, type=Path)
    development.add_argument("--calculator-wheel", required=True, type=Path)
    development.add_argument("--output", required=True, type=Path)
    development.set_defaults(func=_development_manifest)

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
        "--published-spm",
        action="store_true",
        help="Check SPM measurement pins include a published hashed calculator; does not certify country/data compatibility or release readiness.",
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

    for command in (generate, check):
        command.add_argument(
            "--strict-tros",
            action="store_true",
            help="Require full authenticated manifests matching reviewed TRO source pins; requires --include-tros.",
        )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if getattr(args, "strict_tros", False) and not args.include_tros:
        parser.error("--strict-tros requires --include-tros")
    try:
        return args.func(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
