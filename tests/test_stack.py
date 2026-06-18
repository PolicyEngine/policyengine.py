import json

import pytest

from policyengine import stack
from policyengine.cli import main as cli_main


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
        "policyengine-core==3.26.1",
        "policyengine-us==1.687.0",
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


def test_unknown_extra_is_named():
    with pytest.raises(stack.StackError, match="No stack extra"):
        stack.get_extra("ghost")
