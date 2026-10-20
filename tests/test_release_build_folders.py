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

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from policyengine.provenance.certification import (
    CertificationError,
    certify_data_release,
)
from policyengine.provenance.manifest import (
    CountryReleaseManifest,
    DataReleaseManifest,
    ReleaseBuildFolderError,
    certify_data_release_compatibility,
    get_data_release_manifest,
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


NATIONAL_COMMIT = "0123456789abcdef0123456789abcdef01234567"
DENSE_RELEASE = "microcosm-uk-2024-25-dense"
DENSE_BUILD = "uk-frs-calibration-attempt-20261019T000432Z-4e5f6a7b"
DENSE_COMMIT = "89abcdef0123456789abcdef0123456789abcdef"
NATIONAL_FOLDER = f"releases/{NATIONAL_RELEASE}/{NATIONAL_BUILD}"
DENSE_FOLDER = f"releases/{DENSE_RELEASE}/{DENSE_BUILD}"


def manifest_uri(folder: str, revision: str) -> str:
    return f"hf://dataset/{REPOSITORY}@{revision}/{folder}/release_manifest.json"


NATIONAL_URI = manifest_uri(NATIONAL_FOLDER, NATIONAL_COMMIT)
DENSE_URI = manifest_uri(DENSE_FOLDER, DENSE_COMMIT)


def folder_layout_dense_payload() -> dict:
    """A local-area release manifest in the side-by-side layout."""

    return {
        "schema_version": 1,
        "release": DENSE_RELEASE,
        "build": DENSE_BUILD,
        "data_package": {"name": "microcosm-data", "version": "0.1.0"},
        "dataset_role": "non_default_local_area",
        "is_default": False,
        "default_datasets": {},
        "compatible_model_packages": [
            {"name": "policyengine-uk", "specifier": f"=={UK_MODEL_VERSION}"}
        ],
        "artifacts": {
            "microcosm_uk_2024_25_dense": {
                "kind": "microdata",
                "role": "dataset",
                "path": "microcosm_uk_2024_25_dense.h5",
                "repo_id": REPOSITORY,
                "sha256": "c" * 64,
            },
        },
    }


def manifest_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.content = json.dumps(payload).encode()
    response.text = response.content.decode()
    response.raise_for_status.return_value = None
    return response


def missing_file_response() -> MagicMock:
    response = MagicMock()
    response.status_code = 404
    response.content = b"Entry not found"
    response.text = response.content.decode()
    return response


RELEASES_RECORD_URL = (
    f"https://huggingface.co/datasets/{REPOSITORY}/resolve/main/releases.json"
)


def releases_record_payload(
    withdrawn: frozenset[tuple[str, str]] = frozenset(),
    unlisted: frozenset[tuple[str, str]] = frozenset(),
) -> dict:
    """The repository's ``releases.json``, in the release writer's format.

    Lists both national builds (the newer one current) and the dense build
    (no current build), none withdrawn, except the ``(release, build)`` pairs
    named in ``withdrawn`` or ``unlisted``. Certification never reads
    ``current``, so whether the dense release has one does not matter here.
    """

    builds_by_release = {
        NATIONAL_RELEASE: [EARLIER_NATIONAL_BUILD, NATIONAL_BUILD],
        DENSE_RELEASE: [DENSE_BUILD],
    }
    releases = {}
    for release_name, build_names in builds_by_release.items():
        releases[release_name] = {
            "role": "national_default" if release_name == NATIONAL_RELEASE else "dense",
            "current": NATIONAL_BUILD if release_name == NATIONAL_RELEASE else None,
            "builds": {
                build_name: {
                    "published_at": "2026-10-19T08:33:23Z",
                    "withdrawn": (release_name, build_name) in withdrawn,
                }
                for build_name in build_names
                if (release_name, build_name) not in unlisted
            },
        }
    return {"schema_version": 1, "default": NATIONAL_RELEASE, "releases": releases}


def empty_bundle(tmp_path: Path) -> Path:
    bundle_path = tmp_path / "manifest.json"
    bundle_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "bundle_version": "9.9.9",
                "policyengine_version": "9.9.9",
                "packages": {
                    "policyengine": {"name": "policyengine", "version": "9.9.9"},
                    "policyengine-uk": {"name": "policyengine-uk", "version": "2.0.0"},
                },
                "extras": {},
                "countries": {"uk": {"model_package": "policyengine-uk"}},
                "data_releases": {},
            }
        )
        + "\n"
    )
    return bundle_path


