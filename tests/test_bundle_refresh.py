"""Unit tests for ``policyengine.provenance.bundle.refresh_release_bundle``.

Mocks the PyPI JSON API and the HF ``resolve`` endpoint so the tests
run offline. Exercises:

- Updating only the model version (data-version unchanged).
- Updating only the data version (model unchanged).
- Updating both in one call.
- ``pyproject.toml`` pin rewrite.
- ``--no-pyproject`` / ``update_pyproject=False`` short-circuits.
- Error paths: PyPI has no matching wheel; URI is malformed.

The end-to-end TRO regeneration requires the bundled
release-manifest resolver and a live HF metadata call, so it is
tested separately in ``tests/test_release_manifests.py`` via the
existing script-level hook. This file covers only the pure-refresh
surface.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from policyengine.provenance.bundle import refresh_release_bundle

PYPI_PAYLOAD_TEMPLATE = {
    "urls": [
        {
            "packagetype": "bdist_wheel",
            "filename": "policyengine_us-NEW_VERSION-py3-none-any.whl",
            "url": "https://files.pythonhosted.org/packages/ff/00/policyengine_us-NEW_VERSION-py3-none-any.whl",
            "digests": {"sha256": "a" * 64},
        },
        # Source-dist should be ignored.
        {
            "packagetype": "sdist",
            "filename": "policyengine_us-NEW_VERSION.tar.gz",
            "url": "https://files.pythonhosted.org/packages/ff/00/policyengine_us-NEW_VERSION.tar.gz",
            "digests": {"sha256": "b" * 64},
        },
    ]
}


def _pypi_response(package: str, version: str):
    """Return a mock PyPI ``urlopen`` response."""
    payload = json.loads(
        json.dumps(PYPI_PAYLOAD_TEMPLATE).replace("NEW_VERSION", version)
    )
    # PyPI urls contain the filename; replace the package placeholder too.
    for u in payload["urls"]:
        u["filename"] = u["filename"].replace(
            "policyengine_us", package.replace("-", "_")
        )
        u["url"] = u["url"].replace("policyengine_us", package.replace("-", "_"))
    return io.BytesIO(json.dumps(payload).encode())


class _FakeHFResponse:
    """Streams a deterministic byte sequence so sha256 is predictable."""

    def __init__(self, content: bytes, headers: dict | None = None) -> None:
        self._buffer = io.BytesIO(content)
        self.headers = headers or {}

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._buffer.close()


def _data_release_manifest_response(
    *,
    model_version: str = "1.653.3",
    data_version: str = "1.83.4",
    dataset_sha256: str = "e" * 64,
    extra_artifacts: dict | None = None,
    headers: dict | None = None,
):
    artifacts = {
        "enhanced_cps_2024": {
            "kind": "microdata",
            "path": "enhanced_cps_2024.h5",
            "repo_id": "policyengine/policyengine-us-data",
            "revision": data_version,
            "sha256": dataset_sha256,
        }
    }
    if extra_artifacts:
        artifacts.update(extra_artifacts)
    payload = {
        "schema_version": 1,
        "data_package": {
            "name": "policyengine-us-data",
            "version": data_version,
        },
        "build": {
            "build_id": f"policyengine-us-data-{data_version}",
            "built_with_model_package": {
                "name": "policyengine-us",
                "version": model_version,
                "git_sha": "deadbeef",
                "data_build_fingerprint": "sha256:fingerprint",
            },
        },
        "artifacts": artifacts,
    }
    return _FakeHFResponse(
        json.dumps(payload).encode(),
        headers=(
            {"x-repo-commit": "release-manifest-commit-sha"}
            if headers is None
            else headers
        ),
    )


@pytest.fixture
def sandbox(tmp_path: Path) -> dict:
    """A writable scratch copy of the US release manifest + a stub
    pyproject.toml, returned as ``{manifest_dir, pyproject_path,
    manifest_sha256}``.
    """
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    manifest = {
        "schema_version": 1,
        "bundle_id": "us-4.0.0",
        "country_id": "us",
        "policyengine_version": "4.0.0",
        "model_package": {
            "name": "policyengine-us",
            "version": "1.600.0",
            "sha256": "c" * 64,
            "wheel_url": "https://files.pythonhosted.org/packages/old.whl",
        },
        "data_package": {
            "name": "policyengine-us-data",
            "version": "1.70.0",
            "repo_id": "policyengine/policyengine-us-data",
            "release_manifest_path": "releases/1.70.0/release_manifest.json",
            "release_manifest_revision": "old-release-manifest-commit",
        },
        "certified_data_artifact": {
            "data_package": {
                "name": "policyengine-us-data",
                "version": "1.70.0",
            },
            "build_id": "policyengine-us-data-1.70.0",
            "dataset": "enhanced_cps_2024",
            "uri": "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.70.0",
            "sha256": "d" * 64,
        },
        "certification": {
            "compatibility_basis": "matching_data_build_fingerprint",
            "data_build_id": "policyengine-us-data-1.70.0",
            "built_with_model_version": "1.595.0",
            "certified_for_model_version": "1.600.0",
            "certified_by": "test fixture",
        },
        "default_dataset": "enhanced_cps_2024",
        "datasets": {"enhanced_cps_2024": {"path": "enhanced_cps_2024.h5"}},
        "region_datasets": {"national": {"path_template": "enhanced_cps_2024.h5"}},
    }
    (manifest_dir / "us.json").write_text(json.dumps(manifest, indent=2))

    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "[project]\n"
        'version = "4.2.0"\n'
        "\n"
        "[project.optional-dependencies]\n"
        "us = [\n"
        '    "policyengine_core>=3.25.0",\n'
        '    "policyengine-us==1.600.0",\n'
        "]\n"
    )
    return {
        "manifest_dir": manifest_dir,
        "pyproject_path": pyproject_path,
    }


def test__bump_model_only_rewrites_wheel_pins_and_pyproject(sandbox) -> None:
    """Bumping only the model version pulls fresh wheel metadata,
    keeps the dataset pin intact, and updates pyproject.toml.
    """

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if "pypi.org" in url:
            return _pypi_response("policyengine-us", "1.653.3")
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        result = refresh_release_bundle(
            country="us",
            model_version="1.653.3",
            manifest_dir=sandbox["manifest_dir"],
            pyproject_path=sandbox["pyproject_path"],
        )

    assert result.new_model == "1.653.3"
    assert result.new_data == "1.70.0"  # untouched
    assert result.pyproject_updated
    assert "policyengine-us==1.653.3" in sandbox["pyproject_path"].read_text()

    written = json.loads((sandbox["manifest_dir"] / "us.json").read_text())
    assert written["model_package"]["version"] == "1.653.3"
    assert written["model_package"]["sha256"] == "a" * 64
    assert written["bundle_id"] == "us-4.2.0"
    assert written["policyengine_version"] == "4.2.0"
    # Dataset pins untouched.
    assert written["data_package"]["version"] == "1.70.0"
    assert (
        written["data_package"]["release_manifest_path"]
        == "releases/1.70.0/release_manifest.json"
    )
    assert (
        written["data_package"]["release_manifest_revision"]
        == "old-release-manifest-commit"
    )
    assert written["certified_data_artifact"]["sha256"] == "d" * 64


def test__bump_data_only_streams_hf_and_updates_uri(sandbox) -> None:
    """Bumping only the data version streams the HF file, recomputes
    its sha256, and rewrites the URI revision."""
    manifest_path = sandbox["manifest_dir"] / "us.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["data_package"].pop("release_manifest_path")
    manifest["data_package"].pop("release_manifest_revision")
    manifest_path.write_text(json.dumps(manifest, indent=2))

    hf_bytes = b"synthetic dataset payload"
    expected_sha256 = hashlib.sha256(hf_bytes).hexdigest()

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if "huggingface.co" in url:
            assert "@" not in url  # URI revision is in the URL path
            assert "/datasets/" not in url
            assert "1.83.4" in url
            return _FakeHFResponse(hf_bytes)
        raise AssertionError(f"Unexpected URL: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        result = refresh_release_bundle(
            country="us",
            data_version="1.83.4",
            manifest_dir=sandbox["manifest_dir"],
            pyproject_path=sandbox["pyproject_path"],
        )

    assert result.new_model == "1.600.0"  # untouched
    assert result.new_data == "1.83.4"
    assert result.new_dataset_sha256 == expected_sha256
    assert not result.pyproject_updated  # no model bump => no pyproject change

    written = json.loads((sandbox["manifest_dir"] / "us.json").read_text())
    assert written["data_package"]["version"] == "1.83.4"
    assert "release_manifest_path" not in written["data_package"]
    assert "release_manifest_revision" not in written["data_package"]
    assert written["certified_data_artifact"]["data_package"]["version"] == "1.83.4"
    assert written["certified_data_artifact"]["build_id"] == (
        "policyengine-us-data-1.83.4"
    )
    assert written["certified_data_artifact"]["sha256"] == expected_sha256
    assert (
        written["certified_data_artifact"]["uri"]
        == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.83.4"
    )


def test__bump_data_only_writes_release_manifest_revision_when_absent(
    sandbox,
) -> None:
    manifest_path = sandbox["manifest_dir"] / "us.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["data_package"].pop("release_manifest_revision")
    manifest_path.write_text(json.dumps(manifest, indent=2))

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if url.endswith("releases/1.83.4/release_manifest.json"):
            return _data_release_manifest_response()
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        refresh_release_bundle(
            country="us",
            data_version="1.83.4",
            manifest_dir=sandbox["manifest_dir"],
            pyproject_path=sandbox["pyproject_path"],
        )

    written = json.loads((sandbox["manifest_dir"] / "us.json").read_text())
    assert (
        written["data_package"]["release_manifest_revision"]
        == "release-manifest-commit-sha"
    )
    assert (
        written["certified_data_artifact"]["uri"]
        == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@release-manifest-commit-sha"
    )


def test__bump_data_only_falls_back_to_main_for_release_manifest(
    sandbox,
) -> None:
    seen_urls = []

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        seen_urls.append(url)
        if "/resolve/1.83.4/releases/1.83.4/release_manifest.json" in url:
            raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)
        if "/resolve/main/releases/1.83.4/release_manifest.json" in url:
            return _data_release_manifest_response()
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        refresh_release_bundle(
            country="us",
            data_version="1.83.4",
            manifest_dir=sandbox["manifest_dir"],
            pyproject_path=sandbox["pyproject_path"],
        )

    assert any("/resolve/1.83.4/" in url for url in seen_urls)
    assert any("/resolve/main/" in url for url in seen_urls)
    written = json.loads((sandbox["manifest_dir"] / "us.json").read_text())
    assert (
        written["data_package"]["release_manifest_revision"]
        == "release-manifest-commit-sha"
    )
    assert (
        written["certified_data_artifact"]["uri"]
        == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@release-manifest-commit-sha"
    )


def test__release_manifest_version_mismatch_raises(sandbox) -> None:
    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if url.endswith("releases/1.83.4/release_manifest.json"):
            return _data_release_manifest_response(data_version="1.83.3")
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        with pytest.raises(
            ValueError,
            match="declares version '1.83.3', expected '1.83.4'",
        ):
            refresh_release_bundle(
                country="us",
                data_version="1.83.4",
                manifest_dir=sandbox["manifest_dir"],
                pyproject_path=sandbox["pyproject_path"],
            )


def test__bump_both_updates_everything(sandbox) -> None:
    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if "pypi.org" in url:
            return _pypi_response("policyengine-us", "1.653.3")
        if url.endswith("releases/1.83.4/release_manifest.json"):
            return _data_release_manifest_response()
        raise AssertionError(url)

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        result = refresh_release_bundle(
            country="us",
            model_version="1.653.3",
            data_version="1.83.4",
            manifest_dir=sandbox["manifest_dir"],
            pyproject_path=sandbox["pyproject_path"],
        )

    assert result.pyproject_updated
    assert result.new_model == "1.653.3"
    assert result.new_data == "1.83.4"


def test__bump_both_uses_data_release_manifest_metadata(sandbox) -> None:
    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if "pypi.org" in url:
            return _pypi_response("policyengine-us", "1.653.3")
        if url.endswith("releases/1.83.4/release_manifest.json"):
            return _data_release_manifest_response()
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        result = refresh_release_bundle(
            country="us",
            model_version="1.653.3",
            data_version="1.83.4",
            manifest_dir=sandbox["manifest_dir"],
            pyproject_path=sandbox["pyproject_path"],
        )

    assert result.new_dataset_sha256 == "e" * 64

    written = json.loads((sandbox["manifest_dir"] / "us.json").read_text())
    assert written["certified_data_artifact"]["build_id"] == (
        "policyengine-us-data-1.83.4"
    )
    assert written["certified_data_artifact"]["sha256"] == "e" * 64
    assert written["certification"]["compatibility_basis"] == (
        "exact_build_model_version"
    )
    assert written["certification"]["built_with_model_version"] == "1.653.3"
    assert written["certification"]["built_with_model_git_sha"] == "deadbeef"
    assert written["certification"]["data_build_fingerprint"] == ("sha256:fingerprint")
    assert (
        written["data_package"]["release_manifest_revision"]
        == "release-manifest-commit-sha"
    )


def test__custom_release_manifest_refreshes_long_term_dataset_hashes(
    sandbox,
) -> None:
    manifest_path = sandbox["manifest_dir"] / "us.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["data_package"]["release_manifest_path"] = (
        "releases/crfb-longrun-old/release_manifest.json"
    )
    manifest["data_package"]["release_manifest_revision"] = "crfb-longrun-old"
    manifest["datasets"]["long_term_cps_2100"] = {
        "path": "long_term/2100.h5",
        "sha256": "1" * 64,
        "metadata_sha256": "2" * 64,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if (
            "/resolve/crfb-longrun-new/releases/crfb-longrun-new/release_manifest.json"
            in url
        ):
            return _data_release_manifest_response(
                data_version="1.83.4",
                extra_artifacts={
                    "long_term/2100": {
                        "kind": "microdata",
                        "path": "long_term/2100.h5",
                        "repo_id": "policyengine/policyengine-us-data",
                        "revision": "1.83.4",
                        "sha256": "3" * 64,
                    },
                    "long_term/2100.h5.metadata": {
                        "kind": "auxiliary",
                        "path": "long_term/2100.h5.metadata.json",
                        "repo_id": "policyengine/policyengine-us-data",
                        "revision": "1.83.4",
                        "sha256": "4" * 64,
                    },
                },
            )
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        refresh_release_bundle(
            country="us",
            data_version="1.83.4",
            release_manifest_path="releases/crfb-longrun-new/release_manifest.json",
            release_manifest_revision="crfb-longrun-new",
            manifest_dir=sandbox["manifest_dir"],
            pyproject_path=sandbox["pyproject_path"],
        )

    written = json.loads((sandbox["manifest_dir"] / "us.json").read_text())
    assert (
        written["data_package"]["release_manifest_path"]
        == "releases/crfb-longrun-new/release_manifest.json"
    )
    assert (
        written["data_package"]["release_manifest_revision"]
        == "release-manifest-commit-sha"
    )
    assert written["datasets"]["long_term_cps_2100"]["sha256"] == "3" * 64
    assert written["datasets"]["long_term_cps_2100"]["metadata_sha256"] == "4" * 64
    assert (
        written["certified_data_artifact"]["uri"]
        == "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@release-manifest-commit-sha"
    )


def test__custom_release_manifest_requires_existing_long_term_metadata_sidecar(
    sandbox,
) -> None:
    manifest_path = sandbox["manifest_dir"] / "us.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["data_package"]["release_manifest_path"] = (
        "releases/crfb-longrun-old/release_manifest.json"
    )
    manifest["data_package"]["release_manifest_revision"] = "crfb-longrun-old"
    manifest["datasets"]["long_term_cps_2100"] = {
        "path": "long_term/2100.h5",
        "sha256": "1" * 64,
        "metadata_sha256": "2" * 64,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if (
            "/resolve/crfb-longrun-new/releases/crfb-longrun-new/release_manifest.json"
            in url
        ):
            return _data_release_manifest_response(
                data_version="1.83.4",
                extra_artifacts={
                    "long_term/2100": {
                        "kind": "microdata",
                        "path": "long_term/2100.h5",
                        "repo_id": "policyengine/policyengine-us-data",
                        "revision": "1.83.4",
                        "sha256": "3" * 64,
                    },
                },
            )
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        with pytest.raises(
            ValueError,
            match="missing metadata sidecar artifact",
        ):
            refresh_release_bundle(
                country="us",
                data_version="1.83.4",
                release_manifest_path="releases/crfb-longrun-new/release_manifest.json",
                release_manifest_revision="crfb-longrun-new",
                manifest_dir=sandbox["manifest_dir"],
                pyproject_path=sandbox["pyproject_path"],
            )


def test__custom_release_manifest_requires_existing_long_term_dataset_artifact(
    sandbox,
) -> None:
    manifest_path = sandbox["manifest_dir"] / "us.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["data_package"]["release_manifest_path"] = (
        "releases/crfb-longrun-old/release_manifest.json"
    )
    manifest["data_package"]["release_manifest_revision"] = "crfb-longrun-old"
    manifest["datasets"]["long_term_cps_2100"] = {
        "path": "long_term/2100.h5",
        "sha256": "1" * 64,
        "metadata_sha256": "2" * 64,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if (
            "/resolve/crfb-longrun-new/releases/crfb-longrun-new/release_manifest.json"
            in url
        ):
            return _data_release_manifest_response(data_version="1.83.4")
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        with pytest.raises(
            ValueError,
            match="missing dataset artifact",
        ):
            refresh_release_bundle(
                country="us",
                data_version="1.83.4",
                release_manifest_path="releases/crfb-longrun-new/release_manifest.json",
                release_manifest_revision="crfb-longrun-new",
                manifest_dir=sandbox["manifest_dir"],
                pyproject_path=sandbox["pyproject_path"],
            )


def test__custom_release_manifest_requires_existing_long_term_dataset_sha(
    sandbox,
) -> None:
    manifest_path = sandbox["manifest_dir"] / "us.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["data_package"]["release_manifest_path"] = (
        "releases/crfb-longrun-old/release_manifest.json"
    )
    manifest["data_package"]["release_manifest_revision"] = "crfb-longrun-old"
    manifest["datasets"]["long_term_cps_2100"] = {
        "path": "long_term/2100.h5",
        "sha256": "1" * 64,
        "metadata_sha256": "2" * 64,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if (
            "/resolve/crfb-longrun-new/releases/crfb-longrun-new/release_manifest.json"
            in url
        ):
            return _data_release_manifest_response(
                data_version="1.83.4",
                extra_artifacts={
                    "long_term/2100": {
                        "kind": "microdata",
                        "path": "long_term/2100.h5",
                        "repo_id": "policyengine/policyengine-us-data",
                        "revision": "1.83.4",
                    },
                    "long_term/2100.h5.metadata": {
                        "kind": "auxiliary",
                        "path": "long_term/2100.h5.metadata.json",
                        "repo_id": "policyengine/policyengine-us-data",
                        "revision": "1.83.4",
                        "sha256": "4" * 64,
                    },
                },
            )
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        with pytest.raises(
            ValueError,
            match="dataset artifact lacks sha256",
        ):
            refresh_release_bundle(
                country="us",
                data_version="1.83.4",
                release_manifest_path="releases/crfb-longrun-new/release_manifest.json",
                release_manifest_revision="crfb-longrun-new",
                manifest_dir=sandbox["manifest_dir"],
                pyproject_path=sandbox["pyproject_path"],
            )


def test__explicit_release_manifest_revision_does_not_fallback_to_main(
    sandbox,
) -> None:
    seen_urls = []

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        seen_urls.append(url)
        if (
            "/resolve/bad-crfb-ref/releases/crfb-longrun-new/release_manifest.json"
            in url
        ):
            raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)
        if "/resolve/main/releases/crfb-longrun-new/release_manifest.json" in url:
            return _data_release_manifest_response(data_version="1.83.4")
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        with pytest.raises(
            ValueError,
            match="Could not fetch data release manifest",
        ):
            refresh_release_bundle(
                country="us",
                data_version="1.83.4",
                release_manifest_path="releases/crfb-longrun-new/release_manifest.json",
                release_manifest_revision="bad-crfb-ref",
                manifest_dir=sandbox["manifest_dir"],
                pyproject_path=sandbox["pyproject_path"],
            )

    assert any("/resolve/bad-crfb-ref/" in url for url in seen_urls)
    assert not any("/resolve/main/" in url for url in seen_urls)


def test__missing_release_manifest_metadata_raises(sandbox) -> None:
    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if url.endswith("releases/1.83.4/release_manifest.json"):
            return _FakeHFResponse(b"not json")
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        with pytest.raises(
            ValueError,
            match="Could not fetch data release manifest",
        ):
            refresh_release_bundle(
                country="us",
                data_version="1.83.4",
                manifest_dir=sandbox["manifest_dir"],
                pyproject_path=sandbox["pyproject_path"],
            )


def test__missing_release_manifest_commit_raises(sandbox) -> None:
    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if url.endswith("releases/1.83.4/release_manifest.json"):
            return _data_release_manifest_response(headers={})
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        with pytest.raises(
            ValueError,
            match="Could not resolve an immutable HF commit",
        ):
            refresh_release_bundle(
                country="us",
                data_version="1.83.4",
                manifest_dir=sandbox["manifest_dir"],
                pyproject_path=sandbox["pyproject_path"],
            )


def test__release_manifest_missing_certified_artifact_raises(sandbox) -> None:
    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if url.endswith("releases/1.83.4/release_manifest.json"):
            payload = {
                "schema_version": 1,
                "data_package": {
                    "name": "policyengine-us-data",
                    "version": "1.83.4",
                },
                "artifacts": {
                    "other_dataset": {
                        "kind": "microdata",
                        "path": "other_dataset.h5",
                        "repo_id": "policyengine/policyengine-us-data",
                        "revision": "1.83.4",
                        "sha256": "e" * 64,
                    }
                },
            }
            return _FakeHFResponse(
                json.dumps(payload).encode(),
                headers={"x-repo-commit": "release-manifest-commit-sha"},
            )
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        with pytest.raises(
            ValueError,
            match="does not include certified dataset",
        ):
            refresh_release_bundle(
                country="us",
                data_version="1.83.4",
                manifest_dir=sandbox["manifest_dir"],
                pyproject_path=sandbox["pyproject_path"],
            )


def test__update_pyproject_false_leaves_pins_alone(sandbox) -> None:
    def fake_urlopen(*args, **kwargs):
        return _pypi_response("policyengine-us", "1.653.3")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        result = refresh_release_bundle(
            country="us",
            model_version="1.653.3",
            update_pyproject=False,
            manifest_dir=sandbox["manifest_dir"],
            pyproject_path=sandbox["pyproject_path"],
        )

    assert not result.pyproject_updated
    assert "policyengine-us==1.600.0" in sandbox["pyproject_path"].read_text()


def test__invalid_pyproject_version_fails_before_manifest_write(
    sandbox, tmp_path
) -> None:
    invalid_pyproject = tmp_path / "invalid-pyproject.toml"
    invalid_pyproject.write_text('[project]\nname = "policyengine"\n')
    manifest_path = sandbox["manifest_dir"] / "us.json"
    original = manifest_path.read_text()

    with pytest.raises(ValueError, match="Could not find project version"):
        refresh_release_bundle(
            country="us",
            manifest_dir=sandbox["manifest_dir"],
            pyproject_path=invalid_pyproject,
        )

    assert manifest_path.read_text() == original


def test__no_matching_wheel_on_pypi_raises(sandbox) -> None:
    def fake_urlopen(*args, **kwargs):
        return io.BytesIO(json.dumps({"urls": []}).encode())

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        with pytest.raises(ValueError, match="No py3-none-any wheel"):
            refresh_release_bundle(
                country="us",
                model_version="1.999.0",
                manifest_dir=sandbox["manifest_dir"],
                pyproject_path=sandbox["pyproject_path"],
            )


def test__malformed_uri_raises(tmp_path) -> None:
    """If the current manifest's URI doesn't match the expected
    ``hf://.../path@revision`` shape, we refuse to guess."""
    manifest_dir = tmp_path / "m"
    manifest_dir.mkdir()
    bad = {
        "schema_version": 1,
        "bundle_id": "us-4.0.0",
        "country_id": "us",
        "policyengine_version": "4.0.0",
        "model_package": {
            "name": "policyengine-us",
            "version": "1.600.0",
            "sha256": "c" * 64,
            "wheel_url": "https://…old.whl",
        },
        "data_package": {
            "name": "policyengine-us-data",
            "version": "1.70.0",
            "repo_id": "policyengine/policyengine-us-data",
        },
        "certified_data_artifact": {
            "data_package": {
                "name": "policyengine-us-data",
                "version": "1.70.0",
            },
            "build_id": "policyengine-us-data-1.70.0",
            "dataset": "enhanced_cps_2024",
            # Malformed: no @revision.
            "uri": "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5",
            "sha256": "d" * 64,
        },
        "certification": {
            "compatibility_basis": "matching_data_build_fingerprint",
            "data_build_id": "policyengine-us-data-1.70.0",
            "built_with_model_version": "1.595.0",
            "certified_for_model_version": "1.600.0",
            "certified_by": "test fixture",
        },
        "default_dataset": "enhanced_cps_2024",
        "datasets": {"enhanced_cps_2024": {"path": "enhanced_cps_2024.h5"}},
        "region_datasets": {},
    }
    (manifest_dir / "us.json").write_text(json.dumps(bad))

    with pytest.raises(ValueError, match="Cannot parse current dataset URI"):
        refresh_release_bundle(
            country="us",
            data_version="1.83.4",
            manifest_dir=manifest_dir,
            pyproject_path=tmp_path / "pyproject.toml",
        )
