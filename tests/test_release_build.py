"""Small release-boundary controls; no country simulation or publication."""

import base64
import copy
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "release_build", ROOT / "scripts/release_build.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def wheel_bytes(version="6.0.0", changed=False, package="policyengine"):
    prefix = f"{package.replace('-', '_')}-{version}.dist-info/"
    members = {
        "policyengine/__init__.py": b"value = 1\n",
        prefix
        + "METADATA": f"Metadata-Version: 2.4\nName: {package}\nVersion: {version}\n".encode(),
        prefix + "WHEEL": b"Wheel-Version: 1.0\nGenerator: frozen\nTag: py3-none-any\n",
    }
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name, data in members.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
        writer.writerow([name, "sha256=" + digest.decode(), len(data)])
    writer.writerow([prefix + "RECORD", "", ""])
    members[prefix + "RECORD"] = record.getvalue().encode()
    if changed:
        members["policyengine/__init__.py"] = b"value = 2\n"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return output.getvalue()


def test_wheel_record_authenticates_every_member():
    actual = release.wheel_identity(wheel_bytes(), "6.0.0")
    assert actual["version"] == "6.0.0"
    assert len(actual["members"]) == 4
    with pytest.raises(ValueError, match="RECORD"):
        release.wheel_identity(wheel_bytes(changed=True), "6.0.0")
    with pytest.raises(ValueError, match="version"):
        release.wheel_identity(wheel_bytes(), "6.0.0rc1")


def test_wheel_rejects_duplicate_and_escaping_members():
    for name in ("../escape", "policyengine/__init__.py"):
        output = io.BytesIO(wheel_bytes())
        with zipfile.ZipFile(output, "a") as archive:
            archive.writestr(name, b"bad")
        with pytest.raises(ValueError):
            release.wheel_identity(output.getvalue(), "6.0.0")


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True
    )
    (root / ".github").mkdir()
    (root / ".github/bump_version.py").write_bytes(
        (ROOT / ".github/bump_version.py").read_bytes()
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname="policyengine"\nversion="5.3.1"\n'
    )
    (root / "CHANGELOG.md").write_text("## [5.3.1]\n")
    (root / "changelog.d").mkdir()
    (root / "changelog.d/change.breaking.md").write_text("Change\n")
    path = root / release.BUNDLE_PATH
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "bundle_version": "5.3.1",
                "policyengine_version": "5.3.1",
                "packages": {
                    "policyengine": {"name": "policyengine", "version": "5.3.1"},
                    "policyengine-us": {
                        "name": "policyengine-us",
                        "version": "2.0.2",
                        "country": "us",
                        "import_name": "policyengine_us",
                        "role": "country_model",
                    },
                },
                "data_releases": {
                    "us": {
                        "policyengine_version": "5.3.1",
                        "bundle_id": "us-5.3.1",
                        "certification": {"fake": True},
                        "certified_data_artifact": {"old": True},
                        "model_package": {
                            "name": "policyengine-us",
                            "version": "2.0.2",
                        },
                    },
                    "uk": {
                        "policyengine_version": "5.3.1",
                        "bundle_id": "uk-5.3.1",
                        "certification": {"real": True},
                    },
                },
            }
        )
    )
    for country in ("us", "uk"):
        (path.parent / f"{country}.trace.tro.jsonld").write_text("{}")
    schema = root / "src/policyengine/data/schemas/trace_tro.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_bytes(
        (ROOT / "src/policyengine/data/schemas/trace_tro.schema.json").read_bytes()
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "Fixture"], cwd=root, check=True)
    return root


def test_prerelease_uses_real_prediction_and_syncs_every_identity(source):
    assert release.predicted_version(source) == "6.0.0"
    release.prepare_prerelease_metadata(source, "6.0.0rc1")
    bundle = json.loads((source / release.BUNDLE_PATH).read_text())
    assert bundle["bundle_version"] == bundle["policyengine_version"] == "6.0.0rc1"
    assert bundle["packages"]["policyengine"]["version"] == "6.0.0rc1"
    for country, manifest in bundle["data_releases"].items():
        assert manifest["policyengine_version"] == "6.0.0rc1"
        assert manifest["bundle_id"] == f"{country}-6.0.0rc1"
    assert "certification" not in bundle["data_releases"]["us"]
    assert "certified_data_artifact" not in bundle["data_releases"]["us"]
    assert bundle["data_releases"]["uk"]["certification"] == {"real": True}
    assert bundle["development"]["data_certification"] == "not_certified"


def test_prepared_tree_captures_deletions_without_staging_operator_files(source):
    before = release.git(source, "write-tree")
    fragment = source / "changelog.d/change.breaking.md"
    fragment.unlink()
    (source / "CHANGELOG.md").write_text("New release\n")
    (source / "operator-receipt.json").write_text("untrusted")
    prepared = release.prepared_tree(source)
    assert prepared != before
    assert release.git(source, "write-tree") == before
    names = release.git(source, "ls-tree", "-r", "--name-only", prepared).splitlines()
    assert "changelog.d/change.breaking.md" not in names
    assert "operator-receipt.json" not in names