def certify_uk(
    bundle_path: Path,
    manifests: list[dict],
    manifest_uri: str = NATIONAL_URI,
    releases_record: dict | None = None,
    requested_urls: list[str] | None = None,
    **options,
):
    """Certify with fetched files and reachability checks replaced.

    Requests for the repository's ``releases.json`` at ``main`` get
    ``releases_record`` (``releases_record_payload()`` when ``None``, a 404
    when empty); every other request gets the next of ``manifests``. Each
    requested URL is appended to ``requested_urls`` when given.
    """

    record_payload = (
        releases_record_payload() if releases_record is None else releases_record
    )
    manifests_to_serve = list(manifests)

    def fake_get(url: str, headers=None, timeout=None) -> MagicMock:
        if requested_urls is not None:
            requested_urls.append(url)
        if url == RELEASES_RECORD_URL:
            if not record_payload:
                return missing_file_response()
            return manifest_response(record_payload)
        return manifest_response(manifests_to_serve.pop(0))

    with (
        patch(
            "policyengine.provenance.certification.requests.get",
            side_effect=fake_get,
        ),
        patch(
            "policyengine.provenance.certification.head_artifact",
            return_value=True,
        ) as head_artifact,
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
    ):
        result = certify_data_release(
            country="uk",
            data_producer="populace",
            manifest_uri=manifest_uri,
            model_version=UK_MODEL_VERSION,
            bundle_path=bundle_path,
            **options,
        )
    release = json.loads(bundle_path.read_text())["data_releases"]["uk"]
    return result, release, head_artifact


