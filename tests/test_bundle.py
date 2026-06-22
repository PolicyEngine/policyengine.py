import json
import sys
from pathlib import Path

import pytest

from policyengine import bundle
from policyengine.cli import main as cli_main


def test_bundle_manifest_exposes_data_releases():
    manifest = bundle.get_current_bundle()

    assert manifest["bundle_version"] == manifest["policyengine_version"]
    assert manifest["data_releases"]["us"]["data_producer"] == "populace"
    assert manifest["data_releases"]["us"]["version"].startswith("populace-us-2024-")
    assert manifest["data_releases"]["uk"]["data_producer"] == "populace"
    assert manifest["data_releases"]["uk"]["version"].startswith("populace-uk-2023-")
    assert manifest["data_releases"]["uk"]["default_dataset_uri"].startswith(
        "hf://policyengine/populace-uk-private/"
    )


def test_bundle_install_requirements_are_country_scoped():
    manifest = bundle.get_current_bundle()

    assert bundle.bundle_install_requirements(manifest, countries=["uk"]) == [
        f"policyengine=={manifest['policyengine_version']}",
        manifest["packages"]["policyengine-core"]["install_requirement"],
        manifest["packages"]["policyengine-uk"]["install_requirement"],
    ]
    assert (
        "policyengine-us-data==1.78.2; python_version >= '3.12' and python_version < '3.15'"
        in bundle.bundle_install_requirements(
            manifest,
            countries=["us"],
        )
    )


def test_dataset_plans_use_certified_release_metadata(tmp_path):
    plans = bundle.dataset_plans(
        bundle.get_current_bundle(),
        countries=["uk"],
        data_dir=tmp_path,
    )

    assert len(plans) == 1
    assert plans[0].country == "uk"
    assert plans[0].data_version.startswith("populace-uk-2023-")
    assert plans[0].data_producer == "populace"
    assert plans[0].repo_type == "dataset"
    assert plans[0].destination == tmp_path / "populace_uk_2023.h5"


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
    assert calls[0][0] == Path(sys.executable)
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


class FakeResponse:
    status_code = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield b"new-data"


class FakeSession:
    def get(self, *args, **kwargs):
        return FakeResponse()


def test_install_datasets_downloads_then_backs_up_existing_file(tmp_path):
    existing = tmp_path / "populace_us_2024.h5"
    existing.write_bytes(b"old-data")

    installed = bundle.install_datasets(
        bundle.get_current_bundle(),
        countries=["us"],
        data_dir=tmp_path,
        yes=True,
        session=FakeSession(),
    )

    assert installed[0]["country"] == "us"
    assert existing.read_bytes() == b"new-data"
    backups = list((tmp_path / bundle.BACKUP_DIR_NAME).glob("*/populace_us_2024.h5"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"old-data"


def test_status_matches_receipt_and_packages(monkeypatch, tmp_path):
    manifest = bundle.get_current_bundle()
    datasets = [
        {
            "country": "uk",
            "dataset": "populace_uk_2023",
            "version": manifest["data_releases"]["uk"]["version"],
            "uri": manifest["data_releases"]["uk"]["default_dataset_uri"],
            "path": str(tmp_path / "populace_uk_2023.h5"),
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

    report = bundle.inspect_bundle_status(countries=["uk"], data_dir=tmp_path)

    assert report["matched"] is True
    assert {check["status"] for check in report["packages"]} == {"ok"}
    assert {check["status"] for check in report["datasets"]} == {"ok"}


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
