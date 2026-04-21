"""Tests for the PreservationMirror extension to DataReleaseManifest."""

import pytest

from policyengine.provenance.manifest import (
    DataPackageVersion,
    DataReleaseArtifact,
    DataReleaseManifest,
    PackageVersion,
    PreservationMirror,
)


class TestPreservationMirror:
    def test_minimal_mirror_has_only_kind_and_url(self):
        mirror = PreservationMirror(
            kind="zenodo",
            url="https://zenodo.org/records/10000000/files/enhanced_cps_2024.h5",
        )
        assert mirror.kind == "zenodo"
        assert mirror.url.endswith("enhanced_cps_2024.h5")
        assert mirror.doi is None
        assert mirror.sha256 is None
        assert mirror.deposited_at is None

    def test_full_mirror_roundtrips_through_pydantic(self):
        mirror = PreservationMirror(
            kind="zenodo",
            url="https://zenodo.org/records/10000000/files/enhanced_cps_2024.h5",
            doi="10.5281/zenodo.10000000",
            sha256="a" * 64,
            deposited_at="2026-04-21T12:00:00Z",
        )
        dumped = mirror.model_dump()
        round_tripped = PreservationMirror.model_validate(dumped)
        assert round_tripped == mirror


class TestDataReleaseArtifactWithMirror:
    def test_artifact_defaults_to_no_mirrors(self):
        artifact = DataReleaseArtifact(
            kind="dataset",
            path="enhanced_cps_2024.h5",
            repo_id="policyengine/policyengine-us-data",
            revision="1.85.2",
            sha256="a" * 64,
        )
        assert artifact.preservation_mirrors == []

    def test_artifact_accepts_multiple_mirrors(self):
        mirrors = [
            PreservationMirror(
                kind="zenodo",
                url="https://zenodo.org/records/10000000/files/enhanced_cps_2024.h5",
                doi="10.5281/zenodo.10000000",
            ),
            PreservationMirror(
                kind="archival_gcs",
                url="https://storage.googleapis.com/policyengine-preservation/enhanced_cps_2024.h5",
            ),
        ]
        artifact = DataReleaseArtifact(
            kind="dataset",
            path="enhanced_cps_2024.h5",
            repo_id="policyengine/policyengine-us-data",
            revision="1.85.2",
            sha256="a" * 64,
            preservation_mirrors=mirrors,
        )
        assert len(artifact.preservation_mirrors) == 2
        assert {m.kind for m in artifact.preservation_mirrors} == {
            "zenodo",
            "archival_gcs",
        }

    def test_primary_uri_still_derives_from_hf_fields(self):
        artifact = DataReleaseArtifact(
            kind="dataset",
            path="enhanced_cps_2024.h5",
            repo_id="policyengine/policyengine-us-data",
            revision="1.85.2",
            preservation_mirrors=[
                PreservationMirror(
                    kind="zenodo",
                    url="https://zenodo.org/records/10000000/files/enhanced_cps_2024.h5",
                )
            ],
        )
        assert artifact.uri.startswith("hf://")
        assert "policyengine-us-data" in artifact.uri


class TestDataReleaseManifestPreservationDois:
    def test_manifest_defaults_to_empty_preservation_dois(self):
        manifest = DataReleaseManifest(
            schema_version=1,
            data_package=DataPackageVersion(
                name="policyengine-us-data",
                version="1.85.2",
                repo_id="policyengine/policyengine-us-data",
            ),
        )
        assert manifest.preservation_dois == []

    def test_manifest_carries_dois_when_deposited(self):
        manifest = DataReleaseManifest(
            schema_version=1,
            data_package=DataPackageVersion(
                name="policyengine-us-data",
                version="1.85.2",
                repo_id="policyengine/policyengine-us-data",
            ),
            preservation_dois=[
                "10.5281/zenodo.10000000",
                "10.5281/zenodo.10000001",
            ],
        )
        assert manifest.preservation_dois == [
            "10.5281/zenodo.10000000",
            "10.5281/zenodo.10000001",
        ]

    def test_round_trip_with_preservation_metadata(self):
        mirror = PreservationMirror(
            kind="zenodo",
            url="https://zenodo.org/records/10000000/files/enhanced_cps_2024.h5",
            doi="10.5281/zenodo.10000000",
            sha256="b" * 64,
        )
        artifact = DataReleaseArtifact(
            kind="dataset",
            path="enhanced_cps_2024.h5",
            repo_id="policyengine/policyengine-us-data",
            revision="1.85.2",
            sha256="b" * 64,
            preservation_mirrors=[mirror],
        )
        # Use PackageVersion (not DataPackageVersion) because the
        # manifest's ``data_package`` field is typed as the base class.
        # Round-tripping through JSON serialization narrows any
        # subclass instance back to the declared type, which is fine
        # for our purposes but makes strict equality unstable.
        manifest = DataReleaseManifest(
            schema_version=1,
            data_package=PackageVersion(
                name="policyengine-us-data",
                version="1.85.2",
            ),
            artifacts={"enhanced_cps_2024": artifact},
            preservation_dois=["10.5281/zenodo.10000000"],
        )
        json_bytes = manifest.model_dump_json().encode("utf-8")
        restored = DataReleaseManifest.model_validate_json(json_bytes)
        assert restored == manifest


def test_backwards_compatibility_old_manifest_without_preservation_fields():
    """A manifest JSON emitted before the preservation fields existed must
    still validate — the new fields have defaults, not required flags."""
    legacy_json = """{
        "schema_version": 1,
        "data_package": {
            "name": "policyengine-us-data",
            "version": "1.78.2",
            "repo_id": "policyengine/policyengine-us-data"
        },
        "artifacts": {
            "enhanced_cps_2024": {
                "kind": "dataset",
                "path": "enhanced_cps_2024.h5",
                "repo_id": "policyengine/policyengine-us-data",
                "revision": "1.78.2"
            }
        }
    }"""
    manifest = DataReleaseManifest.model_validate_json(legacy_json)
    assert manifest.preservation_dois == []
    artifact = manifest.artifacts["enhanced_cps_2024"]
    assert artifact.preservation_mirrors == []