class TestCertifyBuildFolder:
    def test__given_folder_layout_release__then_datasets_are_pinned_in_its_folder(
        self, tmp_path
    ):
        _, release, _ = certify_uk(
            empty_bundle(tmp_path), [folder_layout_manifest_payload()]
        )

        assert release["datasets"]["microcosm_uk_2024_25"] == {
            "path": f"{NATIONAL_FOLDER}/microcosm_uk_2024_25.h5",
            "revision": NATIONAL_COMMIT,
            "repo_id": REPOSITORY,
            "sha256": "a" * 64,
        }
        assert release["datasets"]["calibration_diagnostics"]["path"] == (
            f"{NATIONAL_FOLDER}/calibration_diagnostics.json"
        )
        assert release["region_datasets"]["national"] == {
            "path_template": f"{NATIONAL_FOLDER}/microcosm_uk_2024_25.h5"
        }
        assert release["default_dataset_uri"] == (
            f"hf://{REPOSITORY}/{NATIONAL_FOLDER}/microcosm_uk_2024_25.h5"
            f"@{NATIONAL_COMMIT}"
        )

    def test__given_folder_layout_release__then_runtime_reads_its_folder_manifest(
        self, tmp_path
    ):
        _, release, _ = certify_uk(
            empty_bundle(tmp_path), [folder_layout_manifest_payload()]
        )

        assert release["data_package"]["release_manifest_path"] == (
            f"{NATIONAL_FOLDER}/release_manifest.json"
        )
        assert release["data_package"]["release_manifest_revision"] == (NATIONAL_COMMIT)

    def test__given_folder_layout_release__then_its_build_names_the_certificate(
        self, tmp_path
    ):
        result, release, _ = certify_uk(
            empty_bundle(tmp_path), [folder_layout_manifest_payload()]
        )

        assert release["version"] == NATIONAL_BUILD
        assert release["certification"]["data_build_id"] == NATIONAL_BUILD
        assert release["certified_data_artifact"]["build_id"] == NATIONAL_BUILD
        assert result.build_id == NATIONAL_BUILD

    def test__given_folder_layout_release__then_checks_the_dataset_in_its_folder(
        self, tmp_path
    ):
        _, _, head_artifact = certify_uk(
            empty_bundle(tmp_path), [folder_layout_manifest_payload()]
        )

        checked = head_artifact.call_args.args[0]
        assert (checked.path, checked.revision) == (
            f"{NATIONAL_FOLDER}/microcosm_uk_2024_25.h5",
            NATIONAL_COMMIT,
        )

    def test__given_artifacts_without_revision__then_certified_revision_pins_them(
        self, tmp_path
    ):
        payload = folder_layout_manifest_payload()
        for artifact in payload["artifacts"].values():
            del artifact["revision"]

        _, release, _ = certify_uk(empty_bundle(tmp_path), [payload])

        assert {dataset["revision"] for dataset in release["datasets"].values()} == {
            NATIONAL_COMMIT
        }

    def test__given_manifest_read_from_another_build_folder__then_refuses(
        self, tmp_path
    ):
        other_folder = f"releases/{NATIONAL_RELEASE}/{EARLIER_NATIONAL_BUILD}"

        with pytest.raises(CertificationError, match=NATIONAL_BUILD):
            certify_uk(
                empty_bundle(tmp_path),
                [folder_layout_manifest_payload()],
                manifest_uri=manifest_uri(other_folder, NATIONAL_COMMIT),
            )

    def test__given_artifact_outside_its_build_folder__then_refuses(self, tmp_path):
        payload = folder_layout_manifest_payload()
        payload["artifacts"]["microcosm_uk_2024_25"]["path"] = (
            f"releases/{NATIONAL_RELEASE}/{EARLIER_NATIONAL_BUILD}/"
            "microcosm_uk_2024_25.h5"
        )

        with pytest.raises(CertificationError, match="outside"):
            certify_uk(empty_bundle(tmp_path), [payload])

    @pytest.mark.parametrize(
        "artifact_path",
        [
            # Starts with the folder, then leaves it: HTTP clients remove the
            # dot segments, so this would fetch the earlier build's file.
            f"{NATIONAL_FOLDER}/../{EARLIER_NATIONAL_BUILD}/microcosm_uk_2024_25.h5",
            f"{NATIONAL_FOLDER}/nested/microcosm_uk_2024_25.h5",
            f"{NATIONAL_FOLDER}/..",
            "..",
            ".",
            "microcosm_uk_2024_25\\..\\other.h5",
        ],
    )
    def test__given_artifact_path_not_directly_inside_its_folder__then_refuses(
        self, tmp_path, artifact_path
    ):
        # The release writer publishes only bare file names, directly inside
        # the build folder.
        payload = folder_layout_manifest_payload()
        payload["artifacts"]["microcosm_uk_2024_25"]["path"] = artifact_path

        with pytest.raises(CertificationError, match="directly inside"):
            certify_uk(empty_bundle(tmp_path), [payload])

    def test__given_artifact_from_another_repository__then_keeps_its_own_pins(
        self, tmp_path
    ):
        payload = folder_layout_manifest_payload()
        payload["artifacts"]["frs_2024_25"] = {
            "kind": "microdata",
            "path": "frs_2024_25.h5",
            "repo_id": "policyengine/policyengine-uk-data-private",
            "revision": "1.58.0",
            "sha256": "e" * 64,
        }

        _, release, _ = certify_uk(empty_bundle(tmp_path), [payload])

        inherited = release["datasets"]["frs_2024_25"]
        assert (inherited["path"], inherited["revision"]) == (
            "frs_2024_25.h5",
            "1.58.0",
        )

    def test__given_folder_layout_local_area_release__then_areas_use_its_folder(
        self, tmp_path
    ):
        _, release, _ = certify_uk(
            empty_bundle(tmp_path),
            [folder_layout_manifest_payload(), folder_layout_dense_payload()],
            regional_manifest_uri=DENSE_URI,
        )

        dense_path = f"{DENSE_FOLDER}/microcosm_uk_2024_25_dense.h5"
        assert release["regional_release_kind"] == "local_area"
        for region_type in ("constituency", "local_authority"):
            assert release["region_datasets"][region_type] == {
                "path_template": dense_path
            }
        dense = release["datasets"]["microcosm_uk_2024_25_dense"]
        assert (dense["path"], dense["revision"]) == (dense_path, DENSE_COMMIT)

    def test__given_tagged_release__then_paths_and_tag_are_as_before(self, tmp_path):
        tag = f"{NATIONAL_RELEASE}-20261019T083323Z-6cba5d71"

        result, release, _ = certify_uk(
            empty_bundle(tmp_path),
            [tagged_layout_manifest_payload()],
            manifest_uri=manifest_uri(f"releases/{NATIONAL_RELEASE}", tag),
        )

        assert release["datasets"]["microcosm_uk_2024_25"]["path"] == (
            "microcosm_uk_2024_25.h5"
        )
        assert release["datasets"]["microcosm_uk_2024_25"]["revision"] == tag
        assert release["datasets"]["calibration_diagnostics"]["path"] == (
            f"releases/{NATIONAL_RELEASE}/calibration_diagnostics.json"
        )
        assert result.build_id == tag


