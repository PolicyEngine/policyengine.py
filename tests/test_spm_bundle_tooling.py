"""Measurement pins are independent of data certification and registry publication."""

import copy
import hashlib
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.version import InvalidVersion, Version

from policyengine import bundle
from policyengine.provenance.bundle_validation import (
    _is_normalized_version,
    validate_bundle_measurements,
)
from policyengine.provenance.spm_configuration import SPMMeasurementConfiguration

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bundle as maintenance  # noqa: E402
from generate_bundle_artifacts import (  # noqa: E402
    load_bundle_manifest,
    normalized_manifest,
)
from spm_bundle import (  # noqa: E402
    configure_spm,
    development_manifest,
    published_calculator_component,
    write_development_manifest,
)


@pytest.fixture
def canonical_bundle():
    # Read the packaged JSON even when an explicitly enabled development plugin
    # replaces runtime get_current_bundle for the household test process.
    return load_bundle_manifest()


@pytest.mark.parametrize(
    "change",
    [
        {"forecast_content_sha256": None},
        {"forecast_content_sha256": "a" * 63},
        {"forecast_content_sha256": "A" * 64},
        {"scenario": None},
        {"scenario": " "},
        {"scenario": "ce_trend "},
        {"scenario": "ce trend"},
        {"geography_kind": "state"},
        {"geography_kind": "metro", "geography_id": None},
        {"geography_kind": "metro", "geography_id": ""},
        {"geography_kind": "national", "geography_id": "31080"},
        {"county_vintage": 2020},
        {"as_of": "2026-02-30"},
        {"as_of": "20260909"},
        {"forecast_path": "/tmp/provider.json"},
        {"provider": "fallback"},
    ],
)
def test_malformed_measurement_defaults_fail_before_bundle_use(
    canonical_bundle, change
):
    canonical_bundle["measurements"]["spm"].update(change)
    with pytest.raises(ValueError):
        SPMMeasurementConfiguration.model_validate(
            canonical_bundle["measurements"]["spm"]
        )
    with pytest.raises(ValueError):
        normalized_manifest(canonical_bundle)
    with pytest.raises(bundle.BundleError):
        bundle._normalise_manifest(canonical_bundle)


@pytest.mark.parametrize("measurements", [None, [], "spm", {"spm": None}])
def test_measurements_require_an_object(canonical_bundle, measurements):
    canonical_bundle["measurements"] = measurements
    with pytest.raises(ValueError):
        validate_bundle_measurements(canonical_bundle)


def test_historical_bundle_without_measurements_still_loads(canonical_bundle):
    canonical_bundle.pop("measurements")
    validate_bundle_measurements(canonical_bundle)
    assert (
        bundle._normalise_manifest(canonical_bundle)["bundle_version"]
        == canonical_bundle["bundle_version"]
    )


def test_staged_config_preserves_certification_and_fails_release_gate(canonical_bundle):
    before = copy.deepcopy(canonical_bundle)
    updated = configure_spm(
        canonical_bundle, canonical_bundle["measurements"]["spm"], None
    )
    assert updated["data_releases"] == before["data_releases"]
    assert updated["packages"] == before["packages"]
    assert updated["packages"]["policyengine-us"]["version"] == "1.764.6"
    validate_bundle_measurements(updated)
    with pytest.raises(ValueError, match="promotion pending"):
        validate_bundle_measurements(updated, require_published_spm=True)


def _calculator_pin():
    # Synthetic registry metadata is a unit fixture, not publication evidence.
    return {
        "name": "spm-calculator",
        "version": "1.0.0",
        "role": "runtime_dependency",
        "country": "us",
        "sha256": "a" * 64,
        "wheel_url": "https://files.pythonhosted.org/unit-test/spm.whl",
    }


def test_published_runtime_dependency_includes_us_and_preserves_uk(canonical_bundle):
    updated = configure_spm(
        canonical_bundle, canonical_bundle["measurements"]["spm"], _calculator_pin()
    )
    assert "spm-calculator==1.0.0" in bundle.bundle_install_requirements(
        updated, countries=["us"]
    )
    assert "spm-calculator==1.0.0" not in bundle.bundle_install_requirements(
        updated, countries=["uk"]
    )
    assert updated["extras"]["uk"] == canonical_bundle["extras"]["uk"]
    validate_bundle_measurements(updated, require_published_spm=True)


@pytest.mark.parametrize(
    "change",
    [
        {"sha256": None},
        {"role": "country_model"},
        {"country": "uk"},
        {"version": ">=1.0"},
        {"version": None},
        {"install_requirement": "spm-calculator>=1"},
        {"installable": False},
        {"markers": "python_version < '0'"},
    ],
)
def test_calculator_requires_scoped_runtime_identity(canonical_bundle, change):
    component = {**_calculator_pin(), **change}
    with pytest.raises(ValueError):
        configure_spm(
            canonical_bundle, canonical_bundle["measurements"]["spm"], component
        )


