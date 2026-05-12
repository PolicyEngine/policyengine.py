from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / ".github" / "vendor_release_bundle.py"

spec = importlib.util.spec_from_file_location("vendor_release_bundle", MODULE_PATH)
vendor_release_bundle = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(vendor_release_bundle)


def test_vendor_bundle_derives_py_release_manifest_and_pins(tmp_path: Path) -> None:
    bundle_root = tmp_path / "policyengine-bundle-4.4.3"
    (bundle_root / "countries").mkdir(parents=True)
    (bundle_root / "install" / "us" / "py314").mkdir(parents=True)
    _write_json(
        bundle_root / "bundle.json",
        {
            "bundle_version": "4.4.3",
            "policyengine": {
                "name": "policyengine",
                "version": "4.4.3",
                "resolution_status": "pinned",
                "role": "bundle_carrier",
            },
            "packages": {
                "policyengine": {
                    "name": "policyengine",
                    "version": "4.4.3",
                    "resolution_status": "pinned",
                    "role": "bundle_carrier",
                },
                "policyengine-core": {
                    "name": "policyengine-core",
                    "version": "3.26.1",
                    "resolution_status": "pinned",
                },
                "policyengine-us": {
                    "name": "policyengine-us",
                    "version": "1.687.0",
                    "resolution_status": "pinned",
                },
            },
            "profiles": {
                "us": {
                    "packages": [
                        "policyengine",
                        "policyengine-core",
                        "policyengine-us",
                    ],
                    "countries": ["us"],
                    "install_targets": {
                        "py314": {
                            "python_version": "3.14",
                            "constraints": "install/us/py314/constraints.txt",
                            "lockfile": "install/us/py314/pylock.toml",
                            "resolver": "uv",
                        }
                    },
                }
            },
            "countries": {"us": "countries/us.json"},
            "validation_report": "validation-report.json",
        },
    )
    _write_json(
        bundle_root / "countries" / "us.json",
        {
            "schema_version": 1,
            "bundle_version": "4.4.3",
            "country_id": "us",
            "model_package": {
                "name": "policyengine-us",
                "version": "1.687.0",
                "sha256": "a" * 64,
                "wheel_url": "https://example.test/policyengine-us.whl",
            },
            "core_package": {"name": "policyengine-core", "version": "3.26.1"},
            "data_package": {
                "name": "policyengine-us-data",
                "version": "1.78.2",
                "repo_id": "policyengine/policyengine-us-data",
                "repo_type": "model",
                "release_manifest_path": "releases/1.78.2/release_manifest.json",
            },
            "artifact_release": {
                "repo_id": "policyengine/policyengine-us-data",
                "repo_type": "model",
                "version": "9cb665d",
            },
            "default_dataset": "enhanced_cps_2024",
            "datasets": {
                "enhanced_cps_2024": {
                    "kind": "microdata",
                    "path": "enhanced_cps_2024.h5",
                    "repo_id": "policyengine/policyengine-us-data",
                    "revision": "1.78.2",
                    "sha256": "b" * 64,
                },
                "weights": {
                    "kind": "weights",
                    "path": "weights.h5",
                    "repo_id": "policyengine/policyengine-us-data",
                    "revision": "1.78.2",
                },
            },
            "certification": {
                "compatibility_basis": "release_manifest_exact_compatibility",
                "data_build_id": "policyengine-us-data-1.78.2",
                "built_with_model_package": {
                    "name": "policyengine-us",
                    "version": "1.687.0",
                },
                "certified_for_model_package": {
                    "name": "policyengine-us",
                    "version": "1.687.0",
                },
            },
        },
    )
    (bundle_root / "install" / "us" / "py314" / "constraints.txt").write_text(
        "policyengine-us==1.687.0\n"
    )
    (bundle_root / "install" / "us" / "py314" / "pylock.toml").write_text("[lock]\n")
    _write_json(bundle_root / "validation-report.json", {"status": "passed"})

    data_root = tmp_path / "data"
    _write_json(
        data_root / "release_manifests" / "us.json",
        {"region_datasets": {"national": {"path_template": "enhanced_cps_2024.h5"}}},
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project.optional-dependencies]\n"
        "us = [\n"
        '    "policyengine-core==0.0.1",\n'
        '    "policyengine-us==0.0.1",\n'
        "]\n"
        "dev = [\n"
        '    "policyengine-core==0.0.1",\n'
        '    "policyengine-us==0.0.1",\n'
        "]\n"
    )

    vendor_release_bundle._vendor_bundle(bundle_root, data_root, pyproject)

    release_manifest = json.loads(
        (data_root / "release_manifests" / "us.json").read_text()
    )
    assert release_manifest["policyengine_version"] == "4.4.3"
    assert release_manifest["bundle_id"] == "us-4.4.3"
    assert release_manifest["certified_data_artifact"]["uri"] == (
        "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.78.2"
    )
    assert release_manifest["datasets"] == {
        "enhanced_cps_2024": {"path": "enhanced_cps_2024.h5"}
    }
    assert release_manifest["region_datasets"] == {
        "national": {"path_template": "enhanced_cps_2024.h5"}
    }
    assert "policyengine-core==3.26.1" in pyproject.read_text()
    assert "policyengine-us==1.687.0" in pyproject.read_text()
    assert (data_root / "install" / "us" / "py314" / "constraints.txt").is_file()


def test_typed_hf_uri_is_converted_to_policyengine_hf_uri() -> None:
    assert (
        vendor_release_bundle._bundle_hf_uri_to_policyengine_uri(
            "hf://model/policyengine/policyengine-uk-data-private@1.55.5/data.h5"
        )
        == "hf://policyengine/policyengine-uk-data-private/data.h5@1.55.5"
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
