import importlib.util
import json
import sys
from pathlib import Path

import pytest

from policyengine import stack
from policyengine.cli import main as cli_main


def _load_export_script(monkeypatch):
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "export_stack_release_assets",
        scripts_dir / "export_stack_release_assets.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stack_manifest_exposes_full_and_slice_extras():
    manifest = stack.get_current_stack()

    assert manifest["stack_version"] == manifest["policyengine_version"]
    assert manifest["extras"]["full"] == [
        "policyengine-core",
        "policyengine-us",
        "policyengine-uk",
        "policyengine-us-data",
    ]
    assert manifest["packages"]["policyengine-uk-data"]["installable"] is False
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


def test_stack_install_requirements_are_exact_pins():
    manifest = stack.get_current_stack()

    assert stack.stack_install_requirements("us") == [
        f"policyengine=={manifest['policyengine_version']}",
        manifest["packages"]["policyengine-core"]["install_requirement"],
        manifest["packages"]["policyengine-us"]["install_requirement"],
    ]


def test_verify_installed_stack_passes_for_matching_extra(monkeypatch):
    manifest = stack.get_current_stack()
    versions = {
        component["name"]: component["version"]
        for component in manifest["packages"].values()
    }

    monkeypatch.setattr(stack.metadata, "version", lambda name: versions[name])
    monkeypatch.setattr(stack, "find_spec", lambda name: object())

    report = stack.verify_installed_stack(extra="models")

    assert report["passed"] is True
    assert {check["status"] for check in report["checks"]} == {"ok"}


def test_verify_installed_stack_reports_version_mismatch(monkeypatch):
    manifest = stack.get_current_stack()
    versions = {
        component["name"]: component["version"]
        for component in manifest["packages"].values()
    }
    versions["policyengine-us"] = "0.0.0"

    monkeypatch.setattr(stack.metadata, "version", lambda name: versions[name])

    report = stack.verify_installed_stack(extra="us", check_imports=False)

    assert report["passed"] is False
    mismatch = next(
        check for check in report["checks"] if check.get("package") == "policyengine-us"
    )
    assert mismatch["status"] == "mismatch"


def test_stack_show_cli_outputs_manifest_json(capsys):
    exit_code = cli_main(["stack", "show", "--extra", "us"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["packages"]) == {
        "policyengine",
        "policyengine-core",
        "policyengine-us",
    }


def test_stack_verify_cli_outputs_json(monkeypatch, capsys):
    manifest = stack.get_current_stack()
    versions = {
        component["name"]: component["version"]
        for component in manifest["packages"].values()
    }
    monkeypatch.setattr(stack.metadata, "version", lambda name: versions[name])

    exit_code = cli_main(
        ["stack", "verify", "--extra", "models", "--no-imports", "--json"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True


def test_export_release_assets_writes_bundle_assets_and_stack_aliases(
    monkeypatch,
    tmp_path,
):
    export_script = _load_export_script(monkeypatch)
    manifest = stack.get_current_stack()
    version = manifest["stack_version"]
    monkeypatch.setattr(
        sys,
        "argv",
        ["export_stack_release_assets", "--dist-dir", str(tmp_path)],
    )

    assert export_script.main() == 0

    bundle_manifest = tmp_path / f"policyengine-bundle-{version}.json"
    stack_manifest = tmp_path / f"policyengine-stack-{version}.json"
    assert bundle_manifest.exists()
    assert stack_manifest.exists()
    assert json.loads(bundle_manifest.read_text()) == json.loads(
        stack_manifest.read_text()
    )
    assert (
        f"policyengine=={manifest['policyengine_version']}"
        in (tmp_path / f"policyengine-bundle-{version}.constraints.txt").read_text()
    )
    assert (
        "PolicyEngine bundle"
        in (tmp_path / f"policyengine-bundle-{version}.citation.txt").read_text()
    )


def test_unknown_extra_is_named():
    with pytest.raises(stack.StackError, match="No stack extra"):
        stack.get_extra("ghost")
