"""Tests for agent-safe release-bundle update orchestration."""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Bundle tooling tests do not need the runtime country models.
os.environ.setdefault("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")

from policyengine import cli
from policyengine.provenance import bundle_update
from policyengine.provenance.bundle import RefreshResult


def _wheel_bytes(package_root: str, files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as wheel:
        wheel.writestr(
            f"{package_root}/build_metadata.py",
            "DATA_BUILD_SURFACE = ('entities.py', 'parameters', 'system.py')\n",
        )
        for path, content in files.items():
            wheel.writestr(f"{package_root}/{path}", content)
    return buffer.getvalue()


def _expected_fingerprint(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(files):
        if "__pycache__" in relative_path.split("/") or relative_path.endswith(
            (".pyc", ".pyo")
        ):
            continue
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(files[relative_path])
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _release_manifest_response(
    *,
    package: str,
    model_version: str,
    data_package: str,
    data_version: str,
    dataset: str,
    repo_id: str,
    sha256: str = "e" * 64,
    fingerprint: str = "sha256:target",
):
    payload = {
        "schema_version": 1,
        "data_package": {"name": data_package, "version": data_version},
        "build": {
            "build_id": f"{data_package}-{data_version}",
            "built_with_model_package": {
                "name": package,
                "version": model_version,
                "git_sha": "deadbeef",
                "data_build_fingerprint": fingerprint,
            },
        },
        "artifacts": {
            dataset: {
                "kind": "microdata",
                "path": f"{dataset}.h5",
                "repo_id": repo_id,
                "revision": data_version,
                "sha256": sha256,
            }
        },
    }
    return SimpleNamespace(payload=payload, repo_commit=f"{data_version}-commit")


def _pypi_response(package: str, version: str):
    package_file = package.replace("-", "_")
    payload = {
        "urls": [
            {
                "packagetype": "bdist_wheel",
                "filename": f"{package_file}-{version}-py3-none-any.whl",
                "url": (
                    "https://files.pythonhosted.org/packages/ff/00/"
                    f"{package_file}-{version}-py3-none-any.whl"
                ),
                "digests": {"sha256": "f" * 64},
            }
        ]
    }
    return io.BytesIO(json.dumps(payload).encode())


def _manifest(
    *,
    country: str,
    model_package: str,
    model_version: str,
    data_package: str,
    data_version: str,
    repo_id: str,
    dataset: str,
    fingerprint: str = "sha256:current",
):
    return {
        "schema_version": 1,
        "bundle_id": f"{country}-4.2.0",
        "country_id": country,
        "policyengine_version": "4.2.0",
        "model_package": {
            "name": model_package,
            "version": model_version,
            "sha256": "a" * 64,
            "wheel_url": "https://files.pythonhosted.org/packages/old.whl",
        },
        "data_package": {
            "name": data_package,
            "version": data_version,
            "repo_id": repo_id,
            "release_manifest_path": "release_manifest.json",
            "release_manifest_revision": f"{data_version}-old-commit",
        },
        "certified_data_artifact": {
            "data_package": {"name": data_package, "version": data_version},
            "build_id": f"{data_package}-{data_version}",
            "dataset": dataset,
            "uri": f"hf://{repo_id}/{dataset}.h5@{data_version}-old-commit",
            "sha256": "d" * 64,
        },
        "certification": {
            "compatibility_basis": "exact_build_model_version",
            "data_build_id": f"{data_package}-{data_version}",
            "built_with_model_version": model_version,
            "certified_for_model_version": model_version,
            "certified_by": f"{data_package} release manifest",
            "data_build_fingerprint": fingerprint,
        },
        "default_dataset": dataset,
        "datasets": {dataset: {"path": f"{dataset}.h5", "sha256": "d" * 64}},
        "region_datasets": {"national": {"path_template": f"{dataset}.h5"}},
    }


@pytest.fixture
def bundle_sandbox(tmp_path: Path) -> dict[str, Path]:
    manifest_dir = tmp_path / "release_manifests"
    manifest_dir.mkdir()
    (manifest_dir / "us.json").write_text(
        json.dumps(
            _manifest(
                country="us",
                model_package="policyengine-us",
                model_version="1.700.0",
                data_package="policyengine-us-data",
                data_version="1.115.5",
                repo_id="policyengine/policyengine-us-data",
                dataset="enhanced_cps_2024",
            ),
            indent=2,
        )
    )
    (manifest_dir / "uk.json").write_text(
        json.dumps(
            _manifest(
                country="uk",
                model_package="policyengine-uk",
                model_version="2.88.20",
                data_package="policyengine-uk-data",
                data_version="1.55.10",
                repo_id="policyengine/policyengine-uk-data-private",
                dataset="enhanced_frs_2023_24",
            ),
            indent=2,
        )
    )
    (manifest_dir / "us.trace.tro.jsonld").write_text("{}")
    (manifest_dir / "uk.trace.tro.jsonld").write_text("{}")

    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "[project]\n"
        'version = "4.2.0"\n'
        "[project.optional-dependencies]\n"
        'us = ["policyengine-us==1.700.0"]\n'
        'uk = ["policyengine-uk==2.88.20"]\n'
    )
    return {"manifest_dir": manifest_dir, "pyproject_path": pyproject_path}


def _patch_resolution(monkeypatch, *, fetch):
    latest = {"policyengine-us": "1.715.2", "policyengine-uk": "2.89.0"}
    fingerprints = {
        ("policyengine-us", "1.715.2"): "sha256:target-us",
        ("policyengine-uk", "2.89.0"): "sha256:target-uk",
    }
    monkeypatch.setattr(
        bundle_update,
        "_latest_pypi_version",
        lambda package: latest[package],
    )
    monkeypatch.setattr(
        bundle_update,
        "_target_model_fingerprint",
        lambda package, version: fingerprints[(package, version)],
    )
    monkeypatch.setattr(bundle_update, "_fetch_data_release_manifest", fetch)


def _fake_refresh(
    *,
    country,
    model_version,
    data_version,
    release_manifest_path,
    release_manifest_revision,
    prevalidated_certification=None,
    manifest_dir,
    pyproject_path,
):
    manifest_path = manifest_dir / f"{country}.json"
    manifest = json.loads(manifest_path.read_text())
    old_model = manifest["model_package"]["version"]
    old_data = manifest["data_package"]["version"]
    manifest["model_package"]["version"] = model_version
    manifest["data_package"]["version"] = data_version
    manifest["data_package"]["release_manifest_path"] = release_manifest_path
    manifest["data_package"]["release_manifest_revision"] = release_manifest_revision
    manifest_path.write_text(json.dumps(manifest, indent=2))
    pyproject_path.write_text(pyproject_path.read_text() + f"\n# refreshed {country}")
    return RefreshResult(
        country=country,
        old_model=old_model,
        new_model=model_version,
        old_data=old_data,
        new_data=data_version,
        old_wheel_sha256="a" * 64,
        new_wheel_sha256="b" * 64,
        old_dataset_sha256="c" * 64,
        new_dataset_sha256="d" * 64,
        manifest_path=manifest_path,
        pyproject_updated=True,
    )


def test__us_latest_refresh_updates_only_us_manifest_and_tro(
    bundle_sandbox, monkeypatch
) -> None:
    def fetch(repo_id, release_manifest_path, revision, allow_main_fallback=True):
        assert repo_id == "policyengine/policyengine-us-data"
        return _release_manifest_response(
            package="policyengine-us",
            model_version="1.715.2",
            data_package="policyengine-us-data",
            data_version="1.116.0",
            dataset="enhanced_cps_2024",
            repo_id=repo_id,
            fingerprint="sha256:target-us",
        )

    _patch_resolution(monkeypatch, fetch=fetch)
    monkeypatch.setattr(bundle_update, "refresh_release_bundle", _fake_refresh)
    monkeypatch.setattr(
        bundle_update,
        "regenerate_trace_tro",
        lambda country, manifest_dir: manifest_dir / f"{country}.trace.tro.jsonld",
    )

    outcome = bundle_update.refresh_release_bundles(
        country="us",
        manifest_dir=bundle_sandbox["manifest_dir"],
        pyproject_path=bundle_sandbox["pyproject_path"],
    )

    assert [plan.country for plan in outcome.plans] == ["us"]
    us_manifest = json.loads((bundle_sandbox["manifest_dir"] / "us.json").read_text())
    uk_manifest = json.loads((bundle_sandbox["manifest_dir"] / "uk.json").read_text())
    assert us_manifest["model_package"]["version"] == "1.715.2"
    assert us_manifest["data_package"]["version"] == "1.116.0"
    assert uk_manifest["model_package"]["version"] == "2.88.20"
    assert outcome.tro_paths == [bundle_sandbox["manifest_dir"] / "us.trace.tro.jsonld"]


def test__uk_explicit_version_uses_private_release_manifest_metadata(
    bundle_sandbox, monkeypatch
) -> None:
    def fetch(repo_id, release_manifest_path, revision, allow_main_fallback=True):
        assert repo_id == "policyengine/policyengine-uk-data-private"
        assert revision == "main"
        return _release_manifest_response(
            package="policyengine-uk",
            model_version="2.89.0",
            data_package="policyengine-uk-data",
            data_version="1.56.0",
            dataset="enhanced_frs_2023_24",
            repo_id=repo_id,
            fingerprint="sha256:target-uk",
        )

    _patch_resolution(monkeypatch, fetch=fetch)

    plans = bundle_update.plan_release_bundle_updates(
        country="uk",
        model_version="2.89.0",
        manifest_dir=bundle_sandbox["manifest_dir"],
        pyproject_path=bundle_sandbox["pyproject_path"],
    )

    assert len(plans) == 1
    assert plans[0].target_data_version == "1.56.0"
    assert plans[0].release_manifest_revision == "1.56.0-commit"
    assert plans[0].compatibility_basis == "exact_build_model_version"


def test__all_mode_preflights_every_country_before_writing(
    bundle_sandbox, monkeypatch
) -> None:
    def fetch(repo_id, release_manifest_path, revision, allow_main_fallback=True):
        if repo_id.endswith("policyengine-us-data"):
            return _release_manifest_response(
                package="policyengine-us",
                model_version="1.700.0",
                data_package="policyengine-us-data",
                data_version="1.116.0",
                dataset="enhanced_cps_2024",
                repo_id=repo_id,
                fingerprint="sha256:other",
            )
        return _release_manifest_response(
            package="policyengine-uk",
            model_version="2.89.0",
            data_package="policyengine-uk-data",
            data_version="1.56.0",
            dataset="enhanced_frs_2023_24",
            repo_id=repo_id,
            fingerprint="sha256:target-uk",
        )

    _patch_resolution(monkeypatch, fetch=fetch)
    called = False

    def fail_if_called(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("mutation should not run")

    monkeypatch.setattr(bundle_update, "refresh_release_bundle", fail_if_called)

    with pytest.raises(ValueError, match="publish a new country data release"):
        bundle_update.refresh_release_bundles(
            country="all",
            manifest_dir=bundle_sandbox["manifest_dir"],
            pyproject_path=bundle_sandbox["pyproject_path"],
        )

    assert not called


def test__all_mode_rejects_common_explicit_target_flags(
    bundle_sandbox, monkeypatch
) -> None:
    def fetch(repo_id, release_manifest_path, revision, allow_main_fallback=True):
        raise AssertionError("preflight should fail before fetching manifests")

    _patch_resolution(monkeypatch, fetch=fetch)

    with pytest.raises(ValueError, match="--country all cannot use common"):
        bundle_update.plan_release_bundle_updates(
            country="all",
            model_version="1.715.2",
            manifest_dir=bundle_sandbox["manifest_dir"],
            pyproject_path=bundle_sandbox["pyproject_path"],
        )


def test__all_mode_restores_partial_write_on_apply_failure(
    bundle_sandbox, monkeypatch
) -> None:
    def fetch(repo_id, release_manifest_path, revision, allow_main_fallback=True):
        if repo_id.endswith("policyengine-us-data"):
            return _release_manifest_response(
                package="policyengine-us",
                model_version="1.715.2",
                data_package="policyengine-us-data",
                data_version="1.116.0",
                dataset="enhanced_cps_2024",
                repo_id=repo_id,
                fingerprint="sha256:target-us",
            )
        return _release_manifest_response(
            package="policyengine-uk",
            model_version="2.89.0",
            data_package="policyengine-uk-data",
            data_version="1.56.0",
            dataset="enhanced_frs_2023_24",
            repo_id=repo_id,
            fingerprint="sha256:target-uk",
        )

    _patch_resolution(monkeypatch, fetch=fetch)
    original_pyproject = bundle_sandbox["pyproject_path"].read_text()

    def refresh_then_fail(**kwargs):
        if kwargs["country"] == "uk":
            raise RuntimeError("boom")
        return _fake_refresh(**kwargs)

    monkeypatch.setattr(bundle_update, "refresh_release_bundle", refresh_then_fail)
    monkeypatch.setattr(
        bundle_update,
        "regenerate_trace_tro",
        lambda country, manifest_dir: manifest_dir / f"{country}.trace.tro.jsonld",
    )

    with pytest.raises(RuntimeError, match="boom"):
        bundle_update.refresh_release_bundles(
            country="all",
            manifest_dir=bundle_sandbox["manifest_dir"],
            pyproject_path=bundle_sandbox["pyproject_path"],
        )

    assert bundle_sandbox["pyproject_path"].read_text() == original_pyproject
    us_manifest = json.loads((bundle_sandbox["manifest_dir"] / "us.json").read_text())
    assert us_manifest["model_package"]["version"] == "1.700.0"


def test__wheel_data_build_fingerprint_hashes_declared_surface(monkeypatch) -> None:
    files = {
        "entities.py": b"entities",
        "parameters/a.yaml": b"a",
        "parameters/nested/b.yaml": b"b",
        "parameters/__pycache__/ignored.pyc": b"ignored",
        "parameters/ignored.pyo": b"ignored",
        "system.py": b"system",
        "variables/not-in-surface.py": b"ignored",
    }
    wheel_bytes = _wheel_bytes("policyengine_us", files)
    monkeypatch.setattr(bundle_update, "_download_bytes", lambda url: wheel_bytes)

    fingerprint = bundle_update._wheel_data_build_fingerprint(
        "policyengine-us",
        "https://example.invalid/policyengine_us.whl",
    )

    included = {
        "entities.py": files["entities.py"],
        "parameters/a.yaml": files["parameters/a.yaml"],
        "parameters/nested/b.yaml": files["parameters/nested/b.yaml"],
        "system.py": files["system.py"],
    }
    assert fingerprint == _expected_fingerprint(included)


def test__current_data_fingerprint_match_allows_model_only_update(
    bundle_sandbox, monkeypatch
) -> None:
    def fetch(repo_id, release_manifest_path, revision, allow_main_fallback=True):
        return None

    _patch_resolution(monkeypatch, fetch=fetch)
    monkeypatch.setattr(
        bundle_update,
        "_target_model_fingerprint",
        lambda package, version: "sha256:current",
    )

    plans = bundle_update.plan_release_bundle_updates(
        country="us",
        model_version="1.715.2",
        manifest_dir=bundle_sandbox["manifest_dir"],
        pyproject_path=bundle_sandbox["pyproject_path"],
    )

    assert plans[0].target_data_version == "1.115.5"
    assert plans[0].compatibility_basis == "matching_data_build_fingerprint"
    assert plans[0].data_source == "current_bundle_certification"


def test__current_bundle_certification_fallback_writes_model_only_update(
    bundle_sandbox, monkeypatch
) -> None:
    def fetch(repo_id, release_manifest_path, revision, allow_main_fallback=True):
        return None

    _patch_resolution(monkeypatch, fetch=fetch)
    monkeypatch.setattr(
        bundle_update,
        "_target_model_fingerprint",
        lambda package, version: "sha256:current",
    )

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url
        if "pypi.org" in url:
            assert "policyengine-us/1.715.2" in url
            return _pypi_response("policyengine-us", "1.715.2")
        raise AssertionError(f"Unexpected URL fetched: {url}")

    with patch("policyengine.provenance.bundle.urlopen", side_effect=fake_urlopen):
        outcome = bundle_update.refresh_release_bundles(
            country="us",
            model_version="1.715.2",
            manifest_dir=bundle_sandbox["manifest_dir"],
            pyproject_path=bundle_sandbox["pyproject_path"],
            regenerate_tros=False,
        )

    assert outcome.plans[0].data_source == "current_bundle_certification"
    assert not outcome.tro_paths
    written = json.loads((bundle_sandbox["manifest_dir"] / "us.json").read_text())
    assert written["model_package"]["version"] == "1.715.2"
    assert written["model_package"]["sha256"] == "f" * 64
    assert written["data_package"]["version"] == "1.115.5"
    assert written["data_package"]["release_manifest_revision"] == "1.115.5-old-commit"
    assert written["certified_data_artifact"]["sha256"] == "d" * 64
    assert (
        written["certification"]["compatibility_basis"]
        == "matching_data_build_fingerprint"
    )
    assert written["certification"]["certified_for_model_version"] == "1.715.2"
    assert written["certification"]["data_build_fingerprint"] == "sha256:current"
    assert "policyengine-us==1.715.2" in bundle_sandbox["pyproject_path"].read_text()


def test__incompatible_model_data_fails_before_mutation(
    bundle_sandbox, monkeypatch
) -> None:
    def fetch(repo_id, release_manifest_path, revision, allow_main_fallback=True):
        return _release_manifest_response(
            package="policyengine-us",
            model_version="1.700.0",
            data_package="policyengine-us-data",
            data_version="1.116.0",
            dataset="enhanced_cps_2024",
            repo_id=repo_id,
            fingerprint="sha256:not-target",
        )

    _patch_resolution(monkeypatch, fetch=fetch)
    monkeypatch.setattr(
        bundle_update,
        "refresh_release_bundle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("mutated")),
    )

    with pytest.raises(ValueError, match="does not certify"):
        bundle_update.refresh_release_bundles(
            country="us",
            model_version="1.715.2",
            manifest_dir=bundle_sandbox["manifest_dir"],
            pyproject_path=bundle_sandbox["pyproject_path"],
        )


def test__source_checkout_guard_fails_when_repo_files_are_missing(tmp_path) -> None:
    with pytest.raises(ValueError, match="source checkout"):
        bundle_update.plan_release_bundle_updates(
            country="us",
            manifest_dir=tmp_path / "missing-manifests",
            pyproject_path=tmp_path / "missing-pyproject.toml",
        )


def test__policyengine_cli_dispatches_refresh_release_bundles(capsys) -> None:
    outcome = SimpleNamespace(summary=lambda: "ok")
    with patch(
        "policyengine.provenance.bundle_update.refresh_release_bundles",
        return_value=outcome,
    ) as refresh:
        exit_code = cli.main(
            [
                "refresh-release-bundles",
                "--country",
                "all",
                "--us-model-version",
                "1.715.2",
                "--uk-model-version",
                "2.89.0",
            ]
        )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "ok"
    assert refresh.call_args.kwargs["country"] == "all"
    assert refresh.call_args.kwargs["us_model_version"] == "1.715.2"
    assert refresh.call_args.kwargs["uk_model_version"] == "2.89.0"


def test__script_parser_returns_nonzero_on_preflight_failure(capsys) -> None:
    with patch(
        "policyengine.provenance.bundle_update.refresh_release_bundles",
        side_effect=ValueError("not certified"),
    ):
        exit_code = bundle_update.main(["--country", "us", "--model-version", "1.2.3"])

    assert exit_code == 1
    assert "not certified" in capsys.readouterr().err


def test__help_mentions_certification_warning() -> None:
    help_text = bundle_update._parser().format_help()
    assert "certifies the target model" in help_text
    assert "--country" in help_text