def candidate(artifact_id=11):
    return {
        "artifact_id": artifact_id,
        "artifact_digest": "sha256:" + "a" * 64,
        "receipt": {
            "flavor": "release",
            "version": "6.0.0",
            "source": {
                "pr": 515,
                "head": "h" * 40,
                "base": "b" * 40,
                "merged_tree": "m" * 40,
            },
            "prepared_tree": "p" * 40,
            "preparation_inputs": {"tags": ["5.3.1"], "epoch": 100},
            "toolchain": {"version": "frozen"},
            "package_identity": {},
            "wheel": {
                "sha256": "w" * 64,
                "members": {"payload": {"sha256": "x" * 64, "size": 1}},
            },
        },
    }


def test_candidate_selection_is_deterministic_and_rejects_divergence():
    first, repeated = candidate(), candidate(12)
    assert release.select_candidate([repeated, first])["artifact_id"] == 11
    changed = copy.deepcopy(repeated)
    changed["receipt"]["wheel"]["sha256"] = "z" * 64
    with pytest.raises(ValueError, match="divergent"):
        release.select_candidate([first, changed])
    with pytest.raises(ValueError, match="candidate"):
        release.select_candidate([])


@pytest.mark.parametrize("field", ["head", "base", "merged_tree"])
def test_publication_rejects_wrong_source_even_with_a_matching_wheel(field):
    expected = candidate()["receipt"]
    actual = copy.deepcopy(expected)
    actual["source"][field] = "other"
    with pytest.raises(ValueError, match="source"):
        release.verify_prepared_receipt(actual, expected)


@pytest.mark.parametrize("field", ["prepared_tree", "preparation_inputs", "toolchain"])
def test_publication_rejects_preparation_or_toolchain_drift(field):
    expected = candidate()["receipt"]
    actual = copy.deepcopy(expected)
    actual[field] = "other"
    with pytest.raises(ValueError):
        release.verify_prepared_receipt(actual, expected)


def test_release_workflow_guards_before_public_side_effects():
    import yaml

    workflow = yaml.safe_load((ROOT / ".github/workflows/push.yaml").read_text())
    steps = workflow["jobs"]["Publish"]["steps"]
    guard = next(
        i
        for i, step in enumerate(steps)
        if "release_build.py publish-check" in step.get("run", "")
    )
    tag = next(
        i for i, step in enumerate(steps) if "publish-git-tag.sh" in step.get("run", "")
    )
    upload = next(
        i
        for i, step in enumerate(steps)
        if "gh-action-pypi-publish" in step.get("uses", "")
    )
    assert guard < tag < upload
    candidate_job = yaml.safe_load(
        (ROOT / ".github/workflows/pr_code_changes.yaml").read_text()
    )["jobs"]["ReleaseCandidate"]
    serialized = json.dumps(candidate_job)
    for forbidden in (
        "publish-git-tag",
        "add-and-commit",
        "gh-action-pypi-publish",
        "gh release",
        "dispatch-policyengine",
    ):
        assert forbidden not in serialized
    assert "upload-artifact" in serialized
    assert candidate_job["permissions"] == {"contents": "read", "actions": "read"}


@pytest.fixture
def artifact_service(monkeypatch):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("receipt.json", b"{}")
    raw = output.getvalue()
    artifact = {
        "id": 11,
        "expired": False,
        "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "workflow_run": {"id": 21, "head_sha": "h" * 40},
        "created_at": "2026-09-12T10:01:00Z",
    }
    run = {
        "id": 21,
        "status": "completed",
        "conclusion": "success",
        "event": "pull_request",
        "path": release.WORKFLOW,
        "repository": {"full_name": release.REPOSITORY},
        "head_repository": {"full_name": release.REPOSITORY},
        "head_sha": "h" * 40,
        "run_attempt": 1,
        "run_started_at": "2026-09-12T10:00:00Z",
        "updated_at": "2026-09-12T10:02:00Z",
    }
    attempt = copy.deepcopy(run)

    def get(path, *, binary=False):
        if binary:
            return raw
        if "/attempts/" in path:
            return attempt
        return artifact if "/artifacts/" in path else run

    monkeypatch.setattr(release, "github", get)
    return artifact, run, attempt


def test_artifact_authentication_accepts_actual_digest_and_origin(artifact_service):
    artifact, run, members = release.authenticated_artifact(
        release.REPOSITORY, 11, release.WORKFLOW
    )
    assert (
        artifact["id"] == 11 and run["id"] == 21 and members == {"receipt.json": b"{}"}
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("conclusion", "failure"),
        ("status", "in_progress"),
        ("event", "workflow_dispatch"),
        ("path", ".github/workflows/unreviewed.yaml"),
        ("head_sha", "other"),
        ("repository", {"full_name": "other/repository"}),
        ("head_repository", {"full_name": "fork/repository"}),
    ],
)
def test_artifact_rejects_wrong_workflow_source_or_origin(artifact_service, key, value):
    artifact_service[1][key] = value
    with pytest.raises(ValueError, match="workflow"):
        release.authenticated_artifact(release.REPOSITORY, 11, release.WORKFLOW)


