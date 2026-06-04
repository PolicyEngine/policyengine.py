from __future__ import annotations

import hashlib
import importlib.util
import json
import tarfile
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "import_policyengine_bundle.py"
)
SPEC = importlib.util.spec_from_file_location("import_policyengine_bundle", SCRIPT_PATH)
assert SPEC is not None
import_policyengine_bundle = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(import_policyengine_bundle)


def test_import_policyengine_bundle_verifies_and_vendors_release(
    tmp_path: Path,
) -> None:
    dist_dir = _write_release_assets(tmp_path, version="4.14.0")
    bundle_dir = tmp_path / "vendored-bundle"
    release_manifest_dir = tmp_path / "release_manifests"
    pyproject_path = _write_pyproject(tmp_path)
    changelog_dir = tmp_path / "changelog.d"

    result = import_policyengine_bundle.import_policyengine_bundle(
        version="4.14.0",
        dist_dir=dist_dir,
        base_url="unused",
        bundle_dir=bundle_dir,
        release_manifest_dir=release_manifest_dir,
        pyproject_path=pyproject_path,
        changelog_dir=changelog_dir,
    )

    assert (bundle_dir / "bundle.json").exists()
    assert result.bundle_dir == bundle_dir
    assert {path.name for path in result.release_manifest_paths} == {
        "uk.json",
        "us.json",
    }

    us_manifest = json.loads((release_manifest_dir / "us.json").read_text())
    assert us_manifest["bundle_id"] == "us-4.14.0"
    assert us_manifest["policyengine_version"] == "4.14.0"
    assert us_manifest["model_package"]["version"] == "1.715.2"
    assert (
        us_manifest["certified_data_artifact"]["uri"]
        == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@data-sha"
    )
    assert us_manifest["certification"]["certified_for_model_version"] == "1.715.2"

    pyproject = pyproject_path.read_text()
    assert '"policyengine_core==3.26.1"' in pyproject
    assert '"policyengine-us==1.715.2"' in pyproject
    assert '"policyengine-uk==3.0.0"' in pyproject
    assert (changelog_dir / "policyengine-bundle-4.14.0.changed.md").exists()


def test_import_policyengine_bundle_rejects_checksum_mismatch(
    tmp_path: Path,
) -> None:
    dist_dir = _write_release_assets(tmp_path, version="4.14.0")
    (dist_dir / "policyengine-bundle-4.14.0.tar.gz.sha256").write_text(
        f"{'0' * 64}  policyengine-bundle-4.14.0.tar.gz\n"
    )

    with pytest.raises(
        import_policyengine_bundle.BundleImportError,
        match="archive_sha256 does not match checksum file",
    ):
        import_policyengine_bundle.import_policyengine_bundle(
            version="4.14.0",
            dist_dir=dist_dir,
            base_url="unused",
            bundle_dir=tmp_path / "vendored-bundle",
            release_manifest_dir=tmp_path / "release_manifests",
            pyproject_path=_write_pyproject(tmp_path),
            changelog_dir=None,
        )


def _write_release_assets(tmp_path: Path, *, version: str) -> Path:
    bundle_root = tmp_path / f"policyengine-bundle-{version}"
    _write_json(bundle_root / "countries" / "us.json", _country_bundle("us", version))
    _write_json(bundle_root / "countries" / "uk.json", _country_bundle("uk", version))
    _write_json(bundle_root / "validation-report.json", _validation_report(version))
    bundle = _bundle_manifest(version)
    _write_json(bundle_root / "bundle.json", bundle)
    bundle["bundle_digest"] = (
        f"sha256:{import_policyengine_bundle._bundle_directory_digest(bundle_root)}"
    )
    _write_json(bundle_root / "bundle.json", bundle)

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    archive_path = dist_dir / f"policyengine-bundle-{version}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(bundle_root, arcname=bundle_root.name)
    archive_sha256 = _sha256_file(archive_path)
    (dist_dir / f"{archive_path.name}.sha256").write_text(
        f"{archive_sha256}  {archive_path.name}\n"
    )
    _write_json(
        dist_dir / f"policyengine-bundle-{version}.json",
        {
            "bundle_version": version,
            "bundle_digest": bundle["bundle_digest"],
            "archive": archive_path.name,
            "archive_sha256": archive_sha256,
        },
    )
    return dist_dir


