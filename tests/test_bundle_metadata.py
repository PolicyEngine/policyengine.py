import importlib.util
import json
import sys
from pathlib import Path

from policyengine import bundle
from policyengine.cli import main as cli_main


def _load_export_script(monkeypatch):
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "export_bundle_release_assets",
        scripts_dir / "export_bundle_release_assets.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_bundle_manifest_exposes_full_and_slice_extras():
    manifest = bundle.get_current_bundle()

    assert manifest["bundle_version"] == manifest["policyengine_version"]
    assert "stack_version" not in manifest
    assert manifest["extras"]["full"] == [
        "policyengine-core",
        "policyengine-us",
        "policyengine-uk",
        "policyengine-us-data",
    ]
    assert "policyengine-uk-data" not in manifest["packages"]
    assert manifest["extras"]["models"] == [
        "policyengine-core",
        "policyengine-us",
        "policyengine-uk",
    ]
    assert manifest["extras"]["us-full"] == [
        "policyengine-core",
        "policyengine-us",
        "policyengine-us-data",
    ]


def test_bundle_manifest_carries_populace_uk_data_release():
    release = bundle.get_current_bundle()["data_releases"]["uk"]

    assert release["data_producer"] == "populace"
    assert release["data_package"]["name"] == "populace-data"
    assert release["data_package"]["repo_type"] == "dataset"
    assert release["default_dataset"] == "populace_uk_2023"
    assert release["version"].startswith("populace-uk-2023-")
    assert release["default_dataset_uri"].startswith(
        "hf://policyengine/populace-uk-private/"
    )


def test_bundle_manifest_cli_outputs_json(capsys):
    exit_code = cli_main(["bundle", "manifest"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["bundle_version"] == payload["policyengine_version"]
    assert set(payload["packages"]) >= {
        "policyengine",
        "policyengine-core",
        "policyengine-us",
        "policyengine-uk",
    }


def test_bundle_verify_packages_only_cli_outputs_json(monkeypatch, capsys):
    manifest = bundle.get_current_bundle()
    versions = {
        component["name"]: component["version"]
        for component in manifest["packages"].values()
    }
    monkeypatch.setattr(bundle.metadata, "version", lambda name: versions[name])

    exit_code = cli_main(
        [
            "bundle",
            "verify",
            "--country",
            "us",
            "--country",
            "uk",
            "--packages-only",
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["matched"] is True
    assert payload["datasets"] == []


def test_export_release_assets_writes_bundle_assets(monkeypatch, tmp_path):
    export_script = _load_export_script(monkeypatch)
    manifest = bundle.get_current_bundle()
    version = manifest["bundle_version"]
    monkeypatch.setattr(
        sys,
        "argv",
        ["export_bundle_release_assets", "--dist-dir", str(tmp_path)],
    )

    assert export_script.main() == 0

    bundle_manifest = tmp_path / f"policyengine-bundle-{version}.json"
    assert bundle_manifest.exists()
    assert not (tmp_path / f"policyengine-stack-{version}.json").exists()
    assert json.loads(bundle_manifest.read_text()) == manifest
    assert (
        f"policyengine=={manifest['policyengine_version']}"
        in (tmp_path / f"policyengine-bundle-{version}.constraints.txt").read_text()
    )
    assert (
        "PolicyEngine bundle"
        in (tmp_path / f"policyengine-bundle-{version}.citation.txt").read_text()
    )
