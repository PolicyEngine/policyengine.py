"""Regenerate bundled TRACE TRO artifacts for every certified bundle country.

Writes ``data/bundle/{country}.trace.tro.jsonld`` for each country whose
certified data release ships in the bundle manifest. Run this before
releasing a new ``policyengine.py`` version so the packaged TRO
matches the pinned bundle. The richer data release manifest is included
when available; otherwise the TRO still binds the certified dataset
sha256 and URI pinned in the bundle manifest.
"""

from __future__ import annotations

import json
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

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_MANIFEST = (
    REPO_ROOT / "src" / "policyengine" / "data" / "bundle" / "manifest.json"
)
BUNDLE_TRO_DIR = REPO_ROOT / "src" / "policyengine" / "data" / "bundle"


def regenerate_all() -> tuple[list[Path], list[tuple[str, Path, str]]]:
    written: list[Path] = []
    regressions: list[tuple[str, Path, str]] = []
    for tro_path, payload in generated_tros():
        tro_path.write_bytes(payload)
        written.append(tro_path)
    return written, regressions


def generated_tros() -> list[tuple[Path, bytes]]:
    payloads: list[tuple[Path, bytes]] = []
    bundle = json.loads(BUNDLE_MANIFEST.read_text())
    BUNDLE_TRO_DIR.mkdir(parents=True, exist_ok=True)
    for country_id in sorted(bundle.get("data_releases", {})):
        tro_path = BUNDLE_TRO_DIR / f"{country_id}.trace.tro.jsonld"
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
            model_wheel_sha256=country_manifest.model_package.sha256,
            model_wheel_url=country_manifest.model_package.wheel_url,
        )
        payloads.append((tro_path, serialize_trace_tro(tro)))
    return payloads


def main() -> int:
    if not BUNDLE_MANIFEST.is_file():
        print(f"no bundle manifest at {BUNDLE_MANIFEST}", file=sys.stderr)
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