def _bundle_manifest(version: str) -> dict:
    return {
        "schema_version": 1,
        "bundle_version": version,
        "created_at": "2026-06-03T00:00:00Z",
        "policyengine": {
            "name": "policyengine",
            "version": version,
            "resolution_status": "pinned",
        },
        "packages": {
            "policyengine": {
                "name": "policyengine",
                "version": version,
                "resolution_status": "pinned",
            },
            "policyengine-core": {
                "name": "policyengine-core",
                "version": "3.26.1",
                "resolution_status": "pinned",
            },
            "policyengine-us": {
                "name": "policyengine-us",
                "version": "1.715.2",
                "resolution_status": "pinned",
            },
            "policyengine-uk": {
                "name": "policyengine-uk",
                "version": "3.0.0",
                "resolution_status": "pinned",
            },
        },
        "profiles": {
            "us": {"packages": ["policyengine-us"], "countries": ["us"]},
            "uk": {"packages": ["policyengine-uk"], "countries": ["uk"]},
            "all": {
                "packages": ["policyengine-us", "policyengine-uk"],
                "countries": ["us", "uk"],
            },
        },
        "countries": {
            "us": "countries/us.json",
            "uk": "countries/uk.json",
        },
        "validation_report": "validation-report.json",
    }


def _country_bundle(country_id: str, version: str) -> dict:
    model_package = "policyengine-us" if country_id == "us" else "policyengine-uk"
    model_version = "1.715.2" if country_id == "us" else "3.0.0"
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
    return {
        "schema_version": 1,
        "bundle_version": version,
        "country_id": country_id,
        "model_package": {
            "name": model_package,
            "version": model_version,
            "resolution_status": "pinned",
            "sha256": "a" * 64,
            "wheel_url": f"https://example.test/{model_package}.whl",
        },
        "core_package": {
            "name": "policyengine-core",
            "version": "3.26.1",
            "resolution_status": "pinned",
        },
        "data_package": {
            "name": data_package,
            "version": "1.0.0",
            "repo_id": repo_id,
            "repo_type": "model",
            "release_manifest_path": "release_manifest.json",
            "release_manifest_revision": "data-sha",
        },
        "artifact_release": {
            "repo_id": repo_id,
            "version": "data-sha",
            "repo_type": "model",
            "release_manifest_uri": f"hf://model/{repo_id}@data-sha/release_manifest.json",
        },
        "default_dataset": dataset,
        "datasets": {
            dataset: {
                "kind": "microdata",
                "path": path,
                "repo_id": repo_id,
                "revision": "data-sha",
                "sha256": "b" * 64,
                "status": "certified",
            }
        },
        "region_datasets": {"national": {"path_template": path}},
        "certification": {
            "compatibility_basis": "manual_runtime_certification",
            "built_with_model_package": {
                "name": model_package,
                "version": model_version,
                "resolution_status": "pinned",
            },
            "built_with_core_package": {
                "name": "policyengine-core",
                "version": "3.26.1",
                "resolution_status": "pinned",
            },
            "certified_for_model_package": {
                "name": model_package,
                "version": model_version,
                "resolution_status": "pinned",
            },
            "certified_for_core_package": {
                "name": "policyengine-core",
                "version": "3.26.1",
                "resolution_status": "pinned",
            },
            "certified_by": "test",
            "data_build_id": f"{data_package}-1.0.0",
            "data_build_fingerprint": "sha256:fingerprint",
        },
    }


def _validation_report(version: str) -> dict:
    return {
        "schema_version": 1,
        "bundle_version": version,
        "generated_at": "2026-06-03T00:00:00Z",
        "status": "passed",
        "checks": [
            {
                "name": "runtime",
                "status": "passed",
                "details": {"validated_on_platform": "test"},
            }
        ],
        "metadata": {"validation_scope": "full"},
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


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