def _registry_responses(monkeypatch, wheel_bytes, download_bytes):
    import spm_bundle

    expected = hashlib.sha256(wheel_bytes).hexdigest()
    wheel_url = (
        "https://files.pythonhosted.org/unit-test/spm_calculator-1.0.0-py3-none-any.whl"
    )
    payload = {
        "info": {"version": "1.0.0"},
        "urls": [
            {
                "packagetype": "bdist_wheel",
                "filename": "spm_calculator-1.0.0-py3-none-any.whl",
                "url": wheel_url,
                "digests": {"sha256": expected},
            }
        ],
    }
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(
            json=lambda: payload, content=download_bytes, raise_for_status=lambda: None
        )

    monkeypatch.setattr(spm_bundle.requests, "get", get)
    return expected, calls, wheel_url


def test_registry_pin_hashes_downloaded_bytes(monkeypatch):
    expected, calls, url = _registry_responses(
        monkeypatch, b"test-wheel", b"test-wheel"
    )
    component = published_calculator_component("1.0.0")
    assert component["sha256"] == expected
    assert component["role"] == "runtime_dependency"
    assert calls == ["https://pypi.org/pypi/spm-calculator/1.0.0/json", url]


def test_registry_pin_rejects_changed_wheel_bytes(monkeypatch):
    _registry_responses(monkeypatch, b"expected-wheel", b"changed-wheel")
    with pytest.raises(ValueError, match="do not match"):
        published_calculator_component("1.0.0")


def _write_wheel(tmp_path, name, version):
    path = tmp_path / f"{name}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"{name}-{version}.dist-info/METADATA",
            f"Name: {name}\nVersion: {version}\n",
        )
    return path


def test_development_fixture_uses_actual_wheel_pins_without_certification(
    canonical_bundle, tmp_path
):
    country = _write_wheel(tmp_path, "policyengine-us", "1.824.7")
    calculator = _write_wheel(tmp_path, "spm-calculator", "1.0.0")
    before = copy.deepcopy(canonical_bundle)
    development = development_manifest(canonical_bundle, country, calculator)
    assert development["development"]["data_certification"] == "not_certified"
    assert development["development"]["promotion_status"] == "pending"
    assert development["packages"]["policyengine-us"]["version"] == "1.824.7"
    assert (
        development["packages"]["spm-calculator"]["sha256"]
        == hashlib.sha256(calculator.read_bytes()).hexdigest()
    )
    assert "certification" not in development["data_releases"]["us"]
    assert "certified_data_artifact" not in development["data_releases"]["us"]
    assert development["data_releases"]["uk"] == before["data_releases"]["uk"]
    assert canonical_bundle == before
    with pytest.raises(ValueError, match="Development fixtures"):
        validate_bundle_measurements(development, require_published_spm=True)


def test_development_fixture_cannot_replace_packaged_manifest(
    canonical_bundle, tmp_path
):
    from generate_bundle_artifacts import BUNDLE_MANIFEST

    with pytest.raises(ValueError, match="cannot overwrite"):
        write_development_manifest(
            canonical_bundle,
            tmp_path / "missing",
            tmp_path / "missing",
            BUNDLE_MANIFEST,
        )


def test_cli_rejects_invalid_configuration_without_writing(
    monkeypatch, canonical_bundle
):
    import generate_bundle_artifacts

    monkeypatch.setattr(
        generate_bundle_artifacts, "load_bundle_manifest", lambda: canonical_bundle
    )
    monkeypatch.setattr(
        generate_bundle_artifacts,
        "write_bundle_manifest",
        lambda _: pytest.fail("Invalid configuration wrote a manifest"),
    )
    with pytest.raises(SystemExit) as error:
        maintenance.main(
            [
                "set-spm",
                "--forecast-content-sha256",
                "invalid",
                "--scenario",
                "ce_trend",
            ]
        )
    assert error.value.code == 2


@pytest.mark.parametrize(
    "version",
    [
        "1",
        "1.0.0",
        "1.0rc1",
        "1.0.post0.dev1",
        "2!1.0+linux.x86.1",
        "1.0+01",
        "1.0+Linux",
        "01.0",
        "1.01",
        "0!1.0",
        "v1.0",
        "1.0RC1",
        "1.0-1",
        "1.0.post",
        "1.0.dev",
        "1.*",
        ">=1.0",
        "",
        None,
    ],
)
def test_dependency_free_exact_version_validation_matches_packaging(version):
    try:
        expected = isinstance(version, str) and str(Version(version)) == version
    except InvalidVersion:
        expected = False
    assert _is_normalized_version(version) is expected
