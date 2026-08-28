import hashlib
import json
import sys
from pathlib import Path

import pytest

from policyengine import bundle
from policyengine.cli import main as cli_main
from policyengine.provenance.dataset_materialization import MaterializedDataset


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _manifest_with_dataset_sha(country: str, sha256: str) -> dict:
    manifest = json.loads(json.dumps(bundle.get_current_bundle()))
    release = manifest["data_releases"][country]
    dataset = release["default_dataset"]
    release["datasets"][dataset]["sha256"] = sha256
    release["certified_data_artifact"]["sha256"] = sha256
    return manifest


def _write_manifest(tmp_path, manifest: dict) -> str:
    path = tmp_path / "bundle-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return str(path)


def test_bundle_manifest_exposes_data_releases():
    manifest = bundle.get_current_bundle()

    assert manifest["bundle_version"] == manifest["policyengine_version"]
    assert manifest["data_releases"]["us"]["data_producer"] == "populace"
    assert manifest["data_releases"]["us"]["version"].startswith("populace-us-2024-")
    # UK certified default reverted to the policyengine-uk-data enhanced FRS per
    # the UC caseload postmortem (policyengine-uk-data discussion #464); the
    # "populace" producer label names the strict verification contract, not the
    # producing repo.
    assert manifest["data_releases"]["uk"]["data_producer"] == "populace"
    assert manifest["data_releases"]["uk"]["version"].startswith(
        "policyengine-uk-data-"
    )
    assert manifest["data_releases"]["uk"]["default_dataset_uri"].startswith(
        "hf://policyengine/policyengine-uk-data-private/enhanced_frs_"
    )


def test_bundle_install_requirements_are_country_scoped():
    manifest = bundle.get_current_bundle()

    assert bundle.bundle_install_requirements(manifest, countries=["uk"]) == [
        f"policyengine=={manifest['policyengine_version']}",
        manifest["packages"]["policyengine-core"]["install_requirement"],
        manifest["packages"]["policyengine-uk"]["install_requirement"],
    ]
    us_requirements = bundle.bundle_install_requirements(
        manifest,
        countries=["us"],
    )
    assert us_requirements == [
        f"policyengine=={manifest['policyengine_version']}",
        manifest["packages"]["policyengine-core"]["install_requirement"],
        manifest["packages"]["policyengine-us"]["install_requirement"],
    ]
    assert not any("policyengine-us-data" in req for req in us_requirements)


def test_selected_dataset_plan_uses_certified_release_metadata(tmp_path):
    entries = bundle._selected_dataset_plans(
        bundle.get_current_bundle(), ["uk"], data_dir=tmp_path
    )

    plan, release = entries[0]
    assert plan.country_id == "uk"
    assert plan.data_package_name == "policyengine-uk-data"
    assert plan.repo_type == "model"
    assert plan.destination == tmp_path / "enhanced_frs_2024_25.h5"
    assert plan.expected_sha256 == release["datasets"][plan.dataset]["sha256"]


def test_install_bundle_package_only_uses_explicit_python(monkeypatch, tmp_path):
    calls = []

    def fake_install(target_python, requirements, *, dry_run=False):
        calls.append((target_python, requirements, dry_run))

    monkeypatch.setattr(bundle, "install_package_scaffold", fake_install)

    result = bundle.install_bundle(
        python=sys.executable,
        countries=["uk"],
        data_dir=tmp_path,
        no_datasets=True,
    )

    assert result["countries"] == ["uk"]
    assert calls[0][0] == Path(sys.executable).resolve()
    receipt = bundle.read_receipt(tmp_path)
    assert receipt is not None
    assert receipt["target_python"] == str(Path(sys.executable).resolve())
    assert calls[0][1] == [
        f"policyengine=={result['bundle_version']}",
        bundle.get_current_bundle()["packages"]["policyengine-core"][
            "install_requirement"
        ],
        bundle.get_current_bundle()["packages"]["policyengine-uk"][
            "install_requirement"
        ],
    ]


def test_resolve_target_python_accepts_path_executable(monkeypatch, tmp_path):
    python_path = tmp_path / "python"
    python_path.write_text("")
    monkeypatch.setattr(bundle.shutil, "which", lambda name: str(python_path))

    assert bundle.resolve_target_python(python="python") == python_path


