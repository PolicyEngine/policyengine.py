"""Release versioning preserves the reviewed registry dependency graph."""

import copy
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "release_lock", ROOT / "scripts/release_lock.py"
)
release_lock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_lock)


def test_registry_lock_rejects_other_sources():
    project = {
        "project": {
            "name": "policyengine",
            "version": "6.0.0",
            "requires-python": ">=3.11",
        }
    }
    lock = {
        "requires-python": ">=3.11",
        "package": [
            {"name": "policyengine", "version": "6.0.0", "source": {"editable": "."}},
            {
                "name": "example",
                "version": "1.0.0",
                "source": {"registry": "https://pypi.org/simple"},
                "wheels": [
                    {
                        "url": "https://files.pythonhosted.org/packages/example.whl",
                        "hash": "sha256:" + "a" * 64,
                    }
                ],
            },
        ],
    }
    release_lock.validate_registry_lock(project, lock)
    for source in (
        {"directory": "../example"},
        {"git": "https://example.com/repo"},
        {"url": "file:///tmp/example.whl"},
        {"registry": "https://other.example/simple"},
    ):
        changed = copy.deepcopy(lock)
        changed["package"][1]["source"] = source
        with pytest.raises(ValueError, match="registry"):
            release_lock.validate_registry_lock(project, changed)


def test_registry_lock_rejects_version_and_python_drift():
    project = {
        "project": {
            "name": "policyengine",
            "version": "6.0.0",
            "requires-python": ">=3.11",
        }
    }
    lock = {
        "requires-python": ">=3.11",
        "package": [
            {"name": "policyengine", "version": "5.3.0", "source": {"editable": "."}}
        ],
    }
    with pytest.raises(ValueError, match="version"):
        release_lock.validate_registry_lock(project, lock)
    release_lock.validate_registry_lock(project, lock, allow_previous_version=True)
    lock["requires-python"] = ">=3.9"
    with pytest.raises(ValueError, match="Python"):
        release_lock.validate_registry_lock(project, lock, allow_previous_version=True)


@pytest.mark.parametrize(
    "config",
    [
        {"project": {"dependencies": ["example @ file:///tmp/example.whl"]}},
        {
            "project": {
                "optional-dependencies": {"us": ["example @ https://example.com/x.whl"]}
            }
        },
        {"tool": {"uv": {"sources": {"example": {"path": "../example"}}}}},
        {"tool": {"uv": {"index": [{"url": "https://other.example/simple"}]}}},
    ],
)
def test_registry_project_rejects_development_overrides(config):
    with pytest.raises(ValueError, match="registry"):
        release_lock.validate_registry_project(config)


def test_actual_uv_refresh_updates_only_root_version(tmp_path):
    if shutil.which("uv") is None:
        pytest.skip("uv is required for the release workflow")
    project = tmp_path / "pyproject.toml"
    project.write_text(
        '[project]\nname = "policyengine"\nversion = "5.3.0"\nrequires-python = ">=3.11"\n[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n'
    )
    subprocess.run(
        ["uv", "lock", "--offline", "--no-config"],
        cwd=tmp_path,
        check=True,
        env=release_lock.resolver_environment(),
    )
    before = release_lock.load_toml(tmp_path / "uv.lock")
    project.write_text(project.read_text().replace('"5.3.0"', '"6.0.0"'))
    release_lock.check_release_lock(tmp_path, refresh=True)
    after = release_lock.load_toml(tmp_path / "uv.lock")
    assert after["package"][0]["version"] == "6.0.0"
    assert release_lock.without_root_version(
        before, "policyengine"
    ) == release_lock.without_root_version(after, "policyengine")
    release_lock.check_release_lock(tmp_path)


