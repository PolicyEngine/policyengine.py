from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from .archive import (
    extract_bundle_archive,
    load_country_bundles,
    validate_bundle_manifest,
)
from .constants import (
    DEFAULT_BUNDLE_DIR,
    DEFAULT_PYPROJECT,
    DEFAULT_RELEASE_MANIFEST_DIR,
)
from .country_manifest import write_country_release_manifests
from .digest import verify_bundle_digest
from .io import load_json, required_dict, required_string
from .pyproject import update_optional_dependency_pins
from .types import BundleImportResult, TroRegenerator


def import_policyengine_bundle(
    archive_path: Path,
    *,
    manifest_dir: Path = DEFAULT_RELEASE_MANIFEST_DIR,
    pyproject_path: Path = DEFAULT_PYPROJECT,
    update_pyproject: bool = True,
    regenerate_tros: bool = True,
    bundle_dir: Optional[Path] = DEFAULT_BUNDLE_DIR,
    changelog_dir: Optional[Path] = None,
    tro_regenerator: Optional[TroRegenerator] = None,
) -> BundleImportResult:
    """Import a schema-v2 ``policyengine-bundles`` archive.

    The runtime contract in policyengine.py remains the existing per-country
    ``CountryReleaseManifest`` schema. This function accepts the newer
    registry-only bundle archive and translates each country bundle into that
    stable runtime shape.
    """

    archive_path = Path(archive_path)
    with tempfile.TemporaryDirectory() as temp_dir:
        unpacked_bundle_dir = extract_bundle_archive(
            archive_path=archive_path,
            output_dir=Path(temp_dir) / "unpacked",
        )
        bundle = load_json(unpacked_bundle_dir / "bundle.json")
        validate_bundle_manifest(bundle, unpacked_bundle_dir)
        verify_bundle_digest(unpacked_bundle_dir, bundle)

        copied_bundle_dir = None
        if bundle_dir is not None:
            copied_bundle_dir = Path(bundle_dir)
            if copied_bundle_dir.exists():
                shutil.rmtree(copied_bundle_dir)
            shutil.copytree(unpacked_bundle_dir, copied_bundle_dir)
            source_bundle_dir = copied_bundle_dir
        else:
            source_bundle_dir = unpacked_bundle_dir

        country_bundles = load_country_bundles(
            bundle_dir=source_bundle_dir,
            bundle=bundle,
        )
        release_manifest_paths = write_country_release_manifests(
            country_bundles=country_bundles,
            manifest_dir=manifest_dir,
        )

    updated_pyproject = None
    if update_pyproject:
        update_optional_dependency_pins(
            pyproject_path=pyproject_path,
            country_bundles=country_bundles,
        )
        updated_pyproject = pyproject_path

    trace_tro_paths: list[Path] = []
    if regenerate_tros:
        trace_tro_paths = regenerate_trace_tros(
            countries=sorted(country_bundles),
            manifest_dir=manifest_dir,
            tro_regenerator=tro_regenerator,
        )

    changelog_path = None
    if changelog_dir is not None:
        changelog_path = write_changelog_fragment(
            changelog_dir=changelog_dir,
            bundle=bundle,
            country_bundles=country_bundles,
        )

    return BundleImportResult(
        bundle_version=required_string(bundle, "bundle_version"),
        countries=sorted(country_bundles),
        bundle_dir=copied_bundle_dir,
        release_manifest_paths=release_manifest_paths,
        pyproject_path=updated_pyproject,
        trace_tro_paths=trace_tro_paths,
        changelog_path=changelog_path,
    )


def regenerate_trace_tros(
    *,
    countries: list[str],
    manifest_dir: Path,
    tro_regenerator: Optional[TroRegenerator],
) -> list[Path]:
    if tro_regenerator is None:
        from policyengine.provenance.bundle import regenerate_trace_tro

        tro_regenerator = regenerate_trace_tro
    return [tro_regenerator(country, manifest_dir) for country in countries]


def write_changelog_fragment(
    *,
    changelog_dir: Path,
    bundle: dict,
    country_bundles: dict[str, dict],
) -> Path:
    bundle_version = required_string(bundle, "bundle_version")
    changelog_dir.mkdir(parents=True, exist_ok=True)
    path = changelog_dir / f"policyengine-bundle-{bundle_version}.changed.md"
    package_fragments = []
    for country_id, country_bundle in sorted(country_bundles.items()):
        model_package = required_dict(country_bundle, "model_package")
        package_fragments.append(
            f"{country_id}: {required_string(model_package, 'name')} "
            f"{required_string(model_package, 'version')}"
        )
    path.write_text(
        f"Import PolicyEngine bundle {bundle_version} "
        f"({'; '.join(package_fragments)}).\n"
    )
    return path
