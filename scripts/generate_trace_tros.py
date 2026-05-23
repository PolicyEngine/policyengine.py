"""Regenerate bundled TRACE TRO artifacts for every country release manifest.

Writes ``data/release_manifests/{country}.trace.tro.jsonld`` for each
country whose bundled manifest ships in the wheel. Run this before
releasing a new ``policyengine.py`` version so the packaged TRO
matches the pinned bundle. The richer data release manifest is included
when available; otherwise the TRO still binds the certified dataset
sha256 and URI pinned in the bundled release manifest.
"""

from __future__ import annotations

import sys
from pathlib import Path

from policyengine.provenance.manifest import (
    DataReleaseManifestUnavailableError,
    get_data_release_manifest,
    get_release_manifest,
)
from policyengine.provenance.trace import (
    build_trace_tro_from_release_bundle,
    serialize_trace_tro,
)

MANIFEST_DIR = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "policyengine"
    / "data"
    / "release_manifests"
)


def regenerate_all() -> tuple[list[Path], list[tuple[str, Path, str]]]:
    written: list[Path] = []
    regressions: list[tuple[str, Path, str]] = []
    for manifest_path in sorted(MANIFEST_DIR.glob("*.json")):
        country_id = manifest_path.stem
        tro_path = manifest_path.with_suffix(".trace.tro.jsonld")
        country_manifest = get_release_manifest(country_id)
        try:
            data_release_manifest = get_data_release_manifest(country_id)
        except DataReleaseManifestUnavailableError as exc:
            data_release_manifest = None
            print(
                f"warning: {country_id}: {exc}; writing limited TRO",
                file=sys.stderr,
            )
        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            data_release_manifest,
            certification=country_manifest.certification,
        )
        tro_path.write_bytes(serialize_trace_tro(tro))
        written.append(tro_path)
    return written, regressions


def main() -> int:
    if not MANIFEST_DIR.is_dir():
        print(f"no manifest dir at {MANIFEST_DIR}", file=sys.stderr)
        return 1
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


if __name__ == "__main__":
    raise SystemExit(main())