def test_resolve_target_python_defaults_to_local_venv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    assert bundle.resolve_target_python(create_venv=False) == (
        tmp_path / ".venv" / "bin" / "python"
    )
    assert not (tmp_path / ".venv").exists()


def test_resolve_target_python_uses_local_venv_from_runner_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "uvx-runner"))
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    assert bundle.resolve_target_python(create_venv=False) == (
        tmp_path / ".venv" / "bin" / "python"
    )
    assert not (tmp_path / ".venv").exists()


def test_install_bundle_materializes_defaults_and_records_receipt(
    monkeypatch, tmp_path
):
    calls = []

    monkeypatch.setattr(
        bundle, "install_package_scaffold", lambda *args, **kwargs: None
    )

    def fake_materialize(plan):
        calls.append(plan)
        plan.destination.parent.mkdir(parents=True, exist_ok=True)
        plan.destination.write_bytes(b"materialized")
        return MaterializedDataset(
            data_package_name=plan.data_package_name,
            repo_type=plan.repo_type,
            revision=plan.revision,
            source_uri=plan.source_uri,
            expected_sha256=plan.expected_sha256,
            actual_sha256=plan.expected_sha256,
            path=plan.destination,
            cache_hit=False,
        )

    monkeypatch.setattr(bundle, "_materialize_resolved_dataset", fake_materialize)

    result = bundle.install_bundle(
        python=sys.executable,
        countries=["uk"],
        data_dir=tmp_path,
        yes=True,
    )

    assert [plan.country_id for plan in calls] == ["uk"]
    assert result["datasets"][0]["data_package_name"] == "policyengine-uk-data"
    assert result["datasets"][0]["installed_sha256"] == calls[0].expected_sha256
    receipt = bundle.read_receipt(tmp_path)
    assert receipt is not None
    assert receipt["datasets"] == result["datasets"]


def test_status_matches_receipt_and_packages(monkeypatch, tmp_path):
    manifest = _manifest_with_dataset_sha("uk", _sha256(b"data"))
    datasets = [
        {
            "country": "uk",
            "dataset": "populace_uk_2023",
            "version": manifest["data_releases"]["uk"]["version"],
            "uri": manifest["data_releases"]["uk"]["default_dataset_uri"],
            "path": str(tmp_path / "populace_uk_2023.h5"),
            "expected_sha256": _sha256(b"data"),
            "installed_sha256": _sha256(b"data"),
        }
    ]
    (tmp_path / "populace_uk_2023.h5").write_bytes(b"data")
    bundle.write_receipt(
        manifest,
        data_dir=tmp_path,
        countries=["uk"],
        datasets=datasets,
    )
    versions = {
        component["name"]: component["version"]
        for component in manifest["packages"].values()
    }
    monkeypatch.setattr(bundle.metadata, "version", lambda name: versions[name])

    report = bundle.inspect_bundle_status(
        manifest_ref=_write_manifest(tmp_path, manifest),
        countries=["uk"],
        data_dir=tmp_path,
    )

    assert report["matched"] is True
    assert {check["status"] for check in report["packages"]} == {"ok"}
    assert {check["status"] for check in report["datasets"]} == {"ok"}
    assert report["datasets"][0]["installed_sha256"] == _sha256(b"data")


def test_status_uses_receipt_target_python(monkeypatch, tmp_path):
    manifest = _manifest_with_dataset_sha("uk", _sha256(b"data"))
    target_python = tmp_path / ".venv" / "bin" / "python"
    target_python.parent.mkdir(parents=True)
    target_python.write_text("")
    datasets = [
        {
            "country": "uk",
            "dataset": "populace_uk_2023",
            "version": manifest["data_releases"]["uk"]["version"],
            "uri": manifest["data_releases"]["uk"]["default_dataset_uri"],
            "path": str(tmp_path / "populace_uk_2023.h5"),
            "expected_sha256": _sha256(b"data"),
            "installed_sha256": _sha256(b"data"),
        }
    ]
    (tmp_path / "populace_uk_2023.h5").write_bytes(b"data")
    bundle.write_receipt(
        manifest,
        data_dir=tmp_path,
        countries=["uk"],
        datasets=datasets,
        target_python=target_python,
    )
    versions = {
        component["name"]: component["version"]
        for component in manifest["packages"].values()
    }
    calls = []

    def fake_versions(python_path, components):
        calls.append(python_path)
        return versions, None

    monkeypatch.setattr(bundle, "_package_versions_from_python", fake_versions)

    report = bundle.inspect_bundle_status(
        manifest_ref=_write_manifest(tmp_path, manifest),
        countries=["uk"],
        data_dir=tmp_path,
    )

    assert report["matched"] is True
    assert calls == [target_python.resolve()]
    assert report["target_python"] == str(target_python.resolve())


