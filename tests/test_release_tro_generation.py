"""Release regeneration authenticates the reviewed, complete TRACE inputs."""

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest
import requests

from policyengine.provenance import manifest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "release_tros"
sys.path.insert(0, str(ROOT / "scripts"))
import bundle as maintenance  # noqa: E402
import generate_trace_tros as generator  # noqa: E402


@pytest.fixture
def release(monkeypatch, tmp_path):
    package = tmp_path / "policyengine"
    bundle_dir = package / "data" / "bundle"
    bundle_dir.mkdir(parents=True)
    for name in ("manifest.json", "us.trace.tro.jsonld"):
        shutil.copyfile(FIXTURES / name, bundle_dir / name)
    # Only the public US snapshot is a repository test fixture. UK is verified
    # against its authenticated private release in the release preflight.
    source = json.loads((bundle_dir / "manifest.json").read_bytes())
    source["data_releases"].pop("uk")
    source["packages"].pop("policyengine-uk")
    (bundle_dir / "manifest.json").write_text(json.dumps(source))
    monkeypatch.setattr(generator, "BUNDLE_MANIFEST", bundle_dir / "manifest.json")
    monkeypatch.setattr(generator, "BUNDLE_TRO_DIR", bundle_dir)
    lock_path = tmp_path / "uv.lock"
    shutil.copyfile(FIXTURES / "country-models.lock.toml", lock_path)
    monkeypatch.setattr(generator, "BUNDLE_LOCK", lock_path)
    monkeypatch.setattr(manifest, "files", lambda _: package)
    response = requests.Response()
    response.status_code = 200
    response._content = (FIXTURES / "us-release_manifest.json").read_bytes()
    monkeypatch.setattr(manifest.requests, "get", lambda *a, **kw: response)
    manifest.get_release_manifest.cache_clear()
    manifest.get_data_release_manifest.cache_clear()
    yield bundle_dir, response
    manifest.get_release_manifest.cache_clear()
    manifest.get_data_release_manifest.cache_clear()


def test_strict_generation_is_complete_and_deterministic(release):
    first = generator.generated_tros(strict=True)
    assert first == generator.generated_tros(strict=True)
    artifacts = json.loads(first[0][1])["@graph"][0]["trov:hasComposition"][
        "trov:hasArtifact"
    ]
    assert len(artifacts) == 4
    assert any(
        item["trov:sha256"]
        == hashlib.sha256(
            (FIXTURES / "us-release_manifest.json").read_bytes()
        ).hexdigest()
        for item in artifacts
    )


def test_runtime_pin_update_requires_matching_certified_model(release):
    from prepare_package_bundle_update import update_package_pins

    path = release[0] / "manifest.json"
    original = path.read_bytes()
    tro_path = release[0] / "us.trace.tro.jsonld"
    reviewed = tro_path.read_bytes()
    updated = update_package_pins(
        json.loads(original), argparse.Namespace(core=None, us="1.824.1", uk=None)
    )
    path.write_text(json.dumps(updated))
    manifest.get_release_manifest.cache_clear()
    manifest.get_data_release_manifest.cache_clear()
    for action in (generator.regenerate_all, maintenance._check_tros):
        with pytest.raises(ValueError, match="runtime.*model"):
            action(strict=True)
        assert tro_path.read_bytes() == reviewed
    # Restoring the actual certified runtime pin admits the same real inputs.
    path.write_bytes(original)
    manifest.get_release_manifest.cache_clear()
    manifest.get_data_release_manifest.cache_clear()
    generator.regenerate_all(strict=True)
    assert maintenance._check_tros(strict=True) == 0


@pytest.mark.parametrize("field", ["name", "version", "sha256", "wheel_url"])
def test_runtime_model_identity_must_match_certification(release, field):
    path = release[0] / "manifest.json"
    payload = json.loads(path.read_bytes())
    payload["packages"]["policyengine-us"][field] = "different"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="runtime.*model"):
        generator.regenerate_all(strict=True)


