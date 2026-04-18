"""Command-line entry point for policyengine.

Exposes a ``trace-tro`` subcommand that emits a TRACE TRO for a
certified country bundle. The TRO is the standards-based provenance
surface on top of the release manifests: see
:mod:`policyengine.core.trace_tro` and ``docs/release-bundles.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from policyengine.core.release_manifest import (
    DataReleaseManifestUnavailableError,
    get_data_release_manifest,
    get_release_manifest,
)
from policyengine.core.trace_tro import (
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
    tro.add_argument(
        "--offline",
        action="store_true",
        help=(
            "Skip fetching the data release manifest over HTTPS. Requires "
            "the bundled manifest to include a data release manifest for "
            "the pinned data package version."
        ),
    )

    bundle = subparsers.add_parser(
        "release-manifest",
        help="Print the bundled country release manifest as JSON.",
    )
    bundle.add_argument("country", help="Country id (e.g. us, uk).")

    return parser


def _emit_bundle_tro(country_id: str, out: Optional[Path], *, offline: bool) -> int:
    country_manifest = get_release_manifest(country_id)
    try:
        data_release_manifest = get_data_release_manifest(country_id)
    except DataReleaseManifestUnavailableError as exc:
        if offline:
            print(
                f"error: data release manifest for '{country_id}' is not "
                "available in offline mode.",
                file=sys.stderr,
            )
            return 2
        raise exc
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


def _emit_release_manifest(country_id: str) -> int:
    manifest = get_release_manifest(country_id)
    print(json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "trace-tro":
        return _emit_bundle_tro(args.country, args.out, offline=args.offline)
    if args.command == "release-manifest":
        return _emit_release_manifest(args.country)
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
