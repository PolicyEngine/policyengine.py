"""Regenerate bundled TRACE TRO artifacts for every country release manifest.

Writes ``data/release_manifests/{country}.trace.tro.jsonld`` for each
country whose bundled manifest ships in the wheel. Run this before
releasing a new ``policyengine.py`` version so the packaged TRO
matches the pinned bundle. Network access is required to fetch the
data release manifest and model wheel hash.
"""

from __future__ import annotations

import sys
from importlib.resources import files
from pathlib import Path

from policyengine.core.release_manifest import (
    get_data_release_manifest,
    get_release_manifest,
)
from policyengine.core.trace_tro import (
    build_trace_tro_from_release_bundle,
    serialize_trace_tro,
)


def regenerate_all() -> list[Path]:
    manifest_root = Path(
        str(files("policyengine").joinpath("data", "release_manifests"))
    )
    written: list[Path] = []
    for manifest_path in sorted(manifest_root.glob("*.json")):
        country_id = manifest_path.stem
        country_manifest = get_release_manifest(country_id)
        data_release_manifest = get_data_release_manifest(country_id)
        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            data_release_manifest,
            certification=country_manifest.certification,
        )
        out_path = manifest_path.with_suffix(".trace.tro.jsonld")
        out_path.write_bytes(serialize_trace_tro(tro))
        written.append(out_path)
    return written


def main() -> int:
    paths = regenerate_all()
    for path in paths:
        print(f"wrote {path}")
    if not paths:
        print("no release manifests found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
