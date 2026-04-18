"""Regenerate bundled TRACE TRO artifacts for every country release manifest.

Writes ``data/release_manifests/{country}.trace.tro.jsonld`` for each
country whose bundled manifest ships in the wheel. Run this before
releasing a new ``policyengine.py`` version so the packaged TRO
matches the pinned bundle. Requires HTTPS access to the data release
manifest (and ``HUGGING_FACE_TOKEN`` for private country data).

If a country previously had a TRO on disk and the new run cannot
regenerate it (e.g. a missing secret or an unreachable HF endpoint),
the script exits non-zero so the release workflow blocks rather than
silently shipping a stale/missing TRO. If no bundled release manifests
are found at all, the script exits 0 with a notice (nothing to do).
"""

from __future__ import annotations

import sys
from pathlib import Path

from policyengine.core.release_manifest import (
    DataReleaseManifestUnavailableError,
    get_data_release_manifest,
    get_release_manifest,
)
from policyengine.core.trace_tro import (
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
            if tro_path.exists():
                regressions.append((country_id, tro_path, str(exc)))
            else:
                print(
                    f"skipped {country_id}: {exc}",
                    file=sys.stderr,
                )
            continue
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