@pytest.mark.parametrize(
    "change", ["missing", "version", "url", "hash", "registry", "extra-wheel"]
)
def test_certified_model_must_match_locked_wheel(release, change):
    lock_path = generator.BUNDLE_LOCK
    text = lock_path.read_text()
    model = manifest.get_release_manifest("us").model_package
    if change == "missing":
        lock_path.unlink()
    elif change == "extra-wheel":
        record = next(
            line for line in text.splitlines() if f'url = "{model.wheel_url}"' in line
        )
        lock_path.write_text(
            text.replace(record, record + "\n" + record.replace("/e2/", "/aa/"))
        )
    else:
        old, new = {
            "version": ('version = "1.764.6"', 'version = "1.824.1"'),
            "url": (model.wheel_url, model.wheel_url.replace("/e2/", "/aa/")),
            "hash": (model.sha256, "a" * 64),
            "registry": ("https://pypi.org/simple", "https://example.com/simple"),
        }[change]
        assert old in text
        lock_path.write_text(text.replace(old, new))
    path = release[0] / "us.trace.tro.jsonld"
    before = path.read_bytes()
    with pytest.raises(ValueError, match="lock|registry"):
        generator.regenerate_all(strict=True)
    assert path.read_bytes() == before


@pytest.mark.parametrize("status", [401, 403, 404, 503])
def test_strict_fetch_failure_preserves_reviewed_tro(release, status):
    bundle_dir, response = release
    path = bundle_dir / "us.trace.tro.jsonld"
    before = path.read_bytes()
    response.status_code = status
    with pytest.raises(ValueError, match="data release manifest"):
        generator.regenerate_all(strict=True)
    assert path.read_bytes() == before


def test_local_generation_retains_explicit_limited_mode(release, capsys):
    release[1].status_code = 404
    assert generator.generated_tros()
    assert "writing limited TRO" in capsys.readouterr().err


def test_strict_rejects_changed_remote_manifest_bytes(release):
    # Equivalent JSON with changed bytes must not silently replace reviewed pins.
    release[1]._content += b"\n"
    with pytest.raises(ValueError, match="reviewed.*hash"):
        generator.generated_tros(strict=True)


def test_strict_network_failure_never_writes_limited_output(
    release, monkeypatch, capsys
):
    path = release[0] / "us.trace.tro.jsonld"
    before = path.read_bytes()

    def unavailable(*args, **kwargs):
        raise requests.Timeout("fixture timeout")

    monkeypatch.setattr(manifest.requests, "get", unavailable)
    with pytest.raises(manifest.DataReleaseManifestUnavailableError):
        generator.regenerate_all(strict=True)
    assert path.read_bytes() == before
    assert "limited TRO" not in capsys.readouterr().err


def test_strict_missing_remote_dataset_never_writes_limited_output(release, capsys):
    path = release[0] / "us.trace.tro.jsonld"
    before = path.read_bytes()
    data = json.loads(release[1].content)
    del data["artifacts"][data["default_datasets"]["national"]]
    release[1]._content = json.dumps(data).encode()
    with pytest.raises(ValueError, match="Default dataset"):
        generator.regenerate_all(strict=True)
    assert path.read_bytes() == before
    assert "limited TRO" not in capsys.readouterr().err


@pytest.mark.parametrize("remove_models", [False, True])
def test_strict_cannot_skip_missing_country_declarations(release, remove_models):
    path = release[0] / "manifest.json"
    payload = json.loads(path.read_bytes())
    payload["data_releases"] = {}
    if remove_models:
        payload["packages"] = {}
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="every bundled country"):
        generator.generated_tros(strict=True)


@pytest.mark.parametrize(
    "change", ["dataset", "hash", "wheel", "certification", "revision"]
)
def test_strict_rejects_incomplete_or_drifted_certification(
    release, monkeypatch, change
):
    country = copy.deepcopy(manifest.get_release_manifest("us"))
    if change == "dataset":
        country.certified_data_artifact.dataset = "missing"
    elif change == "hash":
        country.certified_data_artifact.sha256 = "a" * 64
    elif change == "wheel":
        country.model_package.sha256 = None
    elif change == "certification":
        country.certification.certified_for_model_version = "0.0.0"
    else:
        country.data_package.release_manifest_revision = "main"
    monkeypatch.setattr(generator, "get_release_manifest", lambda _: country)
    with pytest.raises(ValueError):
        generator.generated_tros(strict=True)