def test_artifact_digest_cannot_be_replaced_by_an_operator_claim(artifact_service):
    artifact_service[0]["digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="digest"):
        release.authenticated_artifact(release.REPOSITORY, 11, release.WORKFLOW)


def test_makefile_consumes_frozen_date_instead_of_wall_clock():
    output = subprocess.check_output(
        ["make", "--dry-run", "changelog", "RELEASE_DATE=2032-01-02"],
        cwd=ROOT,
        text=True,
    )
    assert "towncrier build --yes --version" in output
    assert '--date "2032-01-02"' in output
    assert (
        release.controlled_environment({"epoch": 0, "release_date": "1970-01-01"})[
            "RELEASE_DATE"
        ]
        == "1970-01-01"
    )
    with pytest.raises(ValueError, match="date"):
        release.controlled_environment({"epoch": 0, "release_date": "2032-01-02"})


@pytest.mark.parametrize("flavor", ["release", "rc1"])
def test_shared_preparation_sequence_preserves_stable_and_prerelease_boundaries(
    source, monkeypatch, flavor
):
    calls = []
    monkeypatch.setattr(release, "check_toolchain", lambda root: {"frozen": True})
    monkeypatch.setattr(release, "require_unpublished", lambda version: None)
    monkeypatch.setattr(release, "verify_identity_fresh", lambda *args: {})

    def run(root, *cmd, env=None):
        calls.append((cmd, env))
        if "candidate-tros" in cmd:
            (root / release.BUNDLE_PATH.parent / "us.trace.tro.jsonld").write_text(
                "fixture limited TRO"
            )

    monkeypatch.setattr(release, "run", run)
    source_info = {"head": release.git(source, "rev-parse", "HEAD")}
    country = {
        "name": "policyengine-us",
        "version": "2.0.2",
        "sha256": "a" * 64,
        "wheel_url": "file:///candidate/country.whl",
    }
    if flavor == "rc1":
        path = source / release.BUNDLE_PATH
        payload = json.loads(path.read_text())
        payload["packages"]["policyengine-us"] = {
            "name": "policyengine-us",
            "version": "2.0.0",
        }
        path.write_text(json.dumps(payload))
    receipt = release.prepare(
        source, flavor, source_info, country if flavor == "rc1" else None
    )
    commands = [
        list(command[1:]) if command[0] == release.sys.executable else list(command)
        for command, _ in calls
    ]
    if flavor == "release":
        assert commands == [
            ["scripts/check_release_credentials.py"],
            [
                "scripts/bundle.py",
                "check",
                "--published-spm",
                "--include-tros",
                "--strict-tros",
            ],
            ["scripts/release_lock.py"],
            [
                "make",
                "changelog",
                "RELEASE_DATE=" + receipt["preparation_inputs"]["release_date"],
            ],
            ["scripts/bundle.py", "generate"],
            ["scripts/release_lock.py", "--refresh"],
            ["scripts/bundle.py", "generate", "--include-tros", "--strict-tros"],
            [
                "scripts/bundle.py",
                "check",
                "--published-spm",
                "--include-tros",
                "--strict-tros",
            ],
        ]
    else:
        assert commands == [
            ["scripts/bundle.py", "generate"],
            ["scripts/release_build.py", "candidate-tros", "--version", "6.0.0rc1"],
        ]
        payload = json.loads((source / release.BUNDLE_PATH).read_text())
        assert payload["data_releases"]["us"]["model_package"] == {
            "name": country["name"],
            "version": country["version"],
        }
        assert payload["packages"]["policyengine-us"] == {
            "name": "policyengine-us",
            "version": "2.0.2",
        }
    assert all(
        env["SOURCE_DATE_EPOCH"] == str(receipt["preparation_inputs"]["epoch"])
        for _, env in calls
    )


def test_limited_candidate_tro_uses_real_schema_without_data_or_certificate(
    source, monkeypatch
):
    monkeypatch.setenv("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    from jsonschema import Draft202012Validator

    tro = release.candidate_us_tro(source, "6.0.0rc1")
    schema = json.loads(
        (ROOT / "src/policyengine/data/schemas/trace_tro.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(tro)
    node = tro["@graph"][0]
    assert node["trov:createdWith"]["schema:softwareVersion"] == "6.0.0rc1"
    assert "unpublished; not reviewed for release" in node["schema:name"]
    assert "certif" not in json.dumps(tro).lower()
    artifacts = node["trov:hasComposition"]["trov:hasArtifact"]
    assert [a["@id"] for a in artifacts] == ["composition/1/artifact/bundle_manifest"]
    assert (
        artifacts[0]["trov:sha256"]
        == hashlib.sha256((source / release.BUNDLE_PATH).read_bytes()).hexdigest()
    )
    assert {key for key in node["trov:hasPerformance"] if key.startswith("pe:")} == {
        "pe:emittedIn"
    }
    assert node["trov:hasPerformance"]["pe:emittedIn"] == "repository-bundle"


@pytest.mark.parametrize(
    "tamper",
    ["certification", "version", "historical-comment", "uk-manifest", "uk-record"],
)
def test_candidate_identity_rejects_false_certification_or_stale_tro_version(
    source, monkeypatch, tamper
):
    monkeypatch.setenv("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    release.prepare_prerelease_metadata(source, "6.0.0rc1")
    from policyengine.provenance.trace import serialize_trace_tro

    path = source / release.BUNDLE_PATH
    bundle = json.loads(path.read_text())
    # Exercise the actual post-preparation manifest generator before verification.
    generator = release.load_helper(ROOT, "scripts/generate_bundle_artifacts.py")
    bundle = generator.normalized_manifest(bundle)
    path.write_text(json.dumps(bundle))
    us = release.candidate_us_tro(source, "6.0.0rc1")
    monkeypatch.setattr(release, "assert_source_origin", lambda root: {"fixture": True})
    monkeypatch.setattr(release, "candidate_uk_tro", lambda: copy.deepcopy(us))
    for country in ("us", "uk"):
        (path.parent / f"{country}.trace.tro.jsonld").write_bytes(
            serialize_trace_tro(us)
        )
    release.verify_identity(source, "6.0.0rc1", "rc1")
    if tamper == "certification":
        us["@graph"][0]["trov:hasPerformance"]["pe:compatibilityBasis"] = (
            "legacy_compatible_model_package"
        )
    elif tamper == "version":
        us["@graph"][0]["trov:createdWith"]["schema:softwareVersion"] = "5.3.1"
    elif tamper == "historical-comment":
        us["@graph"][0]["trov:wasAssembledBy"]["rdfs:comment"] = (
            "Historical build was certified"
        )
    if tamper.startswith("uk-"):
        changed = copy.deepcopy(us)
        if tamper == "uk-manifest":
            changed["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"][0][
                "trov:sha256"
            ] = "f" * 64
        else:
            changed["@graph"][0]["schema:description"] = "Stale serialized UK record"
        (path.parent / "uk.trace.tro.jsonld").write_bytes(serialize_trace_tro(changed))
    else:
        (path.parent / "us.trace.tro.jsonld").write_text(json.dumps(us))
    with pytest.raises(
        ValueError,
        match="certification|version|limited record|manifest hash|UK reconstruction",
    ):
        release.verify_identity(source, "6.0.0rc1", "rc1")


@pytest.mark.parametrize(
    "failure", [None, "rc1", "wrong-package", "wrong-head", "tampered-wheel"]
)
def test_country_artifact_requires_actual_final_wheel_and_authenticated_receipt(
    source, tmp_path, monkeypatch, failure
):
    monkeypatch.setenv("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    path = source / release.BUNDLE_PATH
    bundle = json.loads(path.read_text())
    bundle["packages"]["policyengine-us"] = {
        "name": "policyengine-us",
        "version": "2.0.2",
    }
    path.write_text(json.dumps(bundle))
    version = "2.0.2rc1" if failure == "rc1" else "2.0.2"
    package = "unexpected" if failure == "wrong-package" else "policyengine-us"
    raw = wheel_bytes(version, package=package, changed=failure == "tampered-wheel")
    filename = "policyengine_us-" + version + "-py3-none-any.whl"
    receipt = {
        "prepared_version": version,
        "source_head": "wrong" if failure == "wrong-head" else "h" * 40,
        "policy_source_matches_head": True,
        "wheel": {
            "filename": filename,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        },
    }
    monkeypatch.setattr(
        release,
        "authenticated_artifact",
        lambda *args: (
            {"id": 11, "digest": "sha256:" + "d" * 64},
            {"id": 21, "head_sha": "h" * 40, "run_attempt": 1},
            {
                "release-build/receipt.json": json.dumps(receipt).encode(),
                "dist/" + filename: raw,
            },
        ),
    )
    actual_command = release.source_command
    monkeypatch.setattr(
        release, "source_command", lambda root, *args: actual_command(ROOT, *args)
    )
    if failure:
        with pytest.raises(ValueError):
            release.country_component(source, "11", tmp_path / "country")
    else:
        component, evidence = release.country_component(
            source, "11", tmp_path / "country"
        )
        assert (
            component["name"] == "policyengine-us" and component["version"] == "2.0.2"
        )
        assert component["sha256"] == hashlib.sha256(raw).hexdigest()
        assert component["wheel_url"] == (tmp_path / "country" / filename).as_uri()
        assert evidence["component"] == component and evidence["artifact_id"] == 11
        assert evidence["source_head"] == "h" * 40


def test_no_country_artifact_input_is_an_explicit_hold(source, monkeypatch):
    monkeypatch.setattr(
        release,
        "authenticated_artifact",
        lambda *args: pytest.fail("No artifact was selected"),
    )
    with pytest.raises(ValueError, match="hold"):
        release.country_component(source, "", source / "unused")


def test_publication_checks_existing_strict_gates_before_member_comparison(
    source, tmp_path, monkeypatch
):
    actual_git = release.git
    head = actual_git(source, "rev-parse", "HEAD")
    source_info = {"pr": 515, "head": head, "base": "b" * 40, "merged_tree": "m" * 40}
    receipt = {
        "source": source_info,
        "flavor": "release",
        "version": "5.3.1",
        "preparation_inputs": release.preparation_inputs(source, head),
        "toolchain": {"frozen": True},
        "prepared_tree": "p" * 40,
        "package_identity": {},
        "wheel": {"sha256": "w" * 64, "members": {"payload": "actual"}},
    }
    calls = []

    def get_git(root, *args, **kwargs):
        if "--format=%s" in args:
            return "Update package version"
        if "--format=%P" in args:
            return head
        if args == ("rev-parse", "HEAD^1"):
            return head
        return actual_git(root, *args, **kwargs)

    monkeypatch.setattr(release, "git", get_git)
    monkeypatch.setattr(release, "source_from_merge", lambda *args: source_info)
    monkeypatch.setattr(
        release,
        "discover_candidate",
        lambda *args: {"receipt": receipt, "artifact_id": 11},
    )
    monkeypatch.setattr(release, "check_toolchain", lambda *args: receipt["toolchain"])
    monkeypatch.setattr(
        release, "prepared_tree", lambda *args: receipt["prepared_tree"]
    )
    monkeypatch.setattr(release, "verify_identity_fresh", lambda *args: {})
    monkeypatch.setattr(
        release,
        "require_unpublished",
        lambda version: calls.append(["registry-unpublished", version]),
    )
    monkeypatch.setattr(
        release, "run", lambda root, *command, env=None: calls.append(list(command[1:]))
    )

    def build(root, actual, output):
        calls.append(["build"])
        actual["wheel"] = copy.deepcopy(receipt["wheel"])

    monkeypatch.setattr(release, "build", build)
    release.publish_check(source, tmp_path / "receipt.json")
    assert calls == [
        ["scripts/check_release_credentials.py"],
        [
            "scripts/bundle.py",
            "check",
            "--published-spm",
            "--include-tros",
            "--strict-tros",
        ],
        ["scripts/release_lock.py"],
        ["build"],
        ["registry-unpublished", "5.3.1"],
    ]
    assert (
        json.loads((tmp_path / "receipt.json").read_text())["member_equality"] is True
    )


@pytest.mark.parametrize(
    "path",
    [
        "src/policyengine/hidden.json",
        "src/other_package/__init__.py",
        "scripts/hidden.py",
    ],
)
def test_untracked_inputs_cannot_enter_a_wheel_outside_the_prepared_tree(source, path):
    unexpected = source / path
    unexpected.parent.mkdir(parents=True, exist_ok=True)
    unexpected.write_text("untracked build input")
    # An ignored input can still be packaged by **/*; exclusion from status
    # cannot exempt it from source authentication.
    (source / ".gitignore").write_text(path + "\n")
    with pytest.raises(ValueError, match="Untracked package/build inputs"):
        release.prepared_tree(source)


@pytest.mark.parametrize(
    "tamper", [None, "hash", "version", "missing", "duplicate", "extra"]
)
def test_frozen_requirement_bytes_match_the_recorded_tool_closure(tmp_path, tamper):
    root = tmp_path
    (root / ".github").mkdir()
    config = json.loads((ROOT / ".github/release-toolchain.json").read_text())
    requirements = (ROOT / ".github/release-tools.txt").read_text()
    if tamper == "hash":
        requirements = requirements.replace(
            config["tools"]["build"]["wheels"][0]["sha256"], "f" * 64
        )
    elif tamper == "version":
        requirements = requirements.replace("build==1.6.1", "build==0.0.0")
    elif tamper == "missing":
        requirements = "\n".join(
            line for line in requirements.splitlines() if not line.startswith("build==")
        )
    elif tamper == "duplicate":
        requirements += (
            next(
                line for line in requirements.splitlines() if line.startswith("build==")
            )
            + "\n"
        )
    elif tamper == "extra":
        requirements += "unknown==1.0.0 --hash=sha256:" + "a" * 64 + "\n"
    (root / ".github/release-tools.txt").write_text(requirements)
    if tamper:
        with pytest.raises(ValueError, match="Frozen tool|frozen tool"):
            release.validate_tool_requirements(root, config)
    else:
        release.validate_tool_requirements(root, config)


@pytest.mark.parametrize("pin", ["25.0", "24.2", ">=25.0"])
def test_exported_tool_overlap_requires_exact_pin_and_preserves_other_bytes(pin):
    config = {"tools": {"packaging": {"version": "25.0"}}}
    other = (
        "other==1.0 ; sys_platform == 'win32' \\\n    --hash=sha256:" + "b" * 64 + "\n"
    )
    operator = ">=" if pin.startswith(">=") else "=="
    overlap = (
        "Packaging" + operator + pin.removeprefix(">=") + " \\\n"
        "    --hash=sha256:" + "a" * 64 + " \\\n"
        "    --hash=sha256:" + "c" * 64 + "\n"
    )
    if pin != "25.0":
        with pytest.raises(ValueError, match="pin differs"):
            release.filter_tool_overlaps(overlap + other, config)
    else:
        filtered, removed = release.filter_tool_overlaps(overlap + other, config)
        assert filtered == other
        assert removed == [{"name": "packaging", "version": "25.0"}]
        assert release.filter_tool_overlaps(other, config) == (other, [])


def test_bootstrap_filters_before_sync_and_records_the_governing_file(
    tmp_path, monkeypatch
):
    root = tmp_path / "source"
    (root / ".github").mkdir(parents=True)
    for name in ("release-toolchain.json", "release-tools.txt"):
        (root / ".github" / name).write_bytes((ROOT / ".github" / name).read_bytes())
    base = "packaging==25.0 --hash=sha256:" + "a" * 64 + "\n"
    calls = []

    def fake_run(root, *command, env=None):
        calls.append(command)
        if command[:2] == ("uv", "export"):
            Path(command[command.index("--output-file") + 1]).write_text(base)
            assert {"--frozen", "--no-header", "--no-annotate"} <= set(command)
        elif command[:3] == ("uv", "pip", "sync"):
            assert Path(command[-2]).read_text() == ""
            assert Path(command[-1]) == root / ".github/release-tools.txt"
            assert "--require-hashes" in command and "--only-binary" in command

    monkeypatch.setattr(release, "run", fake_run)
    monkeypatch.setenv("GITHUB_PATH", str(tmp_path / "github-path"))
    config = json.loads((root / ".github/release-toolchain.json").read_text())
    evidence = release.export_base_requirements(root, tmp_path / "export.txt", config)
    assert evidence == {
        "exported_base_sha256": release.sha256(base.encode()),
        "filtered_base_sha256": release.sha256(b""),
        "removed_tool_overlaps": [{"name": "packaging", "version": "25.0"}],
        "governing_tool_file": ".github/release-tools.txt",
        "governing_tool_file_sha256": release.sha256(
            (root / ".github/release-tools.txt").read_bytes()
        ),
    }
    calls.clear()
    release.bootstrap(root, tmp_path / "build-env")
    assert [command[:2] for command in calls[:4]] == [
        ("uv", "export"),
        ("uv", "venv"),
        ("uv", "pip"),
        ("uv", "pip"),
    ]
    assert calls[-1][-1] == "check-toolchain"


def test_optional_numerical_job_skips_without_weakening_stable_gates():
    import yaml

    jobs = yaml.safe_load(
        (ROOT / ".github/workflows/pr_code_changes.yaml").read_text()
    )["jobs"]
    stable, numerical = jobs["ReleaseCandidate"], jobs["NumericalCandidate"]
    assert "RELEASE_COUNTRY_CANDIDATE_ARTIFACT_ID" not in json.dumps(stable)
    assert (
        numerical["if"]
        == stable["if"] + " && vars.RELEASE_COUNTRY_CANDIDATE_ARTIFACT_ID != ''"
    )
    for job, flavor in ((stable, "release"), (numerical, "rc1")):
        assert "strategy" not in job and "matrix" not in job["if"]
        assert any(
            f"candidate --flavor {flavor}" in step.get("run", "")
            for step in job["steps"]
        )
        assert job["permissions"] == {"contents": "read", "actions": "read"}
        assert not any(
            term in json.dumps(job)
            for term in (
                "publish-git-tag",
                "add-and-commit",
                "gh-action-pypi-publish",
                "gh release",
            )
        )
    # Both release phases retain their unconditional helper gate. The optional
    # numerical input cannot be consulted anywhere in either phase.
    push = yaml.safe_load((ROOT / ".github/workflows/push.yaml").read_text())["jobs"]
    for name, command in (("Versioning", "versioning"), ("Publish", "publish-check")):
        assert "RELEASE_COUNTRY_CANDIDATE_ARTIFACT_ID" not in json.dumps(push[name])
        step = next(
            step
            for step in push[name]["steps"]
            if f"release_build.py {command}" in step.get("run", "")
        )
        assert "if" not in step
    for job in [stable, numerical, push["Versioning"], push["Publish"]]:
        for step in job["steps"]:
            if "uses" in step and not step["uses"].startswith("./"):
                assert release.re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])


@pytest.mark.parametrize(
    "tamper",
    [
        None,
        "package-hash",
        "model-hash",
        "package-role",
        "model-version",
        "manifest-uri",
        "us-uri",
        "uk-uri",
    ],
)
def test_final_generated_candidate_descriptor_and_uri_controls(
    source, monkeypatch, tamper
):
    from policyengine.provenance.trace import serialize_trace_tro

    path = source / release.BUNDLE_PATH
    country = {
        "name": "policyengine-us",
        "version": "2.0.2",
        "sha256": "a" * 64,
        "wheel_url": "file:///local/country.whl",
    }
    release.prepare_prerelease_metadata(source, "6.0.0rc1", country)
    generator = release.load_helper(ROOT, "scripts/generate_bundle_artifacts.py")
    bundle = generator.normalized_manifest(json.loads(path.read_text()))
    if tamper == "package-hash":
        bundle["packages"]["policyengine-us"]["sha256"] = country["sha256"]
    elif tamper == "model-hash":
        bundle["data_releases"]["us"]["model_package"]["sha256"] = country["sha256"]
    elif tamper == "package-role":
        bundle["packages"]["policyengine-us"]["role"] = "unknown"
    elif tamper == "model-version":
        bundle["data_releases"]["us"]["model_package"]["version"] = "2.0.2rc1"
    elif tamper == "manifest-uri":
        bundle["development"]["unexpected_location"] = "FILE:/local/country.whl"
    path.write_text(json.dumps(bundle))
    us = release.candidate_us_tro(source, "6.0.0rc1")
    monkeypatch.setattr(release, "assert_source_origin", lambda root: {"fixture": True})
    monkeypatch.setattr(release, "candidate_uk_tro", lambda: copy.deepcopy(us))
    for code in ("us", "uk"):
        tro = copy.deepcopy(us)
        if tamper == code + "-uri":
            tro["@graph"][0]["schema:description"] = "file:///local/country.whl"
        (path.parent / f"{code}.trace.tro.jsonld").write_bytes(serialize_trace_tro(tro))
    if tamper:
        with pytest.raises(ValueError, match="descriptors|local file URI"):
            release.verify_identity(source, "6.0.0rc1", "rc1")
    else:
        identity = release.verify_identity(source, "6.0.0rc1", "rc1")
        assert identity["bundle_manifest_sha256"] == release.sha256(path.read_bytes())


def test_expected_preparation_errors_are_clean_holds(source, monkeypatch):
    from types import SimpleNamespace

    import policyengine.provenance.manifest as manifests

    def stop(*args):
        raise SystemExit(1)

    monkeypatch.setattr(
        release,
        "load_helper",
        lambda *args: SimpleNamespace(get_current_version=stop, bump_version=stop),
    )
    with pytest.raises(ValueError, match="hold: stable version prediction failed"):
        release.predicted_version(source)
    with pytest.raises(
        ValueError, match="hold: UK TRACE fails schema validation"
    ) as error:
        release.validate_tro_schema(source, {"private": "secret-never-echo"}, "uk")
    assert "secret-never-echo" not in str(error.value)

    def unavailable(*args):
        raise manifests.DataReleaseManifestUnavailableError("private-secret-never-echo")

    monkeypatch.setattr(manifests, "get_data_release_manifest", unavailable)
    with pytest.raises(
        ValueError, match="hold: UK release manifest unavailable"
    ) as error:
        release.candidate_uk_tro()
    assert "secret-never-echo" not in str(error.value)


@pytest.mark.parametrize(
    "stderr,expected",
    [
        ("gh: Forbidden (HTTP 403)", "access denied"),
        ("gh: Not Found (HTTP 404)", "not found or inaccessible"),
        ("gh: API rate limit exceeded (HTTP 403)", "rate limit"),
        ("Run gh auth login", "authentication unavailable"),
        ("transport failed", "request failed"),
    ],
)
def test_github_failures_are_actionable_without_echoing_secrets(
    monkeypatch, stderr, expected
):
    from types import SimpleNamespace

    monkeypatch.setattr(
        release.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout=b"",
            stderr=(stderr + "\nAuthorization: Bearer secret-never-echo").encode(),
        ),
    )
    path = "repos/PolicyEngine/policyengine-us/actions/artifacts/11"
    with pytest.raises(ValueError) as error:
        release.github(path + "?token=secret-never-echo")
    assert expected in str(error.value) and path in str(error.value)
    assert "secret-never-echo" not in str(error.value)


@pytest.mark.parametrize(
    "tamper", ["failed-attempt", "earlier-artifact", "wrong-attempt", "after-attempt"]
)
def test_artifact_requires_the_actual_current_successful_producing_attempt(
    artifact_service, tamper
):
    artifact, run, attempt = artifact_service
    if tamper == "failed-attempt":
        attempt["conclusion"] = "failure"
    elif tamper == "earlier-artifact":
        artifact["created_at"] = "2026-09-12T09:59:00Z"
    elif tamper == "after-attempt":
        artifact["created_at"] = "2026-09-12T10:03:00Z"
    else:
        attempt["run_attempt"] = 2
    with pytest.raises(ValueError, match="attempt"):
        release.authenticated_artifact(release.REPOSITORY, 11, release.WORKFLOW)


def test_candidate_hold_names_the_exact_base_and_supported_merge_modes(monkeypatch):
    monkeypatch.setattr(release, "pages", lambda *args: [])
    source = candidate()["receipt"]["source"]
    with pytest.raises(ValueError, match="publication hold") as error:
        release.discover_candidate(source)
    assert source["base"] in str(error.value)
    assert "merge or squash" in str(error.value)
    assert "rebase merges are unsupported" in str(error.value)


@pytest.mark.parametrize("registry", ["404", "files", "deleted-files", "403"])
def test_registry_absence_requires_authoritative_404(monkeypatch, registry):
    def fetch(*args, **kwargs):
        if registry in {"404", "403"}:
            raise release.urllib.error.HTTPError(
                "https://pypi.org", int(registry), "status", {}, None
            )
        return io.StringIO(
            json.dumps({"urls": [] if registry == "deleted-files" else [{}]})
        )

    monkeypatch.setattr(release.urllib.request, "urlopen", fetch)
    if registry == "404":
        release.require_unpublished("6.0.0")
    else:
        with pytest.raises(ValueError):
            release.require_unpublished("6.0.0")


def test_ci_scopes_country_access_and_preserves_guard_receipts():
    import yaml

    candidate_job = yaml.safe_load(
        (ROOT / ".github/workflows/pr_code_changes.yaml").read_text()
    )["jobs"]["NumericalCandidate"]
    token = next(
        step for step in candidate_job["steps"] if step.get("id") == "country-token"
    )
    assert token["with"]["repositories"] == "policyengine-us"
    assert token["with"]["owner"] == "PolicyEngine"
    assert token["with"]["permission-actions"] == "read"
    assert "vars.RELEASE_COUNTRY_CANDIDATE_ARTIFACT_ID != ''" in candidate_job["if"]
    assert "matrix" not in candidate_job["if"]
    assert set(key for key in token["with"] if key.startswith("permission-")) == {
        "permission-actions"
    }
    push = yaml.safe_load((ROOT / ".github/workflows/push.yaml").read_text())["jobs"]
    steps = push["Versioning"]["steps"]
    upload = next(
        i for i, step in enumerate(steps) if "upload-artifact@" in step.get("uses", "")
    )
    commit = next(
        i for i, step in enumerate(steps) if "add-and-commit@" in step.get("uses", "")
    )
    assert upload < commit
    assert steps[commit]["with"]["add"] == "-u ."
    publishing = push["Publish"]["steps"]
    tag = next(
        i
        for i, step in enumerate(publishing)
        if "publish-git-tag.sh" in step.get("run", "")
    )
    registry = next(
        i
        for i, step in enumerate(publishing)
        if "gh-action-pypi-publish@" in step.get("uses", "")
    )
    assert "require-unpublished" in publishing[tag]["run"]
    assert "require-unpublished" in publishing[registry - 1]["run"]
    assert publishing[registry]["with"]["skip-existing"] is False
    setup = yaml.safe_load(
        (ROOT / ".github/actions/release-toolchain/action.yml").read_text()
    )
    for step in setup["runs"]["steps"]:
        if "uses" in step:
            assert release.re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])


def test_source_origin_rejects_previously_imported_other_checkout(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("POLICYENGINE_SKIP_COUNTRY_IMPORTS", "1")
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    actual = release.assert_source_origin(ROOT)
    assert actual["resources"] == "src/policyengine"
    assert actual["modules"]["policyengine.provenance.trace"].startswith(
        "src/policyengine/"
    )
    monkeypatch.syspath_prepend(str(tmp_path / "src"))
    with pytest.raises(ValueError, match="source origin"):
        release.assert_source_origin(tmp_path)


@pytest.mark.parametrize(
    "member", ["manifest.json", "us.trace.tro.jsonld", "uk.trace.tro.jsonld"]
)
def test_actual_wheel_must_contain_all_three_verified_provenance_members(member):
    receipt = {
        "package_identity": {
            "bundle_manifest_sha256": "a" * 64,
            "tro_sha256": {"us": "b" * 64, "uk": "c" * 64},
        },
        "wheel": {
            "members": {
                "policyengine/data/bundle/" + name: {"sha256": digest * 64}
                for name, digest in [
                    ("manifest.json", "a"),
                    ("us.trace.tro.jsonld", "b"),
                    ("uk.trace.tro.jsonld", "c"),
                ]
            }
        },
    }
    release.verify_wheel_package_identity(receipt)
    receipt["wheel"]["members"]["policyengine/data/bundle/" + member]["sha256"] = (
        "d" * 64
    )
    with pytest.raises(ValueError, match="Built wheel"):
        release.verify_wheel_package_identity(receipt)


def test_candidate_uk_uses_ordinary_builder_and_never_requests_us(monkeypatch):
    from policyengine.provenance import manifest, trace
    from tests.test_certify_data_release import _uk_release_manifest_payload

    bundle_bytes = (ROOT / release.BUNDLE_PATH).read_bytes()
    country = manifest.CountryReleaseManifest.model_validate(
        json.loads(bundle_bytes)["data_releases"]["uk"]
    )
    country.source_sha256 = hashlib.sha256(bundle_bytes).hexdigest()
    data = manifest.DataReleaseManifest.model_validate(_uk_release_manifest_payload())
    calls = []

    def get_country(name):
        calls.append(("country", name))
        assert name == "uk"
        return country

    def get_data(name):
        calls.append(("data", name))
        assert name == "uk"
        return data

    monkeypatch.setattr(manifest, "get_release_manifest", get_country)
    monkeypatch.setattr(manifest, "get_data_release_manifest", get_data)
    actual = release.candidate_uk_tro()
    expected = trace.build_trace_tro_from_release_bundle(
        country,
        data,
        certification=country.certification,
        model_wheel_sha256=country.model_package.sha256,
        model_wheel_url=country.model_package.wheel_url,
        emission_context={"pe:emittedIn": "repository-bundle"},
    )
    assert actual == expected
    assert calls == [("country", "uk"), ("data", "uk")]
    artifacts = actual["@graph"][0]["trov:hasComposition"]["trov:hasArtifact"]
    assert [
        item["trov:sha256"]
        for item in artifacts
        if item["@id"] == "composition/1/artifact/bundle_manifest"
    ] == [country.source_sha256]
