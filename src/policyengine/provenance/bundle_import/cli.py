from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .api import import_policyengine_bundle
from .constants import (
    DEFAULT_BUNDLE_DIR,
    DEFAULT_CHANGELOG_DIR,
    DEFAULT_PYPROJECT,
    DEFAULT_RELEASE_MANIFEST_DIR,
)
from .types import BundleImportError


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import a schema-v2 policyengine-bundles archive into policyengine.py. "
            "The importer verifies the bundle digest, vendors the exploded bundle, "
            "writes .py release manifests, updates country extras, and regenerates "
            "TRACE TRO sidecars."
        )
    )
    parser.add_argument(
        "--archive",
        required=True,
        type=Path,
        help="Path to policyengine-bundle-<version>.tar.gz.",
    )
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR)
    parser.add_argument(
        "--release-manifest-dir",
        type=Path,
        default=DEFAULT_RELEASE_MANIFEST_DIR,
    )
    parser.add_argument("--pyproject", type=Path, default=DEFAULT_PYPROJECT)
    parser.add_argument("--changelog-dir", type=Path, default=DEFAULT_CHANGELOG_DIR)
    parser.add_argument(
        "--no-pyproject",
        action="store_true",
        help="Do not update pyproject optional dependency pins.",
    )
    parser.add_argument(
        "--no-tro",
        action="store_true",
        help="Do not regenerate TRACE TRO sidecar files.",
    )
    parser.add_argument(
        "--no-changelog",
        action="store_true",
        help="Do not write a towncrier changelog fragment.",
    )
    args = parser.parse_args(argv)

    try:
        imported = import_policyengine_bundle(
            args.archive,
            bundle_dir=args.bundle_dir,
            manifest_dir=args.release_manifest_dir,
            pyproject_path=args.pyproject,
            update_pyproject=not args.no_pyproject,
            regenerate_tros=not args.no_tro,
            changelog_dir=None if args.no_changelog else args.changelog_dir,
        )
    except BundleImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"imported bundle: {imported.bundle_version}")
    print(f"countries: {', '.join(imported.countries)}")
    if imported.bundle_dir is not None:
        print(f"vendored bundle: {imported.bundle_dir}")
    for manifest_path in imported.release_manifest_paths:
        print(f"release manifest: {manifest_path}")
    if imported.pyproject_path is not None:
        print(f"updated pyproject: {imported.pyproject_path}")
    for tro_path in imported.trace_tro_paths:
        print(f"trace tro: {tro_path}")
    if imported.changelog_path is not None:
        print(f"changelog: {imported.changelog_path}")
    return 0
