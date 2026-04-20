"""Command-line entry point for policyengine.

Subcommands:

- ``trace-tro <country>`` emit a TRACE TRO for a certified bundle
- ``trace-tro-validate <path>`` validate a TRO against the shipped schema
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
    data_release_manifest = get_data_release_manifest(country_id)
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
    if args.command == "release-manifest":
        return _emit_release_manifest(args.country)
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
