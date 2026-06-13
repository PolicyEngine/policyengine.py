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
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