class TestCertifyOnlyListedBuilds:
    """``releases.json`` at ``main`` is the record of every published build
    and of which ones are withdrawn; certification reads it."""

    def test__given_listed_build__then_reads_releases_record_at_main(self, tmp_path):
        requested_urls: list[str] = []

        certify_uk(
            empty_bundle(tmp_path),
            [folder_layout_manifest_payload()],
            requested_urls=requested_urls,
        )

        assert RELEASES_RECORD_URL in requested_urls

    def test__given_build_withdrawn_in_releases_record__then_refuses(self, tmp_path):
        record = releases_record_payload(
            withdrawn=frozenset({(NATIONAL_RELEASE, NATIONAL_BUILD)})
        )

        with pytest.raises(CertificationError, match="withdrawn"):
            certify_uk(
                empty_bundle(tmp_path),
                [folder_layout_manifest_payload()],
                releases_record=record,
            )

    def test__given_build_not_listed_in_releases_record__then_refuses(self, tmp_path):
        record = releases_record_payload(
            unlisted=frozenset({(NATIONAL_RELEASE, NATIONAL_BUILD)})
        )

        with pytest.raises(CertificationError, match="does not list"):
            certify_uk(
                empty_bundle(tmp_path),
                [folder_layout_manifest_payload()],
                releases_record=record,
            )

    def test__given_withdrawn_local_area_build__then_refuses(self, tmp_path):
        record = releases_record_payload(
            withdrawn=frozenset({(DENSE_RELEASE, DENSE_BUILD)})
        )

        with pytest.raises(CertificationError, match=f"{DENSE_BUILD}.*withdrawn"):
            certify_uk(
                empty_bundle(tmp_path),
                [folder_layout_manifest_payload(), folder_layout_dense_payload()],
                releases_record=record,
                regional_manifest_uri=DENSE_URI,
            )

    def test__given_no_releases_record__then_refuses(self, tmp_path):
        with pytest.raises(CertificationError, match="releases.json"):
            certify_uk(
                empty_bundle(tmp_path),
                [folder_layout_manifest_payload()],
                releases_record={},
            )

    def test__given_tagged_release__then_releases_record_is_not_read(self, tmp_path):
        tag = f"{NATIONAL_RELEASE}-20261019T083323Z-6cba5d71"
        requested_urls: list[str] = []

        certify_uk(
            empty_bundle(tmp_path),
            [tagged_layout_manifest_payload()],
            manifest_uri=manifest_uri(f"releases/{NATIONAL_RELEASE}", tag),
            requested_urls=requested_urls,
        )

        assert RELEASES_RECORD_URL not in requested_urls


PAIR_ID = "a" * 64


def folder_layout_country_manifest(
    certification: dict | None = None,
) -> CountryReleaseManifest:
    """A bundle entry certified from the national build's own folder."""

    return CountryReleaseManifest.model_validate(
        {
            "country_id": "uk",
            "policyengine_version": "9.9.9",
            "model_package": {"name": "policyengine-uk", "version": UK_MODEL_VERSION},
            "data_package": {
                "name": "microcosm-data",
                "version": "0.1.0",
                "repo_id": REPOSITORY,
                "repo_type": "dataset",
                "release_manifest_path": f"{NATIONAL_FOLDER}/release_manifest.json",
                "release_manifest_revision": NATIONAL_COMMIT,
            },
            "default_dataset": "microcosm_uk_2024_25",
            "datasets": {
                "microcosm_uk_2024_25": {
                    "path": f"{NATIONAL_FOLDER}/microcosm_uk_2024_25.h5",
                    "revision": NATIONAL_COMMIT,
                    "repo_id": REPOSITORY,
                }
            },
            **({"certification": certification} if certification else {}),
        }
    )


