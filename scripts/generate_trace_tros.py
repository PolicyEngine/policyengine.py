"""Regenerate bundled TRACE TRO artifacts for every country release manifest.

Writes ``data/release_manifests/{country}.trace.tro.jsonld`` for each
country whose bundled manifest ships in the wheel. Run this before
releasing a new ``policyengine.py`` version so the packaged TRO
matches the pinned bundle. Requires HTTPS access to the data release
manifest (and ``HUGGING_FACE_TOKEN`` for private country data).
Countries whose data release manifest is unreachable are skipped with
a warning so the step can run without all credentials; those TROs can
be regenerated in a later release.
"""

from __future__ import annotations

import sys
from importlib.resources import files
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


def regenerate_all() -> tuple[list[Path], list[tuple[str, str]]]:
    manifest_root = Path(
        str(files("policyengine").joinpath("data", "release_manifests"))
    )
    written: list[Path] = []
    skipped: list[tuple[str, str]] = []
    for manifest_path in sorted(manifest_root.glob("*.json")):
        country_id = manifest_path.stem
        country_manifest = get_release_manifest(country_id)
        try:
            data_release_manifest = get_data_release_manifest(country_id)
        except DataReleaseManifestUnavailableError as exc:
            skipped.append((country_id, str(exc)))
            continue
        tro = build_trace_tro_from_release_bundle(
            country_manifest,
            data_release_manifest,
            certification=country_manifest.certification,
        )
        out_path = manifest_path.with_suffix(".trace.tro.jsonld")
        out_path.write_bytes(serialize_trace_tro(tro))
        written.append(out_path)
    return written, skipped


def main() -> int:
    written, skipped = regenerate_all()
    for path in written:
        print(f"wrote {path}")
    for country_id, reason in skipped:
        print(f"skipped {country_id}: {reason}", file=sys.stderr)
    if not written and not skipped:
        print("no release manifests found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
