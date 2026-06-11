from __future__ import annotations

import json
import tarfile
from pathlib import Path
from typing import Optional

import pytest

from policyengine.provenance import bundle_import


def test_import_policyengine_bundle_imports_schema_v2_archive(
    tmp_path: Path,
) -> None:
    archive_path = _write_bundle_archive(tmp_path, version="4.15.0")
    bundle_dir = tmp_path / "vendored-bundle"
    manifest_dir = tmp_path / "release_manifests"
    pyproject_path = _write_pyproject(tmp_path)
    changelog_dir = tmp_path / "changelog.d"

    def fake_tro_regenerator(country: str, output_dir: Path) -> Path:
        path = output_dir / f"{country}.trace.tro.jsonld"
        path.write_text(f"{country}\n")
        return path

    result = bundle_import.import_policyengine_bundle(
        archive_path,
        bundle_dir=bundle_dir,
        manifest_dir=manifest_dir,
        pyproject_path=pyproject_path,
        changelog_dir=changelog_dir,
        tro_regenerator=fake_tro_regenerator,
    )

    assert result.bundle_version == "4.15.0"
    assert result.countries == ["uk", "us"]
    assert (bundle_dir / "bundle.json").exists()
    assert result.bundle_dir == bundle_dir
    assert {path.name for path in result.release_manifest_paths} == {
        "uk.json",
        "us.json",
    }
    assert {path.name for path in result.trace_tro_paths} == {
        "uk.trace.tro.jsonld",
        "us.trace.tro.jsonld",
    }

    us_manifest = json.loads((manifest_dir / "us.json").read_text())
    assert us_manifest["schema_version"] == 1
    assert us_manifest["bundle_id"] == "us-4.15.0"
    assert us_manifest["policyengine_version"] == "4.15.0"
    assert us_manifest["model_package"]["version"] == "1.722.4"
    assert us_manifest["datasets"]["enhanced_cps_2024"] == {
        "path": "enhanced_cps_2024.h5",
        "revision": "data-sha",
        "sha256": "b" * 64,
        "metadata_sha256": "c" * 64,
        "repo_id": "policyengine/policyengine-us-data",
    }
    assert (
        us_manifest["certified_data_artifact"]["uri"]
        == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@data-sha"
    )
    assert (
        us_manifest["certified_data_artifact"]["build_id"]
        == "policyengine-us-data-1.0.0"
    )
    assert us_manifest["certification"]["compatibility_basis"] == "bundle_candidate"
    assert us_manifest["certification"]["certified_by"] == "policyengine-bundles"
    assert us_manifest["certification"]["certified_for_model_version"] == "1.722.4"
    assert us_manifest["certification"]["data_build_fingerprint"] == (
        "sha256:" + "d" * 64
    )

    pyproject = pyproject_path.read_text()
    assert '"policyengine_core>=3.26.1"' in pyproject
    assert '"policyengine-us==1.722.4"' in pyproject
    assert '"policyengine-uk==3.0.0"' in pyproject
    assert (changelog_dir / "policyengine-bundle-4.15.0.changed.md").exists()


def test_import_policyengine_bundle_rejects_schema_v1_archive(
    tmp_path: Path,
) -> None:
    archive_path = _write_bundle_archive(
        tmp_path,
        version="4.15.0",
        schema_version=1,
    )

    with pytest.raises(bundle_import.BundleImportError, match="schema v2"):
        bundle_import.import_policyengine_bundle(
            archive_path,
            bundle_dir=tmp_path / "vendored-bundle",
            manifest_dir=tmp_path / "release_manifests",
            pyproject_path=_write_pyproject(tmp_path),
            regenerate_tros=False,
        )


def test_import_policyengine_bundle_rejects_digest_mismatch(
    tmp_path: Path,
) -> None:
    archive_path = _write_bundle_archive(
        tmp_path,
        version="4.15.0",
        bundle_digest="sha256:" + "0" * 64,
    )

    with pytest.raises(bundle_import.BundleImportError, match="bundle_digest"):
        bundle_import.import_policyengine_bundle(
            archive_path,
            bundle_dir=tmp_path / "vendored-bundle",
            manifest_dir=tmp_path / "release_manifests",
            pyproject_path=_write_pyproject(tmp_path),
            regenerate_tros=False,
        )


def test_import_policyengine_bundle_rejects_missing_default_dataset(
    tmp_path: Path,
) -> None:
    archive_path = _write_bundle_archive(
        tmp_path,
        version="4.15.0",
        missing_default_dataset=True,
    )

    with pytest.raises(bundle_import.BundleImportError, match="missing_dataset"):
        bundle_import.import_policyengine_bundle(
            archive_path,
            bundle_dir=tmp_path / "vendored-bundle",
            manifest_dir=tmp_path / "release_manifests",
            pyproject_path=_write_pyproject(tmp_path),
            regenerate_tros=False,
        )