def test_refresh_restores_reviewed_lock_on_dependency_drift(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="policyengine"\nversion="6.0.0"\nrequires-python=">=3.11"\n'
    )
    lock_path = tmp_path / "uv.lock"
    before = b'requires-python=">=3.11"\n[[package]]\nname="policyengine"\nversion="5.3.0"\nsource={editable="."}\n'
    lock_path.write_bytes(before)

    def changed(*args, **kwargs):
        lock_path.write_bytes(
            before.replace(b"5.3.0", b"6.0.0")
            + b'[[package]]\nname="unexpected"\nversion="1"\nsource={registry="https://pypi.org/simple"}\nwheels=[{url="https://files.pythonhosted.org/packages/example.whl",hash="sha256:'
            + b"a" * 64
            + b'"}]\n'
        )

    monkeypatch.setattr(release_lock.subprocess, "run", changed)
    with pytest.raises(ValueError, match="dependency graph"):
        release_lock.check_release_lock(tmp_path, refresh=True)
    assert lock_path.read_bytes() == before


def test_resolver_environment_disables_inherited_overrides(monkeypatch):
    monkeypatch.setenv("UV_FROZEN", "1")
    monkeypatch.setenv("UV_FIND_LINKS", "/tmp/candidate-wheels")
    monkeypatch.setenv("UV_INDEX", "https://other.example/simple")
    env = release_lock.resolver_environment()
    assert env["UV_FROZEN"] == "0"
    assert "UV_FIND_LINKS" not in env
    assert "UV_INDEX" not in env


@pytest.fixture(scope="module")
def actual_registry_project(tmp_path_factory):
    root = tmp_path_factory.mktemp("registry-artifact-lock")
    (root / "pyproject.toml").write_text(
        '[project]\nname="policyengine"\nversion="6.0.0"\nrequires-python=">=3.11"\n'
        'dependencies=["packaging==26.2"]\n[build-system]\nrequires=["setuptools"]\n'
        'build-backend="setuptools.build_meta"\n'
    )
    subprocess.run(
        [
            "uv",
            "lock",
            "--no-config",
            "--no-sources",
            "--default-index",
            release_lock.PYPI,
        ],
        cwd=root,
        check=True,
        env=release_lock.resolver_environment(),
    )
    release_lock.check_release_lock(root)
    return root


@pytest.mark.parametrize("kind", ["sdist", "wheel"])
@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/unpublished-candidate.whl",
        "https://example.com/unpublished-candidate.whl",
        "http://files.pythonhosted.org/packages/candidate.whl",
        "https://files.pythonhosted.org.evil.example/packages/candidate.whl",
        "https://user@files.pythonhosted.org/packages/candidate.whl",
        "https://files.pythonhosted.org:8443/packages/candidate.whl",
    ],
)
def test_actual_uv_lock_rejects_artifact_locations_without_mutating(
    actual_registry_project, tmp_path, kind, url
):
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(actual_registry_project / name, tmp_path / name)
    lock_path = tmp_path / "uv.lock"
    package = next(
        p
        for p in release_lock.load_toml(lock_path)["package"]
        if p["name"] == "packaging"
    )
    artifact = package["sdist"] if kind == "sdist" else package["wheels"][0]
    lock_path.write_text(lock_path.read_text().replace(artifact["url"], url))
    before = lock_path.read_bytes()
    for refresh in (False, True):
        with pytest.raises(ValueError, match="artifact"):
            release_lock.check_release_lock(tmp_path, refresh=refresh)
        assert lock_path.read_bytes() == before


@pytest.mark.parametrize(
    "digest", ["sha256:short", "sha256:" + "g" * 64, "md5:" + "a" * 64, ""]
)
def test_actual_uv_lock_rejects_malformed_hash_without_mutating(
    actual_registry_project, tmp_path, digest
):
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(actual_registry_project / name, tmp_path / name)
    lock_path = tmp_path / "uv.lock"
    package = next(
        p
        for p in release_lock.load_toml(lock_path)["package"]
        if p["name"] == "packaging"
    )
    before_text = lock_path.read_text()
    lock_path.write_text(before_text.replace(package["wheels"][0]["hash"], digest))
    before = lock_path.read_bytes()
    with pytest.raises(ValueError, match="artifact"):
        release_lock.check_release_lock(tmp_path)
    assert lock_path.read_bytes() == before
