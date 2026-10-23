"""The local manifest is an opt-in transport for the bundle's exact bytes.

The unset cases characterize certification on main (485dc2330), including
fetched, bundled-offline, and refused pairs. No credentials or network are used.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from policyengine.provenance import manifest as manifests

ENVIRONMENT_VARIABLE = "POLICYENGINE_UK_DATA_MANIFEST_FILE"
MODEL = "2.130.1"
OTHER_MODEL = "2.130.2"
CORE = "3.33.0"
BUILD = "test-data-build"
FINGERPRINT = "sha256:test-build"
_DEFAULT = object()


def _payload():
    return {
        "schema_version": 1,
        "data_package": {"name": "policyengine-uk-data", "version": "test-release"},
        "build": {
            "build_id": BUILD,
            "built_with_core_package": {"name": "policyengine-core", "version": CORE},
            "built_with_model_package": {
                "name": "policyengine-uk",
                "version": MODEL,
                "git_sha": "abc123",
                "data_build_fingerprint": FINGERPRINT,
            },
        },
        "default_datasets": {"national": "test_dataset"},
        "artifacts": {
            "test_dataset": {
                "kind": "microdata",
                "path": "test_dataset.h5",
                "repo_id": "policyengine/test-data",
                "revision": "test-release",
                "sha256": "d" * 64,
            }
        },
    }


def _manifest_bytes(payload):
    # Whitespace and the final newline are deliberately part of the pin.
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def _qualified_certification():
    return {
        "compatibility_basis": "qualified_exact_pair",
        "certified_for_model_version": MODEL,
        "certified_for_core_version": CORE,
        "data_build_id": BUILD,
        "built_with_model_version": MODEL,
        "built_with_model_git_sha": "abc123",
        "data_build_fingerprint": FINGERPRINT,
        "qualification_pair_id": "a" * 64,
        "certified_by": "test-bundle",
    }


def _install_bundle(tmp_path, monkeypatch, payload=None, certification=_DEFAULT):
    """Install synthetic package resources, exercising the real TRO pin reader."""
    manifests.get_data_release_manifest.cache_clear()
    manifests.get_release_manifest.cache_clear()
    payload = payload if payload is not None else _payload()
    raw_bytes = _manifest_bytes(payload)
    local_path = tmp_path / "release_manifest.json"
    local_path.write_bytes(raw_bytes)
    resource_root = tmp_path / "package"
    bundle_dir = resource_root / "data" / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    country = {
        "schema_version": 1,
        "country_id": "uk",
        "policyengine_version": "6.10.1",
        "model_package": {"name": "policyengine-uk", "version": MODEL},
        "data_package": {
            "name": "policyengine-uk-data",
            "version": "test-release",
            "repo_id": "policyengine/test-data",
            "release_manifest_revision": "f" * 40,
        },
        "default_dataset": "test_dataset",
        "certification": (
            _qualified_certification() if certification is _DEFAULT else certification
        ),
    }
    (bundle_dir / "manifest.json").write_text(
        json.dumps({"data_releases": {"uk": country}})
    )
    tro = {
        "@graph": [
            {
                "@id": "tro",
                "trov:hasArrangement": [
                    {
                        "trov:hasArtifactLocation": [
                            {
                                "trov:hasArtifact": {
                                    "@id": "composition/1/artifact/data_release_manifest"
                                },
                                "trov:hasLocation": (
                                    "https://huggingface.co/policyengine/test-data/resolve/"
                                    f"{'f' * 40}/release_manifest.json"
                                ),
                            }
                        ]
                    }
                ],
                "trov:hasComposition": {
                    "@id": "composition/1",
                    "trov:hasArtifact": [
                        {
                            "@id": "composition/1/artifact/data_release_manifest",
                            "trov:sha256": hashlib.sha256(raw_bytes).hexdigest(),
                        }
                    ],
                },
            }
        ]
    }
    trace_path = bundle_dir / "uk.trace.tro.jsonld"
    trace_path.write_text(json.dumps(tro))
    monkeypatch.setattr(manifests, "files", lambda package: resource_root)
    return local_path, trace_path, raw_bytes


@pytest.fixture(autouse=True)
def _isolated_manifest_settings(monkeypatch):
    monkeypatch.delenv(ENVIRONMENT_VARIABLE, raising=False)
    monkeypatch.delenv("POLICYENGINE_US_DATA_MANIFEST_FILE", raising=False)
    manifests.get_data_release_manifest.cache_clear()
    manifests.get_release_manifest.cache_clear()
    yield
    manifests.get_data_release_manifest.cache_clear()
    manifests.get_release_manifest.cache_clear()


def _certify(**kwargs):
    implementation = kwargs.pop(
        "_implementation", manifests.certify_data_release_compatibility
    )
    return implementation(
        "uk",
        runtime_model_version=kwargs.pop("runtime_model_version", MODEL),
        runtime_core_version=kwargs.pop("runtime_core_version", CORE),
        **kwargs,
    )


def test_matching_local_manifest_certifies_without_a_network_call(
    tmp_path, monkeypatch
):
    local_path, _, raw_bytes = _install_bundle(tmp_path, monkeypatch)
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(local_path))

    with patch.object(
        manifests.requests, "get", side_effect=requests.ConnectionError("HF is down")
    ) as network:
        certification = _certify()
        loaded = manifests.get_data_release_manifest("uk")

    network.assert_not_called()
    assert (
        certification.compatibility_basis == "exact_build_model_version_local_manifest"
    )
    assert certification.certified_for_model_version == MODEL
    assert certification.data_build_id == BUILD
    assert certification.data_build_fingerprint == FINGERPRINT
    assert loaded.source_sha256 == hashlib.sha256(raw_bytes).hexdigest()
    assert loaded.artifacts["test_dataset"].revision == "f" * 40
    # Source information stays out of public manifest JSON round trips.
    expected = manifests.DataReleaseManifest.model_validate_json(raw_bytes)
    expected.artifacts["test_dataset"].revision = "f" * 40
    assert loaded.model_dump(mode="json") == expected.model_dump(mode="json")


@settings(
    max_examples=80,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    position=st.integers(min_value=0, max_value=len(_manifest_bytes(_payload())) - 1)
)
def test_any_one_byte_mutation_is_refused(tmp_path, monkeypatch, position):
    local_path, _, raw_bytes = _install_bundle(tmp_path, monkeypatch)
    altered = bytearray(raw_bytes)
    altered[position] ^= 1
    local_path.write_bytes(altered)
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(local_path))

    with patch.object(manifests.requests, "get") as network:
        with pytest.raises(ValueError) as error:
            _certify()

    network.assert_not_called()
    assert hashlib.sha256(raw_bytes).hexdigest() in str(error.value)
    assert hashlib.sha256(altered).hexdigest() in str(error.value)


def test_another_release_is_refused_even_with_an_environment_digest(
    tmp_path, monkeypatch
):
    local_path, _, raw_bytes = _install_bundle(tmp_path, monkeypatch)
    another_release = _payload()
    another_release["build"]["build_id"] = "another-release"
    altered_bytes = _manifest_bytes(another_release)
    local_path.write_bytes(altered_bytes)
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(local_path))
    monkeypatch.setenv(
        "POLICYENGINE_UK_DATA_MANIFEST_SHA256",
        hashlib.sha256(altered_bytes).hexdigest(),
    )

    with pytest.raises(ValueError) as error:
        _certify()

    assert hashlib.sha256(raw_bytes).hexdigest() in str(error.value)
    assert hashlib.sha256(altered_bytes).hexdigest() in str(error.value)


@pytest.mark.parametrize("failure", ["missing", "unreadable", "directory", "empty"])
def test_bad_local_path_is_a_hard_error(tmp_path, monkeypatch, failure):
    local_path, _, raw_bytes = _install_bundle(tmp_path, monkeypatch)
    setting = str(local_path)
    if failure == "missing":
        local_path.unlink()
    elif failure == "unreadable":
        read_bytes = Path.read_bytes

        def read_unless_local(path):
            if path == local_path:
                raise PermissionError("test permission denied")
            return read_bytes(path)

        monkeypatch.setattr(Path, "read_bytes", read_unless_local)
    elif failure == "directory":
        setting = str(tmp_path)
    else:
        setting = ""
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, setting)

    with patch.object(manifests.requests, "get") as network:
        with pytest.raises(ValueError) as error:
            _certify()

    network.assert_not_called()
    assert ENVIRONMENT_VARIABLE in str(error.value)
    assert hashlib.sha256(raw_bytes).hexdigest() in str(error.value)
    assert "actual" in str(error.value).lower()


@pytest.mark.parametrize(
    "failure",
    [
        "absent-trace",
        "absent-pin",
        "invalid-pin",
        "other-artifact",
        "absent-location",
        "stale-release-location",
        "duplicate-pin",
        "duplicate-location",
        "malformed-graph",
        "malformed-composition",
    ],
)
def test_local_manifest_requires_the_bundled_manifest_artifact_pin(
    tmp_path, monkeypatch, failure
):
    local_path, trace_path, _ = _install_bundle(tmp_path, monkeypatch)
    if failure == "absent-trace":
        trace_path.unlink()
    else:
        tro = json.loads(trace_path.read_text())
        artifact = tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"][0]
        if failure == "absent-pin":
            del artifact["trov:sha256"]
        elif failure == "invalid-pin":
            artifact["trov:sha256"] = "not-a-sha256"
        elif failure == "other-artifact":
            artifact["@id"] = "composition/1/artifact/dataset"
        elif failure == "absent-location":
            del tro["@graph"][0]["trov:hasArrangement"]
        elif failure == "stale-release-location":
            location = tro["@graph"][0]["trov:hasArrangement"][0][
                "trov:hasArtifactLocation"
            ][0]
            location["trov:hasLocation"] = (
                "https://huggingface.co/policyengine/test-data/resolve/"
                "old-release/release_manifest.json"
            )
        elif failure == "duplicate-pin":
            tro["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"].append(
                copy.deepcopy(artifact)
            )
        elif failure == "duplicate-location":
            locations = tro["@graph"][0]["trov:hasArrangement"][0][
                "trov:hasArtifactLocation"
            ]
            locations.append(copy.deepcopy(locations[0]))
        elif failure == "malformed-graph":
            tro["@graph"] = None
        else:
            tro["@graph"][0]["trov:hasComposition"] = []
        trace_path.write_text(json.dumps(tro))
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(local_path))

    with patch.object(manifests.requests, "get") as network:
        with pytest.raises(ValueError, match="(?i)(bundle|pin|digest|sha256)"):
            _certify()

    network.assert_not_called()


@pytest.mark.parametrize("difference", ["model", "core", "build", "model-package"])
def test_a_valid_digest_cannot_widen_exact_pair_certification(
    tmp_path, monkeypatch, difference
):
    payload = _payload()
    runtime = {}
    if difference == "model":
        runtime["runtime_model_version"] = OTHER_MODEL
    elif difference == "core":
        runtime["runtime_core_version"] = "99.0.0"
    elif difference == "build":
        payload["build"]["build_id"] = "another-build"
    else:
        payload["build"]["built_with_model_package"]["name"] = "another-model"
    local_path, _, _ = _install_bundle(tmp_path, monkeypatch, payload)
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(local_path))

    with pytest.raises(ValueError, match="not certified|different model package"):
        _certify(**runtime)


@pytest.mark.parametrize(
    ("mode", "expected_basis"),
    [
        ("fingerprint", "matching_data_build_fingerprint_local_manifest"),
        ("publisher-claim", "legacy_compatible_model_package_local_manifest"),
        ("qualified", "qualified_exact_pair_local_manifest"),
    ],
)
def test_local_transport_retains_existing_certification_bases(
    tmp_path, monkeypatch, mode, expected_basis
):
    payload = _payload()
    payload["build"]["built_with_model_package"]["version"] = OTHER_MODEL
    runtime = {}
    if mode == "fingerprint":
        runtime["runtime_data_build_fingerprint"] = FINGERPRINT
    elif mode == "publisher-claim":
        payload["compatible_model_packages"] = [
            {"name": "policyengine-uk", "specifier": f"=={MODEL}"}
        ]
    local_path, _, _ = _install_bundle(tmp_path, monkeypatch, payload)
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(local_path))

    assert _certify(**runtime).compatibility_basis == expected_basis


def test_local_fingerprint_mismatch_does_not_create_a_new_acceptance_path(
    tmp_path, monkeypatch
):
    payload = _payload()
    payload["build"]["built_with_model_package"]["version"] = OTHER_MODEL
    local_path, _, _ = _install_bundle(
        tmp_path, monkeypatch, payload, certification=None
    )
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(local_path))

    with pytest.raises(ValueError, match="not certified"):
        _certify(runtime_data_build_fingerprint="sha256:different")


def _response(raw_bytes):
    response = Mock()
    response.status_code = 200
    response.content = raw_bytes
    response.text = raw_bytes.decode("utf-8")
    return response


def test_setting_local_manifest_after_a_cached_fetch_still_checks_its_pin(
    tmp_path, monkeypatch
):
    local_path, _, raw_bytes = _install_bundle(tmp_path, monkeypatch)
    with patch.object(manifests.requests, "get", return_value=_response(raw_bytes)):
        assert _certify().compatibility_basis == "exact_build_model_version"
    local_path.write_bytes(raw_bytes + b" ")
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(local_path))

    with patch.object(manifests.requests, "get") as network:
        with pytest.raises(ValueError):
            _certify()

    network.assert_not_called()


@pytest.mark.parametrize("change", ["mutation", "deletion"])
def test_a_successful_local_load_does_not_cache_unchecked_bytes(
    tmp_path, monkeypatch, change
):
    local_path, _, raw_bytes = _install_bundle(tmp_path, monkeypatch)
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(local_path))
    with patch.object(manifests.requests, "get") as network:
        assert (
            _certify().compatibility_basis == "exact_build_model_version_local_manifest"
        )
        if change == "mutation":
            local_path.write_bytes(raw_bytes + b" ")
        else:
            local_path.unlink()
        with pytest.raises(ValueError):
            _certify()
    network.assert_not_called()


@pytest.fixture(scope="module")
def main_certification():
    """Keep the exact main implementation as a differential test oracle."""
    snapshot = (
        Path(__file__).parent
        / "fixtures"
        / "local_manifest"
        / "main_485dc2330_certification.py.txt"
    )
    namespace = vars(manifests).copy()
    exec(compile(snapshot.read_text(), str(snapshot), "exec"), namespace)
    return namespace["certify_data_release_compatibility"]


@pytest.mark.parametrize(
    "case",
    [
        "fetched-exact",
        "fetched-fingerprint",
        "fetched-claim",
        "fetched-qualified",
        "fetched-model-mismatch",
        "fetched-core-mismatch",
        "fetched-build-mismatch",
        "offline-bundled",
        "offline-model-mismatch",
        "offline-fingerprint-mismatch",
    ],
)
def test_unset_setting_matches_main_certification_cases(
    tmp_path, monkeypatch, main_certification, case
):
    """Golden differential of existing release/qualified-pair test scenarios.

    Compare complete results or exact exception types/messages with an unchanged
    main 485dc2330 implementation, then check the characterized expected result.
    Synthetic resources isolate the comparison from future country release pins.
    """
    payload = _payload()
    bundled = _qualified_certification()
    runtime = {}
    expected_error = None
    expected = manifests.DataCertification(
        compatibility_basis="exact_build_model_version",
        certified_for_model_version=MODEL,
        data_build_id=BUILD,
        built_with_model_version=MODEL,
        built_with_model_git_sha="abc123",
        data_build_fingerprint=FINGERPRINT,
    )
    if case in {"fetched-fingerprint", "fetched-claim", "fetched-qualified"}:
        payload["build"]["built_with_model_package"]["version"] = OTHER_MODEL
        expected.built_with_model_version = OTHER_MODEL
    if case == "fetched-fingerprint":
        runtime["runtime_data_build_fingerprint"] = FINGERPRINT
        expected.compatibility_basis = "matching_data_build_fingerprint"
    elif case == "fetched-claim":
        payload["compatible_model_packages"] = [
            {"name": "policyengine-uk", "specifier": f">={MODEL},<3.0.0"}
        ]
        expected.compatibility_basis = "legacy_compatible_model_package"
    elif case in {"fetched-qualified", "offline-bundled"}:
        expected = manifests.DataCertification.model_validate(bundled)
    elif case == "fetched-model-mismatch":
        runtime["runtime_model_version"] = OTHER_MODEL
        expected_error = "Data release manifest is not certified for the runtime model"
    elif case == "fetched-core-mismatch":
        runtime["runtime_core_version"] = "99.0.0"
        expected_error = "Data release manifest is not certified for the runtime core"
    elif case == "fetched-build-mismatch":
        payload["build"]["build_id"] = "another-build"
        expected_error = (
            "Data release manifest is not certified for the remote data build"
        )
    elif case == "offline-model-mismatch":
        runtime["runtime_model_version"] = OTHER_MODEL
        expected = manifests.DataCertification(
            compatibility_basis="unverified_data_release_manifest_unavailable",
            certified_for_model_version=OTHER_MODEL,
            data_build_id=BUILD,
            built_with_model_version=MODEL,
            built_with_model_git_sha="abc123",
            data_build_fingerprint=FINGERPRINT,
            certified_by="test-bundle",
        )
    elif case == "offline-fingerprint-mismatch":
        bundled["compatibility_basis"] = "matching_data_build_fingerprint"
        runtime["runtime_data_build_fingerprint"] = "sha256:different"
        expected_error = "Runtime data build fingerprint does not match the bundled"
    _, _, raw_bytes = _install_bundle(
        tmp_path, monkeypatch, payload, certification=copy.deepcopy(bundled)
    )
    assert ENVIRONMENT_VARIABLE not in manifests.os.environ
    network_settings = (
        {"side_effect": requests.Timeout("offline")}
        if case.startswith("offline-")
        else {"return_value": _response(raw_bytes)}
    )

    def outcome(implementation):
        try:
            return (
                "ok",
                _certify(_implementation=implementation, **runtime).model_dump(),
            )
        except ValueError as error:
            return ("error", type(error), str(error))

    with patch.object(manifests.requests, "get", **network_settings) as network:
        main_outcome = outcome(main_certification)
        manifests.get_data_release_manifest.cache_clear()
        current_outcome = outcome(manifests.certify_data_release_compatibility)

    assert current_outcome == main_outcome
    if expected_error:
        assert current_outcome[0] == "error"
        assert expected_error in current_outcome[2]
    else:
        assert current_outcome == ("ok", expected.model_dump())
    assert network.call_count == 2