def test_import_policyengine_bundle_wraps_invalid_generated_manifest(
    tmp_path: Path,
) -> None:
    archive_path = _write_bundle_archive(
        tmp_path,
        version="4.15.0",
        invalid_data_package_repo_type=True,
    )

    with pytest.raises(bundle_import.BundleImportError, match="us is invalid"):
        bundle_import.import_policyengine_bundle(
            archive_path,
            bundle_dir=tmp_path / "vendored-bundle",
            manifest_dir=tmp_path / "release_manifests",
            pyproject_path=_write_pyproject(tmp_path),
            regenerate_tros=False,
        )


def test_import_policyengine_bundle_can_skip_pyproject_and_tros(
    tmp_path: Path,
) -> None:
    archive_path = _write_bundle_archive(tmp_path, version="4.15.0")
    pyproject_path = _write_pyproject(tmp_path)
    original_pyproject = pyproject_path.read_text()

    result = bundle_import.import_policyengine_bundle(
        archive_path,
        bundle_dir=None,
        manifest_dir=tmp_path / "release_manifests",
        pyproject_path=pyproject_path,
        update_pyproject=False,
        regenerate_tros=False,
    )

    assert result.bundle_dir is None
    assert result.pyproject_path is None
    assert result.trace_tro_paths == []
    assert pyproject_path.read_text() == original_pyproject


def test_import_policyengine_bundle_updates_only_countries_in_archive(
    tmp_path: Path,
) -> None:
    archive_path = _write_bundle_archive(
        tmp_path,
        version="4.15.0",
        countries=("us",),
    )
    manifest_dir = tmp_path / "release_manifests"
    pyproject_path = _write_pyproject(tmp_path)

    result = bundle_import.import_policyengine_bundle(
        archive_path,
        bundle_dir=None,
        manifest_dir=manifest_dir,
        pyproject_path=pyproject_path,
        regenerate_tros=False,
    )

    assert result.countries == ["us"]
    assert {path.name for path in result.release_manifest_paths} == {"us.json"}
    assert (manifest_dir / "us.json").exists()
    assert not (manifest_dir / "uk.json").exists()
    pyproject = pyproject_path.read_text()
    assert '"policyengine-us==1.722.4"' in pyproject
    assert '"policyengine-uk==2.88.20"' in pyproject


def test_import_policyengine_bundle_cli_smoke(tmp_path: Path, capsys) -> None:
    archive_path = _write_bundle_archive(tmp_path, version="4.15.0")
    exit_code = bundle_import.main(
        [
            "--archive",
            str(archive_path),
            "--bundle-dir",
            str(tmp_path / "vendored-bundle"),
            "--release-manifest-dir",
            str(tmp_path / "release_manifests"),
            "--pyproject",
            str(_write_pyproject(tmp_path)),
            "--changelog-dir",
            str(tmp_path / "changelog.d"),
            "--no-tro",
        ]
    )

    assert exit_code == 0
    assert "imported bundle: 4.15.0" in capsys.readouterr().out


def _write_bundle_archive(
    tmp_path: Path,
    *,
    version: str,
    schema_version: int = 2,
    bundle_digest: Optional[str] = None,
    missing_default_dataset: bool = False,
    invalid_data_package_repo_type: bool = False,
    countries: tuple[str, ...] = ("us", "uk"),
) -> Path:
    bundle_root = tmp_path / f"policyengine-bundle-{version}"
    for country in countries:
        _write_json(
            bundle_root / "countries" / f"{country}.json",
            _country_bundle(
                country,
                version,
                missing_default_dataset=(missing_default_dataset and country == "us"),
                invalid_data_package_repo_type=(
                    invalid_data_package_repo_type and country == "us"
                ),
            ),
        )
    _write_json(bundle_root / "validation-report.json", _validation_report(version))
    bundle = _bundle_manifest(
        version,
        schema_version=schema_version,
        countries=countries,
    )
    _write_json(bundle_root / "bundle.json", bundle)
    bundle["bundle_digest"] = bundle_digest or (
        f"sha256:{bundle_import._bundle_directory_digest(bundle_root)}"
    )
    _write_json(bundle_root / "bundle.json", bundle)

    archive_path = tmp_path / f"policyengine-bundle-{version}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(bundle_root, arcname=bundle_root.name)
    return archive_path


def _bundle_manifest(
    version: str,
    *,
    schema_version: int,
    countries: tuple[str, ...],
) -> dict:
    return {
        "schema_version": schema_version,
        "bundle_version": version,
        "created_at": "2026-06-03T00:00:00Z",
        "policyengine": _package_pin("policyengine", version),
        "packages": {
            "policyengine": _package_pin("policyengine", version),
            "policyengine-core": _package_pin("policyengine-core", "3.26.1"),
            "policyengine-us": _package_pin("policyengine-us", "1.722.4"),
            "policyengine-uk": _package_pin("policyengine-uk", "3.0.0"),
        },
        "countries": {country: f"countries/{country}.json" for country in countries},
        "validation_report": "validation-report.json",
    }