class TestImportCheckBuildFolder:
    def setup_method(self):
        get_data_release_manifest.cache_clear()

    def teardown_method(self):
        get_data_release_manifest.cache_clear()

    def _patched(self, remote_payload: dict, country_manifest=None):
        return (
            patch(
                "policyengine.provenance.manifest.get_release_manifest",
                return_value=country_manifest or folder_layout_country_manifest(),
            ),
            patch(
                "policyengine.provenance.manifest.requests.get",
                return_value=manifest_response(remote_payload),
            ),
        )

    def test__given_remote_manifest_of_its_folder__then_artifacts_resolve_in_it(
        self,
    ):
        bundle_patch, request_patch = self._patched(folder_layout_manifest_payload())
        with bundle_patch, request_patch as get:
            manifest = get_data_release_manifest("uk")

        assert get.call_args.args[0] == (
            f"https://huggingface.co/datasets/{REPOSITORY}/resolve/"
            f"{NATIONAL_COMMIT}/{NATIONAL_FOLDER}/release_manifest.json"
        )
        assert manifest.artifacts["microcosm_uk_2024_25"].uri == (
            f"hf://{REPOSITORY}/{NATIONAL_FOLDER}/microcosm_uk_2024_25.h5"
            f"@{NATIONAL_COMMIT}"
        )

    def test__given_remote_manifest_naming_another_build__then_refuses(self):
        bundle_patch, request_patch = self._patched(
            folder_layout_manifest_payload(build=EARLIER_NATIONAL_BUILD)
        )
        with (
            bundle_patch,
            request_patch,
            pytest.raises(ReleaseBuildFolderError, match=EARLIER_NATIONAL_BUILD),
        ):
            get_data_release_manifest("uk")

    def test__given_remote_artifact_leaving_its_folder__then_refuses(self):
        remote = folder_layout_manifest_payload()
        remote["artifacts"]["microcosm_uk_2024_25"]["path"] = (
            f"{NATIONAL_FOLDER}/../{EARLIER_NATIONAL_BUILD}/microcosm_uk_2024_25.h5"
        )
        bundle_patch, request_patch = self._patched(remote)
        with (
            bundle_patch,
            request_patch,
            pytest.raises(ReleaseBuildFolderError, match="directly inside"),
        ):
            get_data_release_manifest("uk")

    def test__given_mismatched_remote_manifest__then_bundled_certificate_is_not_used(
        self,
    ):
        # A manifest naming another build is wrong, not unavailable: the
        # fallback to the bundled certificate must not hide it.
        bundled = folder_layout_country_manifest(
            certification={
                "compatibility_basis": "legacy_compatible_model_package",
                "certified_for_model_version": UK_MODEL_VERSION,
                "data_build_id": NATIONAL_BUILD,
            }
        )
        bundle_patch, request_patch = self._patched(
            folder_layout_manifest_payload(build=EARLIER_NATIONAL_BUILD), bundled
        )
        with (
            bundle_patch,
            request_patch,
            pytest.raises(ValueError, match=EARLIER_NATIONAL_BUILD),
        ):
            certify_data_release_compatibility(
                "uk", runtime_model_version=UK_MODEL_VERSION
            )

    def test__given_publisher_claim_on_folder_build__then_build_names_it(self):
        bundle_patch, request_patch = self._patched(folder_layout_manifest_payload())
        with bundle_patch, request_patch:
            certification = certify_data_release_compatibility(
                "uk", runtime_model_version=UK_MODEL_VERSION
            )

        assert certification.compatibility_basis == "legacy_compatible_model_package"
        assert certification.data_build_id == NATIONAL_BUILD

    def test__given_qualified_folder_build__then_import_check_honours_its_build(
        self,
    ):
        qualified = {
            "compatibility_basis": "qualified_exact_pair",
            "certified_for_model_version": "2.130.1",
            "certified_for_core_version": "3.33.0",
            "data_build_id": NATIONAL_BUILD,
            "qualification_pair_id": PAIR_ID,
        }
        remote = folder_layout_manifest_payload()
        remote["compatible_model_packages"] = []
        bundle_patch, request_patch = self._patched(
            remote, folder_layout_country_manifest(certification=qualified)
        )
        with bundle_patch, request_patch:
            certification = certify_data_release_compatibility(
                "uk", runtime_model_version="2.130.1", runtime_core_version="3.33.0"
            )

        assert certification.compatibility_basis == "qualified_exact_pair"
        assert certification.data_build_id == NATIONAL_BUILD
