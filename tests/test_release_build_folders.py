"""Microcosm builds published side by side in their own release folders.

In this layout each build is published once, in ``releases/<release>/<build>/``,
and never changed afterwards; a root ``releases.json`` records which build of
each release is current, and no new Hugging Face tags are made. Each build's
``release_manifest.json`` names its ``release`` and ``build`` as strings
(microcosm-emitter#24 checks that they equal the folder's names).

The manifest shape below is assumed until Microcosm's release writer change
(H2c) defines it: top-level ``release`` and ``build`` strings, the existing
``artifacts`` entries with bare file names, and no ``cut_tag``.

Invariants:

- a build is named by its ``build``, so two builds of one release never match;
- a manifest published before the layout (``build`` an object, maybe with
  ``cut_tag``) is read exactly as before.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from policyengine.provenance.manifest import (
    DataReleaseManifest,
    release_build_id,
)

REPOSITORY = "policyengine/populace-uk-private"
NATIONAL_RELEASE = "microcosm-uk-2024-25-national"
NATIONAL_BUILD = "uk-frs-calibration-attempt-20261019T083323Z-6cba5d71"
EARLIER_NATIONAL_BUILD = "uk-frs-calibration-attempt-20261014T214443Z-d12ff9b3"
UK_MODEL_VERSION = "2.126.12"


def folder_layout_manifest_payload(
    release: str = NATIONAL_RELEASE,
    build: str = NATIONAL_BUILD,
) -> dict:
    """A national release manifest in the side-by-side layout."""

    return {
        "schema_version": 1,
        "release": release,
        "build": build,
        "data_package": {"name": "microcosm-data", "version": "0.1.0"},
        "default_datasets": {"national": "microcosm_uk_2024_25"},
        "compatible_model_packages": [
            {"name": "policyengine-uk", "specifier": f"=={UK_MODEL_VERSION}"}
        ],
        "artifacts": {
            "microcosm_uk_2024_25": {
                "kind": "microdata",
                "role": "dataset",
                "path": "microcosm_uk_2024_25.h5",
                "repo_id": REPOSITORY,
                "revision": "main",
                "sha256": "a" * 64,
            },
            "calibration_diagnostics": {
                "kind": "diagnostics",
                "role": "calibration_diagnostics",
                "path": "calibration_diagnostics.json",
                "repo_id": REPOSITORY,
                "revision": "main",
                "sha256": "b" * 64,
            },
        },
    }


def tagged_layout_manifest_payload() -> dict:
    """A manifest published before the layout: ``build`` is an object."""

    tag = f"{NATIONAL_RELEASE}-20261019T083323Z-6cba5d71"
    payload = folder_layout_manifest_payload()
    del payload["release"]
    payload["build"] = {
        "build_id": NATIONAL_RELEASE,
        "cut_tag": tag,
        "built_with_model_package": {
            "name": "policyengine-uk",
            "version": UK_MODEL_VERSION,
        },
    }
    for artifact in payload["artifacts"].values():
        artifact["revision"] = tag
    return payload


class TestBuildFolderManifest:
    def test__given_folder_layout_manifest__then_build_is_the_data_build_id(self):
        manifest = DataReleaseManifest.model_validate(folder_layout_manifest_payload())

        assert manifest.release == NATIONAL_RELEASE
        assert release_build_id(manifest.build) == NATIONAL_BUILD

    def test__given_folder_layout_manifest__then_names_its_build_folder(self):
        manifest = DataReleaseManifest.model_validate(folder_layout_manifest_payload())

        assert manifest.build_folder == (
            f"releases/{NATIONAL_RELEASE}/{NATIONAL_BUILD}"
        )

    def test__given_two_builds_of_one_release__then_their_build_ids_differ(self):
        newer = DataReleaseManifest.model_validate(folder_layout_manifest_payload())
        earlier = DataReleaseManifest.model_validate(
            folder_layout_manifest_payload(build=EARLIER_NATIONAL_BUILD)
        )

        assert release_build_id(newer.build) != release_build_id(earlier.build)

    def test__given_folder_layout_manifest__then_records_no_build_details(self):
        # The string build carries no built_with_* packages; until Microcosm
        # says where they go, certification relies on compatibility claims.
        manifest = DataReleaseManifest.model_validate(folder_layout_manifest_payload())

        assert manifest.build is not None
        assert manifest.build.built_with_model_package is None
        assert manifest.build.cut_tag is None

    def test__given_folder_layout_manifest__then_dump_keeps_build_a_string(self):
        manifest = DataReleaseManifest.model_validate(folder_layout_manifest_payload())

        dumped = manifest.model_dump(mode="json", exclude_none=True)

        assert dumped["release"] == NATIONAL_RELEASE
        assert dumped["build"] == NATIONAL_BUILD
        assert DataReleaseManifest.model_validate(dumped) == manifest

    def test__given_folder_layout_artifact_without_revision__then_parses(self):
        payload = folder_layout_manifest_payload()
        for artifact in payload["artifacts"].values():
            del artifact["revision"]

        manifest = DataReleaseManifest.model_validate(payload)

        assert manifest.artifacts["microcosm_uk_2024_25"].revision is None

    def test__given_tagged_layout_artifact_without_revision__then_refuses(self):
        payload = tagged_layout_manifest_payload()
        del payload["artifacts"]["microcosm_uk_2024_25"]["revision"]

        with pytest.raises(ValidationError, match="revision"):
            DataReleaseManifest.model_validate(payload)

    def test__given_string_build_without_release__then_refuses(self):
        payload = folder_layout_manifest_payload()
        del payload["release"]

        with pytest.raises(ValidationError, match="release"):
            DataReleaseManifest.model_validate(payload)

    def test__given_release_with_object_build__then_refuses(self):
        payload = tagged_layout_manifest_payload()
        payload["release"] = NATIONAL_RELEASE

        with pytest.raises(ValidationError, match="build"):
            DataReleaseManifest.model_validate(payload)

    @pytest.mark.parametrize(
        ("field_name", "unsafe_name"),
        [("release", "../microcosm-uk"), ("build", "attempt/../other")],
    )
    def test__given_unsafe_release_or_build_name__then_refuses(
        self, field_name, unsafe_name
    ):
        payload = folder_layout_manifest_payload()
        payload[field_name] = unsafe_name

        with pytest.raises(ValidationError, match=field_name):
            DataReleaseManifest.model_validate(payload)

    def test__given_tagged_layout_manifest__then_cut_tag_stays_the_data_build_id(
        self,
    ):
        manifest = DataReleaseManifest.model_validate(tagged_layout_manifest_payload())

        assert manifest.release is None
        assert manifest.build_folder is None
        assert release_build_id(manifest.build) == (
            f"{NATIONAL_RELEASE}-20261019T083323Z-6cba5d71"
        )
        dumped = manifest.model_dump(mode="json", exclude_none=True)
        assert dumped["build"]["build_id"] == NATIONAL_RELEASE
