"""A TRO's manifest pin includes every assertion for the JSON-LD node ID."""

from __future__ import annotations

import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from policyengine.provenance import manifest as manifests

ARTIFACT_ID = "composition/1/artifact/data_release_manifest"
PIN = "a" * 64


def _tro():
    return {
        "@graph": [
            {
                "@id": "tro",
                "trov:hasComposition": {
                    "trov:hasArtifact": [{"@id": ARTIFACT_ID, "trov:sha256": PIN}]
                },
                "trov:hasArrangement": [
                    {
                        "trov:hasArtifactLocation": [
                            {
                                "trov:hasArtifact": {"@id": ARTIFACT_ID},
                                "trov:hasLocation": (
                                    "https://huggingface.co/policyengine/test-data/"
                                    "resolve/test-release/release_manifest.json"
                                ),
                            }
                        ]
                    }
                ],
            }
        ]
    }


@pytest.fixture
def read_pin(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "data" / "bundle"
    bundle_dir.mkdir(parents=True)
    country_manifest = manifests.CountryReleaseManifest(
        country_id="uk",
        policyengine_version="6.10.1",
        model_package=manifests.PackageVersion(name="policyengine-uk", version="test"),
        data_package=manifests.DataPackageVersion(
            name="policyengine-uk-data",
            version="test-release",
            repo_id="policyengine/test-data",
        ),
        default_dataset="test_dataset",
    )
    monkeypatch.setattr(manifests, "files", lambda package: tmp_path)
    monkeypatch.setattr(
        manifests, "get_release_manifest", lambda country: country_manifest
    )

    def read(tro):
        (bundle_dir / "uk.trace.tro.jsonld").write_text(json.dumps(tro))
        return manifests.bundled_data_release_manifest_sha256("uk")

    return read


@pytest.mark.parametrize("before_inline_definition", [False, True])
def test_direct_graph_conflicting_manifest_pin_is_refused(
    read_pin, before_inline_definition
):
    tro = _tro()
    duplicate = {"@id": ARTIFACT_ID, "trov:sha256": "0" * 64}
    if before_inline_definition:
        tro["@graph"].insert(0, duplicate)
    else:
        tro["@graph"].append(duplicate)

    with pytest.raises(ValueError, match="no valid SHA-256 pin"):
        read_pin(tro)


@pytest.mark.parametrize(
    "assertion",
    [
        [PIN],
        [PIN, "0" * 64],
        {"@value": PIN},
        {"@value": "0" * 64},
        "not-a-sha256",
        None,
        42,
    ],
)
def test_noncanonical_duplicate_hash_assertions_fail_closed(read_pin, assertion):
    tro = _tro()
    tro["@graph"].append({"@id": ARTIFACT_ID, "trov:sha256": assertion})

    with pytest.raises(ValueError, match="no valid SHA-256 pin"):
        read_pin(tro)


def test_identical_external_definitions_and_references_do_not_add_a_hash(read_pin):
    tro = _tro()
    tro["@graph"].extend(
        [
            {"@id": ARTIFACT_ID, "trov:sha256": PIN.upper()},
            {"extension": {"@id": ARTIFACT_ID, "trov:sha256": PIN}},
            {"@id": ARTIFACT_ID},
        ]
    )

    assert read_pin(tro) == PIN


def test_hash_on_an_existing_artifact_reference_is_checked(read_pin):
    tro = _tro()
    reference = tro["@graph"][0]["trov:hasArrangement"][0]["trov:hasArtifactLocation"][
        0
    ]["trov:hasArtifact"]
    reference["trov:sha256"] = "0" * 64

    with pytest.raises(ValueError, match="no valid SHA-256 pin"):
        read_pin(tro)


@settings(
    max_examples=80,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    placement=st.sampled_from(
        ["graph", "document", "tro", "composition", "arrangement", "location"]
    ),
    wrappers=st.lists(
        st.sampled_from(["list", "property", "graph"]), min_size=0, max_size=8
    ),
    conflicting_hash=st.binary(min_size=32, max_size=32)
    .map(bytes.hex)
    .filter(lambda digest: digest != PIN),
)
def test_conflicting_pin_is_refused_at_any_duplicate_placement(
    read_pin, placement, wrappers, conflicting_hash
):
    tro = _tro()
    duplicate = {"@id": ARTIFACT_ID, "trov:sha256": conflicting_hash}
    for wrapper in wrappers:
        if wrapper == "list":
            duplicate = [duplicate]
        elif wrapper == "graph":
            duplicate = {"@graph": [duplicate]}
        else:
            duplicate = {"extension": duplicate}

    root = tro["@graph"][0]
    if placement == "graph":
        # Keep the surrounding graph canonical so refusal must inspect the
        # nested assertion, rather than fail on an unrelated malformed node.
        tro["@graph"].append({"extension": duplicate})
    else:
        target = {
            "document": tro,
            "tro": root,
            "composition": root["trov:hasComposition"],
            "arrangement": root["trov:hasArrangement"][0],
            "location": root["trov:hasArrangement"][0]["trov:hasArtifactLocation"][0],
        }[placement]
        target["extension"] = duplicate

    with pytest.raises(ValueError, match="no valid SHA-256 pin"):
        read_pin(tro)