def test_status_reports_dataset_hash_mismatch(monkeypatch, tmp_path):
    manifest = _manifest_with_dataset_sha("uk", _sha256(b"certified-data"))
    dataset_path = tmp_path / "populace_uk_2023.h5"
    dataset_path.write_bytes(b"tampered-data")
    bundle.write_receipt(
        manifest,
        data_dir=tmp_path,
        countries=["uk"],
        datasets=[
            {
                "country": "uk",
                "dataset": "populace_uk_2023",
                "version": manifest["data_releases"]["uk"]["version"],
                "uri": manifest["data_releases"]["uk"]["default_dataset_uri"],
                "path": str(dataset_path),
                "expected_sha256": _sha256(b"certified-data"),
                "installed_sha256": _sha256(b"certified-data"),
            }
        ],
    )
    versions = {
        component["name"]: component["version"]
        for component in manifest["packages"].values()
    }
    monkeypatch.setattr(bundle.metadata, "version", lambda name: versions[name])

    report = bundle.inspect_bundle_status(
        manifest_ref=_write_manifest(tmp_path, manifest),
        countries=["uk"],
        data_dir=tmp_path,
    )

    assert report["matched"] is False
    assert report["datasets"][0]["status"] == "sha256_mismatch"
    assert report["datasets"][0]["expected_sha256"] == _sha256(b"certified-data")
    assert report["datasets"][0]["installed_sha256"] == _sha256(b"tampered-data")


def test_status_reports_missing_receipt_target_python(tmp_path):
    manifest = bundle.get_current_bundle()
    missing_python = tmp_path / ".venv" / "bin" / "python"
    bundle.write_receipt(
        manifest,
        data_dir=tmp_path,
        countries=["uk"],
        datasets=[],
        target_python=missing_python,
    )

    report = bundle.inspect_bundle_status(
        countries=["uk"],
        data_dir=tmp_path,
        packages_only=True,
    )

    assert report["matched"] is False
    assert {check["status"] for check in report["packages"]} == {
        "target_python_missing"
    }


def test_status_treats_corrupt_receipt_as_missing(monkeypatch, tmp_path):
    manifest = bundle.get_current_bundle()
    (tmp_path / bundle.RECEIPT_FILENAME).write_text("{not-json", encoding="utf-8")
    versions = {
        component["name"]: component["version"]
        for component in manifest["packages"].values()
    }
    monkeypatch.setattr(bundle.metadata, "version", lambda name: versions[name])

    report = bundle.inspect_bundle_status(countries=["uk"], data_dir=tmp_path)

    assert report["matched"] is False
    assert report["receipt"] is None
    assert report["datasets"][0]["status"] == "missing_receipt"


def test_bundle_manifest_cli_outputs_json(capsys):
    exit_code = cli_main(["bundle", "manifest"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["bundle_version"] == payload["policyengine_version"]


def test_bundle_install_dry_run_cli_uses_standard_flags(capsys):
    exit_code = cli_main(
        [
            "bundle",
            "install",
            "--python",
            sys.executable,
            "--country",
            "uk",
            "--no-datasets",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "pip install" in output
    assert (
        bundle.get_current_bundle()["packages"]["policyengine-uk"][
            "install_requirement"
        ]
        in output
    )


def test_bundle_verify_cli_handles_unknown_bundle(capsys):
    exit_code = cli_main(["bundle", "verify", "0.0.0"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Bundle '0.0.0'" in captured.err


def test_unknown_bundle_version_is_named():
    with pytest.raises(bundle.BundleError, match="Bundle '0.0.0'"):
        bundle.load_bundle_manifest("0.0.0")
