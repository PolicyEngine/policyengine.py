"""Supported dataset years recorded in the bundle manifest (#734).

Certification records, on each country's certified dataset record
(``data_releases.<country>.certified_data_artifact.supported_years``), the
years :func:`policyengine.provenance.dataset_years.supported_years` returns for
that dataset's bytes under the country model, core and (US) spm-calculator the
bundle pins. It computes them in a separate ``uv run --isolated`` environment
holding exactly those versions, so a certification run from an environment
with other versions installed still records the pinned model's years.
``bundle.py check`` and the runtime manifest model refuse a malformed record.

The runtime use of the record is tested in ``tests/test_dataset_years.py``.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.test_certify_data_release import (
    MANIFEST_URI,
    UK_MANIFEST_URI,
    _bundle_source_payload,
    _load_bundle_script,
    _populace_manifest_payload_without_regions,
    _uk_release_manifest_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_MANIFEST_PATH = (
    REPO_ROOT / "src" / "policyengine" / "data" / "bundle" / "manifest.json"
)

MALFORMED_RECORDS = [
    pytest.param([], id="empty"),
    pytest.param([2025, 2024], id="descending"),
    pytest.param([2024, 2024, 2025], id="duplicate"),
    pytest.param([2024, "2025"], id="text"),
    pytest.param([2024, True], id="boolean"),
    pytest.param([2024.0, 2025.0], id="decimal"),
    pytest.param("2024-2035", id="not-a-list"),
]


def _shipped_bundle() -> dict:
    return json.loads(BUNDLE_MANIFEST_PATH.read_text())


def _certification():
    return importlib.import_module("policyengine.provenance.certification")


# --- The shipped manifest ---------------------------------------------------------


@pytest.mark.parametrize("country_id", ["uk", "us"])
def test_the_manifest_records_supported_years_for_every_country(country_id):
    certified = _shipped_bundle()["data_releases"][country_id][
        "certified_data_artifact"
    ]
    recorded = certified.get("supported_years")

    assert isinstance(recorded, list) and recorded, (
        f"data_releases.{country_id}.certified_data_artifact records no supported_years"
    )
    assert all(type(year) is int for year in recorded)
    assert recorded == sorted(set(recorded))


def test_the_recorded_us_years_start_with_the_early_year_allowance():
    from policyengine.provenance.dataset_years import US_EARLY_YEAR_ALLOWANCE

    recorded = _shipped_bundle()["data_releases"]["us"]["certified_data_artifact"][
        "supported_years"
    ]

    assert recorded[0] == 2022
    assert US_EARLY_YEAR_ALLOWANCE <= set(recorded)


def test_the_runtime_manifest_model_carries_the_recorded_years():
    from policyengine.provenance.manifest import get_release_manifest

    recorded = _shipped_bundle()["data_releases"]["us"]["certified_data_artifact"][
        "supported_years"
    ]

    certified = get_release_manifest("us").certified_data_artifact
    assert certified is not None
    assert certified.supported_years == recorded


# --- The record's form ------------------------------------------------------------


@pytest.mark.parametrize("malformed", MALFORMED_RECORDS)
def test_the_manifest_model_refuses_a_malformed_record(malformed):
    from pydantic import ValidationError

    from policyengine.provenance.manifest import CertifiedDataArtifact

    with pytest.raises(ValidationError, match="supported_years"):
        CertifiedDataArtifact(
            dataset="populace_us_2024",
            uri="hf://policyengine/populace-us/populace_us_2024.h5@tag",
            supported_years=malformed,
        )


@pytest.mark.parametrize("malformed", MALFORMED_RECORDS)
def test_the_bundle_check_refuses_a_malformed_record(malformed):
    from policyengine.provenance import bundle_validation

    bundle = _shipped_bundle()
    bundle["data_releases"]["us"]["certified_data_artifact"]["supported_years"] = (
        malformed
    )

    with pytest.raises(
        ValueError, match=r"data_releases\.us\.certified_data_artifact\.supported_years"
    ):
        bundle_validation.validate_supported_years(bundle)


def test_the_bundle_check_accepts_a_certificate_without_the_record():
    """Certificates from before the record existed omit it; the runtime then
    computes the years from the source."""

    from policyengine.provenance import bundle_validation

    bundle = _shipped_bundle()
    for release in bundle["data_releases"].values():
        release["certified_data_artifact"].pop("supported_years", None)

    bundle_validation.validate_supported_years(bundle)


def test_the_bundle_check_command_validates_the_record(monkeypatch, capsys):
    maintenance = _load_bundle_script(monkeypatch)
    import generate_bundle_artifacts

    bundle = _shipped_bundle()
    bundle["data_releases"]["us"]["certified_data_artifact"]["supported_years"] = [
        2025,
        2024,
    ]
    monkeypatch.setattr(
        generate_bundle_artifacts, "load_bundle_manifest", lambda *arguments: bundle
    )
    monkeypatch.setattr(
        generate_bundle_artifacts,
        "generate",
        lambda **keyword_arguments: 0,
    )

    with pytest.raises(SystemExit):
        maintenance.main(["check"])

    assert "certified_data_artifact.supported_years" in capsys.readouterr().err


# --- Certification writes the record -----------------------------------------------


def _manifest_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.content = json.dumps(payload).encode()
    return response


def _certify(bundle_path: Path, *, country: str, manifest_uri: str, payload: dict):
    """Certify with every network call stood in for; returns the record calls."""

    record_calls = []

    def certified_supported_years(country_id, data_release, **keyword_arguments):
        record_calls.append((country_id, data_release, keyword_arguments))
        return [2024, 2025, 2026]

    with (
        patch(
            "policyengine.provenance.certification.requests.get",
            return_value=_manifest_response(payload),
        ),
        patch("policyengine.provenance.certification.head_artifact", return_value=True),
        patch(
            "policyengine.provenance.certification.head_release_file",
            return_value=True,
        ),
        patch(
            "policyengine.provenance.certification.head_artifact_reference",
            return_value=True,
        ),
        patch(
            "policyengine.provenance.certification.fetch_pypi_wheel_metadata",
            return_value={"sha256": "d" * 64, "url": "https://example"},
        ),
        patch(
            "policyengine.provenance.certification.policyengine_version",
            return_value="9.9.9",
        ),
        patch(
            "policyengine.provenance.certification.certified_supported_years",
            side_effect=certified_supported_years,
        ),
    ):
        _certification().certify_data_release(
            country=country,
            data_producer="populace",
            manifest_uri=manifest_uri,
            model_version="2.89.2" if country == "uk" else "1.723.0",
            bundle_path=bundle_path,
        )
    return record_calls


def _source_bundle(tmp_path: Path) -> Path:
    payload = _bundle_source_payload()
    payload["packages"]["policyengine-core"] = {
        "name": "policyengine-core",
        "version": "3.33.3",
    }
    payload["packages"]["spm-calculator"] = {
        "name": "spm-calculator",
        "version": "1.0.0",
    }
    bundle_path = tmp_path / "manifest.json"
    bundle_path.write_text(json.dumps(payload) + "\n")
    return bundle_path


def test_certification_records_the_years_of_the_certified_dataset(tmp_path):
    bundle_path = _source_bundle(tmp_path)

    record_calls = _certify(
        bundle_path,
        country="uk",
        manifest_uri=UK_MANIFEST_URI,
        payload=_uk_release_manifest_payload(),
    )

    release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
    assert release["certified_data_artifact"]["supported_years"] == [2024, 2025, 2026]
    ((country_id, data_release, keyword_arguments),) = record_calls
    assert country_id == "uk"
    assert data_release["default_dataset"] == "populace_us_2024"
    assert data_release["certified_data_artifact"]["sha256"] == "a" * 64
    assert keyword_arguments["packages"] == {
        "policyengine-uk": "2.89.2",
        "policyengine-core": "3.33.3",
    }


def test_us_certification_computes_the_years_with_the_pinned_spm_calculator(
    tmp_path,
):
    bundle_path = _source_bundle(tmp_path)

    record_calls = _certify(
        bundle_path,
        country="us",
        manifest_uri=MANIFEST_URI,
        payload=_populace_manifest_payload_without_regions(),
    )

    ((_, _, keyword_arguments),) = record_calls
    assert keyword_arguments["packages"] == {
        "policyengine-us": "1.723.0",
        "policyengine-core": "3.33.3",
        "spm-calculator": "1.0.0",
    }


# --- Computing the record from the certified bytes ---------------------------------


def _local_data_release(tmp_path: Path, contents: bytes) -> tuple[dict, Path]:
    """The shipped US record, pointed at a verified local copy in tmp_path."""

    release = _shipped_bundle()["data_releases"]["us"]
    default_dataset = release["default_dataset"]
    digest = hashlib.sha256(contents).hexdigest()
    release["datasets"][default_dataset]["sha256"] = digest
    release["certified_data_artifact"]["sha256"] = digest
    local_copy = tmp_path / release["datasets"][default_dataset]["path"]
    local_copy.write_bytes(contents)
    return release, local_copy


PINNED_US_PACKAGES = {
    "policyengine-us": "2.2.1",
    "policyengine-core": "3.33.3",
    "spm-calculator": "1.0.0",
}


def _environment_run(printed: dict, commands: list):
    def run(command, **keyword_arguments):
        commands.append((command, keyword_arguments))
        return subprocess.CompletedProcess(
            command, 0, stdout="a warning\n" + json.dumps(printed) + "\n", stderr=""
        )

    return run


def test_the_record_is_computed_on_the_certified_bytes_with_exact_pins(tmp_path):
    release, local_copy = _local_data_release(tmp_path, b"certified bytes")
    commands: list = []
    run = _environment_run(
        {"package_versions": PINNED_US_PACKAGES, "supported_years": [2022, 2023]},
        commands,
    )

    recorded = _certification().certified_supported_years(
        "us", release, packages=PINNED_US_PACKAGES, data_dir=tmp_path, run=run
    )

    assert recorded == [2022, 2023]
    ((command, keyword_arguments),) = commands
    assert command[:5] == ["uv", "run", "--isolated", "--no-project", "--no-config"]
    pins = [
        command[position + 1]
        for position, argument in enumerate(command)
        if argument == "--with"
    ]
    assert pins == [
        "policyengine-core==3.33.3",
        "policyengine-us==2.2.1",
        "spm-calculator==1.0.0",
    ]
    assert "us" in command
    assert str(local_copy) in command
    assert "VIRTUAL_ENV" not in keyword_arguments["env"]


def test_the_record_refuses_a_certified_dataset_without_a_hash(tmp_path):
    release, _ = _local_data_release(tmp_path, b"certified bytes")
    del release["datasets"][release["default_dataset"]]["sha256"]

    with pytest.raises(_certification().CertificationError, match="sha256"):
        _certification().certified_supported_years(
            "us",
            release,
            packages=PINNED_US_PACKAGES,
            data_dir=tmp_path,
            run=_environment_run({}, []),
        )


def test_the_record_refuses_an_environment_with_other_versions(tmp_path):
    release, _ = _local_data_release(tmp_path, b"certified bytes")
    resolved = {**PINNED_US_PACKAGES, "spm-calculator": "1.0.1"}

    with pytest.raises(_certification().CertificationError, match="spm-calculator"):
        _certification().certified_supported_years(
            "us",
            release,
            packages=PINNED_US_PACKAGES,
            data_dir=tmp_path,
            run=_environment_run(
                {"package_versions": resolved, "supported_years": [2024]}, []
            ),
        )


@pytest.mark.parametrize("malformed", MALFORMED_RECORDS)
def test_the_record_refuses_malformed_computed_years(tmp_path, malformed):
    release, _ = _local_data_release(tmp_path, b"certified bytes")

    with pytest.raises(_certification().CertificationError, match="supported years"):
        _certification().certified_supported_years(
            "us",
            release,
            packages=PINNED_US_PACKAGES,
            data_dir=tmp_path,
            run=_environment_run(
                {"package_versions": PINNED_US_PACKAGES, "supported_years": malformed},
                [],
            ),
        )


def test_a_failed_environment_is_refused_with_its_error(tmp_path):
    release, _ = _local_data_release(tmp_path, b"certified bytes")

    def run(command, **keyword_arguments):
        raise subprocess.CalledProcessError(
            1, command, stderr="No solution found when resolving --with dependencies"
        )

    with pytest.raises(_certification().CertificationError, match="No solution found"):
        _certification().certified_supported_years(
            "us", release, packages=PINNED_US_PACKAGES, data_dir=tmp_path, run=run
        )


# --- Recording the years for the current bundle -------------------------------------


def test_recording_writes_only_the_years_for_the_pinned_bundle(tmp_path):
    shipped = _shipped_bundle()
    for release in shipped["data_releases"].values():
        release["certified_data_artifact"].pop("supported_years", None)
    bundle_path = tmp_path / "manifest.json"
    bundle_path.write_text(json.dumps(shipped, indent=2, sort_keys=True) + "\n")
    record_calls = []

    def certified_supported_years(country_id, data_release, **keyword_arguments):
        record_calls.append((country_id, keyword_arguments))
        return [2022, 2023, 2024]

    with patch(
        "policyengine.provenance.certification.certified_supported_years",
        side_effect=certified_supported_years,
    ):
        recorded = _certification().record_supported_years(
            "us", bundle_path=bundle_path, data_dir=tmp_path
        )

    written = json.loads(bundle_path.read_text())
    assert recorded == [2022, 2023, 2024]
    assert written["data_releases"]["us"]["certified_data_artifact"][
        "supported_years"
    ] == [2022, 2023, 2024]
    written["data_releases"]["us"]["certified_data_artifact"].pop("supported_years")
    assert written == shipped
    ((country_id, keyword_arguments),) = record_calls
    assert country_id == "us"
    assert keyword_arguments["packages"] == {
        package_name: shipped["packages"][package_name]["version"]
        for package_name in ("policyengine-us", "policyengine-core", "spm-calculator")
    }


def test_the_record_command_forwards_to_recording(monkeypatch, tmp_path):
    maintenance = _load_bundle_script(monkeypatch)
    import generate_bundle_artifacts

    certification = _certification()
    record_calls = []

    def record_supported_years(country_id, **keyword_arguments):
        record_calls.append((country_id, keyword_arguments))
        return [2024]

    monkeypatch.setattr(certification, "record_supported_years", record_supported_years)
    monkeypatch.setattr(
        generate_bundle_artifacts, "generate", lambda **keyword_arguments: 0
    )

    assert (
        maintenance.main(
            ["record-supported-years", "--country", "uk", "--data-dir", str(tmp_path)]
        )
        == 0
    )
    ((country_id, keyword_arguments),) = record_calls
    assert country_id == "uk"
    assert keyword_arguments["data_dir"] == tmp_path