@pytest.mark.parametrize("change", ["missing", "limited", "location"])
def test_strict_requires_prepared_reviewed_sidecar(release, change):
    path = release[0] / "us.trace.tro.jsonld"
    if change == "missing":
        path.unlink()
    elif change == "limited":
        release[1].status_code = 404
        path.write_bytes(generator.generated_tros()[0][1])
        release[1].status_code = 200
    else:
        path.write_text(path.read_text().replace("resolve/populace-", "resolve/other-"))
    with pytest.raises(ValueError, match="reviewed"):
        generator.generated_tros(strict=True)


def test_strict_all_countries_validate_before_any_write(release, monkeypatch):
    path = release[0] / "us.trace.tro.jsonld"
    before = path.read_bytes()
    bundle_path = release[0] / "manifest.json"
    bundle = json.loads(bundle_path.read_bytes())
    bundle["data_releases"]["zz"] = bundle["data_releases"]["us"]
    bundle_path.write_text(json.dumps(bundle))
    with pytest.raises(ValueError):
        generator.regenerate_all(strict=True)
    assert path.read_bytes() == before


def test_reviewed_sidecar_allows_only_version_regeneration(release):
    spec = importlib.util.spec_from_file_location(
        "release_bump", ROOT / ".github/bump_version.py"
    )
    bump = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bump)
    before = generator.generated_tros(strict=True)[0][1]
    bump.sync_bundle_versions(release[0] / "manifest.json", "6.0.0")
    manifest.get_release_manifest.cache_clear()
    manifest.get_data_release_manifest.cache_clear()
    after = generator.generated_tros(strict=True)[0][1]
    assert before != after
    assert b'"schema:softwareVersion": "6.0.0"' in after
    assert b'"pe:emittedIn": "repository-bundle"' in after
    # New version bytes are allowed, but regenerate/check must agree exactly.
    generator.regenerate_all(strict=True)
    assert generator.generated_tros(strict=True)[0][1] == after


def test_strict_cli_requires_tros_and_checks_exact_bytes(release, monkeypatch):
    import generate_bundle_artifacts

    with pytest.raises(SystemExit) as exc:
        maintenance.main(["check", "--strict-tros"])
    assert exc.value.code == 2
    monkeypatch.setattr(generate_bundle_artifacts, "generate", lambda **kw: 0)
    monkeypatch.setattr(maintenance, "REPO_ROOT", release[0].parents[2])
    assert maintenance.main(["check", "--include-tros", "--strict-tros"]) == 1
    assert maintenance.main(["generate", "--include-tros", "--strict-tros"]) == 0
    assert maintenance.main(["check", "--include-tros", "--strict-tros"]) == 0


def test_release_workflows_gate_complete_inputs_and_lock():
    import yaml

    pr = yaml.safe_load((ROOT / ".github/workflows/pr_code_changes.yaml").read_text())
    push = yaml.safe_load((ROOT / ".github/workflows/push.yaml").read_text())
    assert "pull_request_target" not in pr.get("on", pr.get(True, {}))
    assert (
        "github.event.pull_request.head.repo.full_name == github.repository"
        in pr["jobs"]["BundleVerification"]["if"]
    )
    for job in (
        push["jobs"]["Versioning"],
        push["jobs"]["Publish"],
    ):
        commands = "\n".join(step.get("run", "") for step in job["steps"])
        assert "check --published-spm --include-tros --strict-tros" in commands
        assert 'if [[ -z "${HUGGING_FACE_TOKEN:-}" ]]' in commands
        assert "python scripts/release_lock.py" in commands
        assert commands.index(
            "python scripts/check_release_credentials.py"
        ) < commands.index("check --published-spm")
    # The pull-request job checks only the reviewed registry lock. The
    # read-only credential, published-measurement and TRACE sidecar gates
    # depend on the release workflow regenerating sidecars and publishing
    # wheels first, so a pull request can never satisfy them.
    pr_commands = "\n".join(
        step.get("run", "") for step in pr["jobs"]["BundleVerification"]["steps"]
    )
    assert "python scripts/release_lock.py" in pr_commands
    assert "--published-spm" not in pr_commands
    commands = "\n".join(
        step.get("run", "") for step in push["jobs"]["Versioning"]["steps"]
    )
    assert commands.index("check --published-spm") < commands.index("make changelog")
    assert (
        commands.index("make changelog")
        < commands.index("release_lock.py --refresh")
        < commands.index("generate --include-tros --strict-tros")
    )