def _country_bundle(
    country_id: str,
    version: str,
    *,
    missing_default_dataset: bool = False,
    invalid_data_package_repo_type: bool = False,
) -> dict:
    model_package = "policyengine-us" if country_id == "us" else "policyengine-uk"
    model_version = "1.722.4" if country_id == "us" else "3.0.0"
    data_package = (
        "policyengine-us-data" if country_id == "us" else "policyengine-uk-data"
    )
    repo_id = (
        "policyengine/policyengine-us-data"
        if country_id == "us"
        else "policyengine/policyengine-uk-data-private"
    )
    dataset = "enhanced_cps_2024" if country_id == "us" else "enhanced_frs_2023_24"
    path = f"{dataset}.h5"
    default_dataset = "missing_dataset" if missing_default_dataset else dataset
    return {
        "schema_version": 2,
        "bundle_version": version,
        "country_id": country_id,
        "model_package": _package_pin(model_package, model_version),
        "core_package": _package_pin("policyengine-core", "3.26.1"),
        "data_package": {
            "name": data_package,
            "version": "1.0.0",
            "repo_id": repo_id,
            "repo_type": 123 if invalid_data_package_repo_type else "model",
            "release_manifest_path": "release_manifest.json",
            "release_manifest_revision": "data-sha",
        },
        "artifact_release": {
            "repo_id": repo_id,
            "version": "data-sha",
            "repo_type": "model",
            "release_manifest_uri": f"hf://model/{repo_id}@data-sha/release_manifest.json",
            "release_manifest_sha256": "a" * 64,
        },
        "default_dataset": default_dataset,
        "datasets": {
            dataset: {
                "kind": "microdata",
                "uri": f"hf://model/{repo_id}@data-sha/{path}",
                "path": path,
                "repo_id": repo_id,
                "revision": "data-sha",
                "sha256": "b" * 64,
                "metadata_sha256": "c" * 64,
                "status": "certified",
            }
        },
        "region_datasets": {
            "national": {
                "path_template": path,
                "uri_template": f"hf://model/{repo_id}@data-sha/{path}",
            }
        },
        "compatibility": {
            "basis": "bundle_candidate",
            "model_package": _package_pin(model_package, model_version),
            "core_package": _package_pin("policyengine-core", "3.26.1"),
            "data_package": {"name": data_package, "version": "1.0.0"},
            "release_manifest_uri": f"hf://model/{repo_id}@data-sha/release_manifest.json",
            "release_manifest_sha256": "a" * 64,
            "asserted_by": "policyengine-bundles",
            "metadata": {
                "candidate_model_package": model_package,
                "candidate_data_release_manifest_uri": (
                    f"hf://model/{repo_id}@data-sha/release_manifest.json"
                ),
                "data_build_id": f"{data_package}-1.0.0",
                "built_with_model_version": model_version,
                "built_with_model_git_sha": "git-sha",
                "data_build_fingerprint": "sha256:" + "d" * 64,
            },
        },
    }


def _package_pin(name: str, version: str) -> dict:
    return {
        "name": name,
        "version": version,
        "resolution_status": "pinned",
        "sha256": "a" * 64,
        "wheel_url": f"https://example.test/{name}-{version}.whl",
    }


def _validation_report(version: str) -> dict:
    return {
        "schema_version": 2,
        "bundle_version": version,
        "generated_at": "2026-06-03T00:00:00Z",
        "status": "passed",
        "checks": [
            {
                "name": "registry_validation",
                "status": "passed",
                "command": "test",
                "started_at": "2026-06-03T00:00:00Z",
                "ended_at": "2026-06-03T00:00:01Z",
                "details": {
                    "validated_on_platform": "test",
                    "bundle_dir": "/tmp/bundle",
                },
            }
        ],
        "metadata": {"validation_kind": "registry"},
    }


def _write_pyproject(tmp_path: Path) -> Path:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "[project.optional-dependencies]\n"
        "uk = [\n"
        '    "policyengine_core>=3.26.0",\n'
        '    "policyengine-uk==2.88.20",\n'
        "]\n"
        "us = [\n"
        '    "policyengine_core==3.26.0",\n'
        '    "policyengine-us==1.700.0",\n'
        "]\n"
        "dev = [\n"
        '    "pytest",\n'
        '    "policyengine_core==3.26.0",\n'
        '    "policyengine-uk==2.88.20",\n'
        '    "policyengine-us==1.700.0",\n'
        "]\n"
    )
    return pyproject_path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
