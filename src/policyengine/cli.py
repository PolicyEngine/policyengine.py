"""Command-line entry point for policyengine.

Subcommands:

- ``trace-tro <country>`` emit a TRACE TRO for a certified bundle
- ``trace-tro-validate <path>`` validate a TRO against the shipped schema
- ``trace-tro-verify <path>`` fetch and rehash every artifact a TRO claims
- ``release-manifest <country>`` print the bundled country manifest

See :mod:`policyengine.provenance.trace` and ``docs/release-bundles.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import files
from pathlib import Path
from typing import Optional, Sequence

from policyengine.bundle import (
    BundleError,
    inspect_bundle_status,
    install_bundle,
    load_bundle_manifest,
)
from policyengine.provenance.manifest import (
    DataReleaseManifestUnavailableError,
    get_data_release_manifest,
    get_release_manifest,
)
from policyengine.provenance.trace import (
    build_trace_tro_from_release_bundle,
    serialize_trace_tro,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="policyengine",
        description="PolicyEngine reproducibility and release tooling.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    tro = subparsers.add_parser(
        "trace-tro",
        help="Emit a TRACE Transparent Research Object for a certified bundle.",
    )
    tro.add_argument("country", help="Country id (e.g. us, uk).")
    tro.add_argument(
        "--out",
        "-o",
        type=Path,
        default=None,
        help="Write the TRO to this path. Defaults to stdout.",
    )

    validate = subparsers.add_parser(
        "trace-tro-validate",
        help="Validate a TRO file against the shipped JSON Schema.",
    )
    validate.add_argument("path", type=Path, help="Path to a .trace.tro.jsonld file.")

    verify = subparsers.add_parser(
        "trace-tro-verify",
        help=(
            "Fetch every artifact the TRO claims, rehash it, and check the "
            "composition fingerprint. Relative locations resolve against the "
            "TRO file's directory, so a self-contained run record verifies "
            "offline."
        ),
    )
    verify.add_argument("path", type=Path, help="Path to a .trace.tro.jsonld file.")
    verify.add_argument(
        "--base-dir",
        type=Path,
        default=None,
        help=(
            "Directory for resolving relative artifact locations. Defaults "
            "to the TRO file's directory."
        ),
    )
    verify.add_argument(
        "--skip",
        action="append",
        default=[],
        metavar="ARTIFACT_ID",
        help=(
            "Short artifact id to skip (e.g. a restricted-access dataset). "
            "May be repeated. Skipped artifacts are listed but do not fail "
            "verification."
        ),
    )

    bundle = subparsers.add_parser(
        "release-manifest",
        help=(
            "Print the bundled country release manifest as JSON. Use this to "
            "inspect the pinned model/data versions shipped with this "
            "policyengine release."
        ),
    )
    bundle.add_argument("country", help="Country id (e.g. us, uk).")

    bundle = subparsers.add_parser(
        "bundle",
        help="Install, inspect, or verify a PolicyEngine bundle.",
    )
    bundle_subparsers = bundle.add_subparsers(
        dest="bundle_command",
        required=True,
    )

    bundle_install = bundle_subparsers.add_parser(
        "install",
        help="Install a bundle's package scaffold and certified datasets.",
    )
    bundle_install.add_argument(
        "version",
        nargs="?",
        help="Bundle version to install. Defaults to the newest packaged bundle.",
    )
    bundle_install.add_argument(
        "--manifest",
        help="Custom bundle manifest path or URL.",
    )
    bundle_install.add_argument(
        "--python",
        help=(
            "Python interpreter to install the package scaffold into. Defaults "
            "to the active environment, or ./.venv when run from uvx/pipx."
        ),
    )
    bundle_install.add_argument(
        "--venv",
        type=Path,
        help=(
            "Virtual environment to create or reuse as the installation target. "
            "Defaults to ./.venv when run from uvx/pipx."
        ),
    )
    bundle_install.add_argument(
        "--country",
        action="append",
        choices=("us", "uk"),
        help="Country to include. Repeat for multiple countries. Defaults to all.",
    )
    bundle_install.add_argument(
        "--no-datasets",
        action="store_true",
        help="Install packages without downloading certified datasets.",
    )
    bundle_install.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data"),
        help="Directory for certified dataset files and the bundle receipt.",
    )
    bundle_install.add_argument(
        "--yes",
        action="store_true",
        help="Confirm dataset downloads non-interactively.",
    )
    bundle_install.add_argument(
        "--dry-run",
        action="store_true",
        help="Print installation actions without changing packages or datasets.",
    )

    bundle_status = bundle_subparsers.add_parser(
        "status",
        help="Show local package and dataset status for a bundle.",
    )
    bundle_status.add_argument("version", nargs="?", help="Bundle version to compare.")
    bundle_status.add_argument("--manifest", help="Custom bundle manifest path or URL.")
    bundle_status.add_argument(
        "--python",
        help=(
            "Python interpreter to inspect. Defaults to the receipt target, "
            "then the current process."
        ),
    )
    bundle_status.add_argument(
        "--venv",
        type=Path,
        help=(
            "Virtual environment to inspect. Defaults to the receipt target, "
            "then the current process."
        ),
    )
    bundle_status.add_argument(
        "--country",
        action="append",
        choices=("us", "uk"),
        help="Country to inspect. Repeat for multiple countries. Defaults to all.",
    )
    bundle_status.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data"),
        help="Directory containing the bundle receipt and datasets.",
    )
    bundle_status.add_argument(
        "--json",
        action="store_true",
        help="Print the full status report as JSON.",
    )
    bundle_status.add_argument(
        "--packages-only",
        action="store_true",
        help="Skip dataset receipt checks and verify only installed packages.",
    )

    bundle_verify = bundle_subparsers.add_parser(
        "verify",
        help="Verify local packages and datasets against a bundle.",
    )
    bundle_verify.add_argument("version", nargs="?", help="Bundle version to verify.")
    bundle_verify.add_argument("--manifest", help="Custom bundle manifest path or URL.")
    bundle_verify.add_argument(
        "--python",
        help=(
            "Python interpreter to inspect. Defaults to the receipt target, "
            "then the current process."
        ),
    )
    bundle_verify.add_argument(
        "--venv",
        type=Path,
        help=(
            "Virtual environment to inspect. Defaults to the receipt target, "
            "then the current process."
        ),
    )
    bundle_verify.add_argument(
        "--country",
        action="append",
        choices=("us", "uk"),
        help="Country to verify. Repeat for multiple countries. Defaults to all.",
    )
    bundle_verify.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data"),
        help="Directory containing the bundle receipt and datasets.",
    )
    bundle_verify.add_argument(
        "--json",
        action="store_true",
        help="Print the full verification report as JSON.",
    )
    bundle_verify.add_argument(
        "--packages-only",
        action="store_true",
        help="Skip dataset receipt checks and verify only installed packages.",
    )

    bundle_manifest = bundle_subparsers.add_parser(
        "manifest",
        help="Print a bundle manifest as JSON.",
    )
    bundle_manifest.add_argument("version", nargs="?", help="Bundle version to print.")
    bundle_manifest.add_argument(
        "--manifest", help="Custom bundle manifest path or URL."
    )

    return parser


def _emit_bundle_tro(country_id: str, out: Optional[Path]) -> int:
    country_manifest = get_release_manifest(country_id)
    try:
        data_release_manifest = get_data_release_manifest(country_id)
    except DataReleaseManifestUnavailableError:
        data_release_manifest = None
    tro = build_trace_tro_from_release_bundle(
        country_manifest,
        data_release_manifest,
        certification=country_manifest.certification,
    )
    payload = serialize_trace_tro(tro)
    if out is None:
        sys.stdout.buffer.write(payload)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload)
    return 0


def _validate_tro(path: Path) -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print(
            "error: jsonschema is required for trace-tro-validate. "
            "Install with: pip install jsonschema",
            file=sys.stderr,
        )
        return 1
    schema_path = Path(
        str(files("policyengine").joinpath("data", "schemas", "trace_tro.schema.json"))
    )
    schema = json.loads(schema_path.read_text())
    payload = json.loads(path.read_text())
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    if errors:
        print(f"error: {path} is invalid against the TRO schema:", file=sys.stderr)
        for error in errors:
            print(f"  - {error.message}", file=sys.stderr)
        return 1
    print(f"ok: {path}")
    return 0


def _verify_tro(path: Path, base_dir: Optional[Path], skip: Sequence[str]) -> int:
    from policyengine.provenance.verify import verify_trace_tro

    tro = json.loads(path.read_text())
    report = verify_trace_tro(tro, base_dir=base_dir or path.parent, skip=skip)
    for check in report.artifacts:
        if check.status == "ok":
            print(f"ok: {check.artifact_id} ({check.location})")
        elif check.status == "skipped":
            print(f"skipped: {check.artifact_id}")
        else:
            print(f"{check.status}: {check.artifact_id} — {check.detail}")
    print(f"fingerprint: {report.fingerprint_status}")
    if report.ok:
        print(f"ok: {path}")
        return 0
    print(f"error: {path} failed verification", file=sys.stderr)
    return 1


def _emit_release_manifest(country_id: str) -> int:
    manifest = get_release_manifest(country_id)
    print(json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def _install_bundle(args: argparse.Namespace) -> int:
    try:
        result = install_bundle(
            args.version,
            manifest_ref=args.manifest,
            python=args.python,
            venv=args.venv,
            countries=args.country,
            data_dir=args.data_dir,
            no_datasets=args.no_datasets,
            yes=args.yes,
            dry_run=args.dry_run,
        )
    except BundleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _bundle_status(args: argparse.Namespace) -> int:
    try:
        report = inspect_bundle_status(
            args.version,
            manifest_ref=args.manifest,
            python=args.python,
            venv=args.venv,
            countries=args.country,
            data_dir=args.data_dir,
            packages_only=args.packages_only,
        )
    except BundleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        status = "matched" if report["matched"] else "mismatch"
        print(f"PolicyEngine bundle {report['bundle_version']}: {status}")
        if report["target_python"]:
            print(f"target Python: {report['target_python']}")
        for check in report["packages"]:
            installed = check.get("installed_version", "missing")
            print(
                f"- {check['package']}: {check['status']} "
                f"(expected {check['expected_version']}, installed {installed})"
            )
        for check in report["datasets"]:
            installed = check.get("installed_version", "missing")
            print(
                f"- {check['country']} dataset {check['dataset']}: "
                f"{check['status']} (expected {check['expected_version']}, "
                f"installed {installed})"
            )
    return 0 if report["matched"] else 1


def _bundle_verify(args: argparse.Namespace) -> int:
    try:
        report = inspect_bundle_status(
            args.version,
            manifest_ref=args.manifest,
            python=args.python,
            venv=args.venv,
            countries=args.country,
            data_dir=args.data_dir,
            packages_only=args.packages_only,
        )
    except BundleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"PolicyEngine bundle {report['bundle_version']}: "
            f"{'ok' if report['matched'] else 'failed'}"
        )
    return 0 if report["matched"] else 1


def _emit_bundle_manifest(args: argparse.Namespace) -> int:
    try:
        manifest = load_bundle_manifest(args.version, manifest_ref=args.manifest)
    except BundleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "trace-tro":
        return _emit_bundle_tro(args.country, args.out)
    if args.command == "trace-tro-validate":
        return _validate_tro(args.path)
    if args.command == "trace-tro-verify":
        return _verify_tro(args.path, args.base_dir, args.skip)
    if args.command == "release-manifest":
        return _emit_release_manifest(args.country)
    if args.command == "bundle":
        if args.bundle_command == "install":
            return _install_bundle(args)
        if args.bundle_command == "status":
            return _bundle_status(args)
        if args.bundle_command == "verify":
            return _bundle_verify(args)
        if args.bundle_command == "manifest":
            return _emit_bundle_manifest(args)
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
