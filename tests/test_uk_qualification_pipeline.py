"""Orchestration of UK candidate qualification (no network).

Invariants:

- resolution keeps the certified core when the model accepts it and never
  picks a prerelease, yanked or unpublished version;
- the decision never qualifies a pair main already certifies or one main
  supersedes, and never repeats a terminal attempt;
- rewriting the certified-version test constants leaves no old value behind
  and touches only quoted literals;
- the replay request built for a candidate is valid against the scorecard's
  vendored schema and binds the candidate commit, wheels and dataset;
- promotion planning readies only the selected target and closes exactly the
  candidates it or main supersede.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from policyengine.provenance.qualification import ReplayStatus
from policyengine.provenance.qualification_ledger import write_json
from policyengine.provenance.uk_qualification import (
    accept_review,
    assemble_receipt,
    build_replay_request,
    candidate_action,
    candidate_branch,
    certified_constant_replacements,
    choose_core_version,
    core_requirement,
    latest_data_release,
    plan_promotion,
    read_replay,
    resolve_candidate,
    rewrite_certified_constants,
)
from tests.qualification_fixtures import (
    HARNESS,
    ISSUED,
    VENDORED_SCHEMAS,
    gates,
    golden,
    make_pair,
    make_receipt,
    sha,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE = json.loads(
    (REPO_ROOT / "src/policyengine/data/bundle/manifest.json").read_text()
)


def _wheel(name, version, digest):
    return {
        "packagetype": "bdist_wheel",
        "filename": f"{name.replace('-', '_')}-{version}-py3-none-any.whl",
        "url": f"https://files.pythonhosted.org/packages/{name}-{version}.whl",
        "digests": {"sha256": digest},
    }


MANIFEST = {
    "schema_version": 1,
    "data_package": {"name": "policyengine-uk-data", "version": "1.58.0"},
    "default_datasets": {"national": "enhanced_frs_2024_25"},
    "build": {"build_id": "policyengine-uk-data-1.58.0"},
    "artifacts": {
        "enhanced_frs_2024_25": {
            "kind": "microdata",
            "path": "enhanced_frs_2024_25.h5",
            "repo_id": "policyengine/policyengine-uk-data-private",
            "revision": "1.58.0",
            "sha256": "d" * 64,
            "size_bytes": 128369110,
        }
    },
}


def _resolver(**overrides):
    projects = {
        "policyengine-uk": {
            "releases": {
                "2.126.6": [_wheel("policyengine-uk", "2.126.6", "1" * 64)],
                "2.126.8": [_wheel("policyengine-uk", "2.126.8", "2" * 64)],
                "2.127.0rc1": [_wheel("policyengine-uk", "2.127.0rc1", "3" * 64)],
                "2.127.1": [
                    {**_wheel("policyengine-uk", "2.127.1", "4" * 64), "yanked": True}
                ],
            }
        },
        "policyengine-uk/2.126.8": {
            "info": {"requires_dist": ["policyengine-core>=3.32.27"]}
        },
        "policyengine-uk/2.126.6": {
            "info": {"requires_dist": ["policyengine-core>=3.34.0"]}
        },
        "policyengine-core": {
            "releases": {
                v: [_wheel("policyengine-core", v, v.replace(".", "")[0] * 64)]
                for v in ("3.33.0", "3.34.0", "3.34.1", "3.35.0rc1")
            }
        },
    }
    manifest_bytes = json.dumps(MANIFEST).encode()
    kwargs = dict(
        current_core="3.33.0",
        pypi_project=lambda path: projects[path],
        hf_revision_sha=lambda repo, rev: "f" * 40,
        hf_tags=lambda repo: ["1.57.4", "1.58.0", "v1.11.1", "version_a"],
        hf_file=lambda repo, rev, path: manifest_bytes,
    )
    kwargs.update(overrides)
    return resolve_candidate(**kwargs), manifest_bytes


def test_resolution_picks_newest_stable_and_keeps_an_accepted_core():
    resolved, manifest_bytes = _resolver()
    pair = resolved.pair
    assert pair.model.version == "2.126.8"
    assert pair.model.wheel_sha256 == "2" * 64
    assert pair.core.version == "3.33.0"
    assert pair.data.release_version == "1.58.0"
    assert pair.data.release_manifest_revision == "f" * 40
    assert (
        pair.data.release_manifest_sha256 == hashlib.sha256(manifest_bytes).hexdigest()
    )
    assert resolved.manifest_uri.startswith(
        "hf://model/policyengine/policyengine-uk-data-private@"
    )


def test_resolution_moves_core_only_when_the_model_requires_it():
    resolved, _ = _resolver(model_version="2.126.6")
    assert resolved.pair.core.version == "3.34.1"


def test_core_requirement_and_choice():
    assert (
        core_requirement(["numpy>=1", "policyengine_core>=3.32.27,<4"])
        == "<4,>=3.32.27"
    )
    with pytest.raises(ValueError):
        core_requirement(["numpy"])
    with pytest.raises(ValueError):
        choose_core_version("3.33.0", ">=9", [])


def test_latest_data_release_ignores_non_version_tags():
    assert latest_data_release(["1.57.4", "1.58.0", "v1.11.1", "version_a"]) == "1.58.0"


def test_resolution_refuses_unpublished_versions():
    with pytest.raises(ValueError):
        _resolver(model_version="9.9.9")


def test_actions(tmp_path):
    current = BUNDLE["data_releases"]["uk"]
    certified = make_pair(
        model=current["model_package"]["version"],
        data=current["data_package"]["version"],
        core=BUNDLE["packages"]["policyengine-core"]["version"],
        dataset_sha=current["certified_data_artifact"]["sha256"],
    )
    assert (
        candidate_action(certified, BUNDLE, tmp_path, base_commit="a" * 40)[0]
        == "already_certified"
    )
    older = make_pair(model="2.100.0", data="1.50.0", core="3.30.0")
    assert candidate_action(older, BUNDLE, tmp_path, base_commit="a" * 40)[0] == "stale"
    newer = make_pair(model="2.200.0", data="1.58.0", core="3.33.0")
    assert (
        candidate_action(newer, BUNDLE, tmp_path, base_commit="a" * 40)[0] == "qualify"
    )
    rejected = make_receipt(pair=newer, gate_results=gates(wheel_hashes="fail"))
    write_json(
        tmp_path / "uk" / newer.pair_id / "qualification_receipt.json",
        rejected.canonical_payload(),
    )
    assert (
        candidate_action(newer, BUNDLE, tmp_path, base_commit="a" * 40)[0]
        == "duplicate"
    )
    assert (
        candidate_action(newer, BUNDLE, tmp_path, base_commit="a" * 40, force=True)[0]
        == "qualify"
    )


def test_incomplete_pairs_requalify_on_a_new_base_only(tmp_path):
    pair = make_pair(model="2.200.0")
    incomplete = make_receipt(
        pair=pair, gate_results=gates(reform_contract="unavailable")
    )
    write_json(
        tmp_path / "uk" / pair.pair_id / "qualification_receipt.json",
        incomplete.canonical_payload(),
    )
    (tmp_path / "uk" / pair.pair_id / "attempts" / ("a" * 12)).mkdir(parents=True)
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit="a" * 40)[0] == "duplicate"
    )
    assert (
        candidate_action(pair, BUNDLE, tmp_path, base_commit="b" * 40)[0] == "qualify"
    )


def _new_record(old):
    new = json.loads(json.dumps(old))
    new["model_package"]["version"] = "2.126.8"
    new["certification"]["built_with_model_version"] = "2.126.0"
    new["certification"]["data_build_id"] = "policyengine-uk-data-1.59.0"
    new["data_package"]["version"] = "1.59.0"
    new["data_package"]["release_manifest_revision"] = "1" * 40
    return new


def test_constant_rewrite_leaves_no_old_values(tmp_path):
    for relative in (
        "tests/test_models.py",
        "tests/test_release_manifests.py",
        "tests/test_uk_regions.py",
    ):
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / relative, tmp_path / relative)
    old = BUNDLE["data_releases"]["uk"]
    new = _new_record(old)
    replacements = certified_constant_replacements(old, new)
    changed = rewrite_certified_constants(tmp_path, replacements)
    assert set(changed) == {
        "tests/test_models.py",
        "tests/test_release_manifests.py",
        "tests/test_uk_regions.py",
    }
    for relative in changed:
        text = (tmp_path / relative).read_text()
        for before, after in replacements:
            assert f'"{before}"' not in text and f'@{before}"' not in text
    manifests = (tmp_path / "tests/test_release_manifests.py").read_text()
    assert 'UK_MODEL_VERSION = "2.126.8"' in manifests
    assert 'UK_DATA_RELEASE_PATH = "releases/1.59.0/release_manifest.json"' in manifests
    assert 'UK_DATA_RELEASE_REVISION = "' + "1" * 40 + '"' in manifests
    assert rewrite_certified_constants(tmp_path, replacements) == []


@pytest.mark.parametrize("qualification_only", [False, True])
def test_preparation_generates_new_sidecars_and_verifies_the_exact_pair(
    tmp_path, monkeypatch, qualification_only
):
    """Run preparation, certification and real TRO generation without a network."""

    from policyengine.provenance import certification, manifest
    from policyengine.provenance.uk_qualification import prepare_candidate_commit

    monkeypatch.syspath_prepend(str(REPO_ROOT / "scripts"))
    import bundle as maintenance
    import certify_data_release as certify_script
    import generate_bundle_artifacts as artifacts
    import generate_trace_tros as tros

    release = json.loads(json.dumps(MANIFEST))
    release["build"].update(
        built_with_model_package={
            "name": "policyengine-uk",
            "version": "2.100.0" if qualification_only else "2.126.8",
        },
        built_with_core_package={
            "name": "policyengine-core",
            "version": "3.0.0" if qualification_only else "3.33.0",
        },
    )
    release_bytes = json.dumps(release).encode()
    resolved, _ = _resolver(hf_file=lambda *args: release_bytes)
    pair = resolved.pair
    bundle_dir = tmp_path / "src/policyengine/data/bundle"
    bundle_dir.mkdir(parents=True)
    source = json.loads(json.dumps(BUNDLE))
    source["data_releases"].pop("us")
    source["packages"].pop("policyengine-us")
    for packages in source["extras"].values():
        if "policyengine-us" in packages:
            packages.remove("policyengine-us")
    bundle_path = bundle_dir / "manifest.json"
    write_json(bundle_path, source)
    sidecar = bundle_dir / "uk.trace.tro.jsonld"
    old_sidecar = (
        REPO_ROOT / "src/policyengine/data/bundle/uk.trace.tro.jsonld"
    ).read_bytes()
    sidecar.write_bytes(old_sidecar)
    shutil.copy(REPO_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    (tmp_path / "changelog.d").mkdir()
    for name in ("test_models.py", "test_release_manifests.py", "test_uk_regions.py"):
        (tmp_path / "tests").mkdir(exist_ok=True)
        shutil.copy(REPO_ROOT / "tests" / name, tmp_path / "tests" / name)

    def country_manifest(country):
        assert country == "uk"
        result = manifest.CountryReleaseManifest.model_validate(
            json.loads(bundle_path.read_text())["data_releases"][country]
        )
        result.source_sha256 = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
        return result

    def data_manifest(country=None):
        result = manifest.DataReleaseManifest.model_validate_json(release_bytes)
        result.source_sha256 = hashlib.sha256(release_bytes).hexdigest()
        return result

    monkeypatch.setattr(certify_script, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(maintenance, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(artifacts, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(artifacts, "BUNDLE_MANIFEST", bundle_path)
    monkeypatch.setattr(artifacts, "PYPROJECT", tmp_path / "pyproject.toml")
    load_bundle = artifacts.load_bundle_manifest
    monkeypatch.setattr(
        artifacts, "load_bundle_manifest", lambda path=bundle_path: load_bundle(path)
    )
    monkeypatch.setattr(tros, "BUNDLE_MANIFEST", bundle_path)
    monkeypatch.setattr(tros, "BUNDLE_TRO_DIR", bundle_dir)
    monkeypatch.setattr(tros, "BUNDLE_LOCK", tmp_path / "uv.lock")
    monkeypatch.setattr(tros, "get_release_manifest", country_manifest)
    monkeypatch.setattr(tros, "get_data_release_manifest", data_manifest)
    monkeypatch.setattr(
        certification,
        "fetch_release_manifest",
        lambda uri, **kw: (
            data_manifest(),
            pair.data.release_manifest_sha256,
            certification.parse_manifest_uri(uri),
        ),
    )
    monkeypatch.setattr(
        certification,
        "fetch_pypi_wheel_metadata",
        lambda *args: {
            "sha256": pair.model.wheel_sha256,
            "url": resolved.model_wheel.url,
        },
    )
    monkeypatch.setattr(certification, "head_artifact", lambda *args, **kw: True)
    monkeypatch.setattr(
        certification, "required_supplemental_release_files", lambda *args: []
    )
    calls = []

    def run(command, *, cwd, env=None):
        calls.append(command)
        assert cwd == tmp_path
        if command[1] == "scripts/bundle.py":
            assert maintenance.main(command[2:]) == 0
        elif command[:2] == ["uv", "lock"]:
            (tmp_path / "uv.lock").write_text(
                "[[package]]\n"
                'name = "policyengine-uk"\n'
                f'version = "{pair.model.version}"\n'
                'source = { registry = "https://pypi.org/simple" }\n'
                f'wheels = [{{url = "{resolved.model_wheel.url}", hash = "sha256:{pair.model.wheel_sha256}"}}]\n'
            )
        else:
            assert command[1] == "scripts/release_lock.py"
        return subprocess.CompletedProcess(command, 0)

    prepared = prepare_candidate_commit(
        tmp_path, resolved, python=sys.executable, run=run, refresh_snapshots=False
    )
    assert sidecar.read_bytes() != old_sidecar
    assert pair.data.release_manifest_sha256.encode() in sidecar.read_bytes()
    assert prepared["compatibility_basis"] == (
        "qualified_exact_pair" if qualification_only else "built_with_model_package"
    )
    assert (tmp_path / prepared["changelog_fragment"]).is_file()
    assert maintenance.main(["check", "--include-tros", "--strict-tros"]) == 0
    assert calls[-1][2:] == ["check", "--include-tros", "--strict-tros"]
    if qualification_only:
        changed = json.loads(bundle_path.read_bytes())
        changed["packages"]["policyengine-core"]["version"] = "99.0.0"
        write_json(bundle_path, changed)
        with pytest.raises(ValueError, match="runtime core.*qualified exact pair"):
            tros.generated_tros(strict=True)


def test_replay_request_is_valid_for_the_scorecard():
    pair = make_pair()
    release_bundle = dict(
        golden("qualification_request_golden")["candidate"]["expected_release_bundle"]
    )
    request = build_replay_request(
        pair, HARNESS, release_bundle=release_bundle, issued_by=ISSUED
    )
    schema = json.loads(
        (VENDORED_SCHEMAS / "qualification_request.v1.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(request.document())
    candidate = request.document()["candidate"]
    assert candidate["policyengine"]["source"] == {
        "git": {
            "repository": "PolicyEngine/policyengine.py",
            "commit": HARNESS.git_commit,
        }
    }
    assert candidate["policyengine_uk"]["wheel_sha256"] == pair.model.wheel_sha256
    assert candidate["data"]["sha256"] == pair.data.dataset_sha256
    assert request.document()["requested_by"]["pair_id"] == pair.pair_id
    again = build_replay_request(
        pair, HARNESS, release_bundle=release_bundle, issued_by=ISSUED
    )
    assert again.request_id == request.request_id


def test_the_real_cli_generates_replay_requests_despite_country_import_suppression(
    tmp_path,
):
    """The real CLI can read the UK certificate despite automatic import suppression."""

    from importlib.util import find_spec

    if find_spec("policyengine_uk") is None:
        pytest.skip("Replay request generation requires the installed UK model")
    attempt = tmp_path / "attempt"
    write_json(attempt / "candidate.json", {"pair": make_pair().canonical_payload()})
    write_json(attempt / "harness.json", HARNESS.canonical_payload())
    env = dict(os.environ)
    env["POLICYENGINE_SKIP_COUNTRY_IMPORTS"] = "1"
    env.pop("GITHUB_OUTPUT", None)
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/check_uk_candidate.py"),
            "request-replay",
            "--attempt",
            str(attempt),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    request = json.loads((attempt / "replay/request.json").read_text())
    schema = json.loads(
        (VENDORED_SCHEMAS / "qualification_request.v1.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(request)
    candidate = request["candidate"]
    assert candidate["policyengine"]["source"]["git"]["commit"] == HARNESS.git_commit
    bundle = candidate["expected_release_bundle"]
    record = BUNDLE["data_releases"]["uk"]
    assert bundle["model_version"] == record["model_package"]["version"]
    assert bundle["data_version"] == record["data_package"]["version"]
    assert bundle["default_dataset"] == record["default_dataset"]


def test_reading_replay_state():
    pair = make_pair()
    request = build_replay_request(
        pair,
        HARNESS,
        release_bundle=golden("qualification_request_golden")["candidate"][
            "expected_release_bundle"
        ],
        issued_by=ISSUED,
    )
    gate, status, receipt = read_replay(
        request, fetch=lambda ref, path: None, state_ref="replay-state"
    )
    assert gate.status == "unavailable" and status is None
    running = ReplayStatus.model_validate(
        {
            "schema": "policyengine.uk-replay-status/v1",
            "request_id": request.request_id,
            "status": "running",
            "history": [
                {
                    "status": "running",
                    "at": "2026-10-15T10:00:00Z",
                    "run_url": "https://github.com/PolicyEngine/policyengine-scorecard/actions/runs/3",
                }
            ],
        }
    ).document()
    gate, status, _ = read_replay(
        request,
        fetch=lambda ref, path: (
            json.dumps(running).encode() if path.endswith("STATUS.json") else None
        ),
        state_ref="replay-state",
    )
    assert gate.status == "unavailable" and status.status == "running"
    terminal = {
        **running,
        "status": "complete",
        "receipt_sha256": "a" * 64,
        "receipt_commit": "c" * 40,
    }
    gate, _, _ = read_replay(
        request,
        fetch=lambda ref, path: (
            json.dumps(terminal).encode() if path.endswith("STATUS.json") else None
        ),
        state_ref="replay-state",
    )
    assert gate.status == "fail" and "no REPLAY_RECEIPT.json" in gate.summary


def test_assembled_receipt_without_replay_is_incomplete():
    pair = make_pair()
    local = [gate for gate in gates() if gate.gate_id != "replay"]
    receipt = assemble_receipt(
        pair,
        HARNESS,
        local,
        issued_by=ISSUED,
        completed_at="2026-10-15T10:00:00Z",
        previous=None,
        replay=None,
    )
    assert receipt.verdict == "incomplete"
    assert [gate.gate_id for gate in receipt.gates] == [gate.gate_id for gate in local]


def test_acceptance_is_bound_to_the_receipt():
    receipt = make_receipt(gate_results=gates(metrics_review="needs_review"))
    with pytest.raises(ValueError):
        accept_review(
            receipt,
            reviewer="maria",
            accepted_receipt_sha256=sha("1"),
            explanation="x",
            accepted_at="t",
        )
    reviewed = accept_review(
        receipt,
        reviewer="maria",
        accepted_receipt_sha256=receipt.unreviewed_sha256,
        explanation="Council tax move follows the 2025-26 band revaluation in uk-data.",
        accepted_at="2026-10-16T09:00:00Z",
    )
    assert reviewed.promotable
    with pytest.raises(ValueError):
        accept_review(
            make_receipt(),
            reviewer="m",
            accepted_receipt_sha256=sha("1"),
            explanation="x",
            accepted_at="t",
        )


def test_promotion_plan():
    current = (
        BUNDLE["data_releases"]["uk"]["model_package"]["version"],
        BUNDLE["data_releases"]["uk"]["data_package"]["version"],
        BUNDLE["packages"]["policyengine-core"]["version"],
    )
    newest = make_receipt(
        pair=make_pair(model="2.200.0", data=current[1], core=current[2])
    )
    older = make_receipt(
        pair=make_pair(model="2.199.0", data=current[1], core=current[2])
    )
    rejected = make_receipt(
        pair=make_pair(model="2.201.0", data=current[1], core=current[2]),
        gate_results=gates(replay="fail"),
    )
    stale = make_receipt(pair=make_pair(model="2.0.0", data="1.0.0", core="3.0.0"))
    branches = {
        candidate_branch(r.pair): r.harness.git_commit
        for r in (newest, older, rejected, stale)
    }
    branches["candidate/uk/unknown"] = "0" * 40
    plan = plan_promotion([newest, older, rejected, stale], BUNDLE, branches)
    assert plan.target == newest
    assert plan.ready_branch == candidate_branch(newest.pair)
    assert plan.ready_commit == newest.harness.git_commit
    assert plan.close_branches == sorted(
        [candidate_branch(older.pair), candidate_branch(stale.pair)]
    )
    assert candidate_branch(rejected.pair) not in plan.close_branches


def _promotable_pair_and_branch(core=None):
    current = BUNDLE["data_releases"]["uk"]["data_package"]["version"]
    core = core or BUNDLE["packages"]["policyengine-core"]["version"]
    return make_pair(model="2.200.0", data=current, core=core)


def test_pairs_that_share_versions_never_share_a_branch():
    """Interrupted review of #574: a qualified pair readied the branch of an
    incomplete pair with the same model and data but another core."""

    qualified_pair = _promotable_pair_and_branch()
    other_core = _promotable_pair_and_branch(core="3.99.0")
    assert qualified_pair.pair_id != other_core.pair_id
    assert candidate_branch(qualified_pair) != candidate_branch(other_core)
    assert qualified_pair.pair_id[:12] in candidate_branch(qualified_pair)
    qualified = make_receipt(pair=qualified_pair)
    incomplete = make_receipt(pair=other_core, gate_results=gates(replay="unavailable"))
    plan = plan_promotion(
        [qualified, incomplete],
        BUNDLE,
        {candidate_branch(other_core): incomplete.harness.git_commit},
    )
    assert plan.target == qualified
    assert plan.ready_branch is None
    assert "has no open pull request" in plan.reason


def test_a_branch_that_moved_off_the_qualified_commit_is_not_promoted():
    """The replayed and tested commit must be the promoted commit."""

    qualified = make_receipt(pair=_promotable_pair_and_branch())
    branch = candidate_branch(qualified.pair)
    plan = plan_promotion([qualified], BUNDLE, {branch: "f" * 40})
    assert plan.target == qualified and plan.ready_branch is None
    assert "not the qualified commit" in plan.reason
    plan = plan_promotion([qualified], BUNDLE, {branch: qualified.harness.git_commit})
    assert plan.ready_branch == branch


def test_promote_readies_and_merges_only_the_qualified_commit(monkeypatch, tmp_path):
    import argparse
    import importlib.util

    qualified = make_receipt(pair=_promotable_pair_and_branch())
    branch = candidate_branch(qualified.pair)
    spec = importlib.util.spec_from_file_location(
        "check_uk_candidate_for_test",
        Path(__file__).resolve().parents[1] / "scripts" / "check_uk_candidate.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    calls = []
    monkeypatch.setattr(cli, "latest_receipts", lambda root: [qualified])
    monkeypatch.setattr(
        cli, "subprocess", SimpleNamespace(run=lambda argv, **k: calls.append(argv))
    )
    monkeypatch.setattr(cli, "config", lambda: {"promotion": {"automatic": True}})
    monkeypatch.setattr(cli, "_open_candidate_branches", lambda: {branch: "f" * 40})
    assert cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True)) == 0
    assert calls == []
    monkeypatch.setattr(
        cli,
        "_open_candidate_branches",
        lambda: {branch: qualified.harness.git_commit},
    )
    assert cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True)) == 0
    assert calls[0][:3] == ["gh", "pr", "ready"] and calls[0][3] == branch
    assert calls[1][-2:] == ["--match-head-commit", qualified.harness.git_commit]


def test_a_forced_rerun_stages_a_new_attempt(tmp_path):
    """Interrupted review of #574: a forced run reused the existing attempt key,
    so the workflow's duplicate guard stopped it."""

    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import attempt_key

    pair = _promotable_pair_and_branch()
    base = "a" * 40
    assert attempt_key(pair, tmp_path, base_commit=base, force=True) == base[:12]
    attempt_directory(tmp_path, "uk", pair.pair_id, base[:12]).mkdir(parents=True)
    assert attempt_key(pair, tmp_path, base_commit=base) == base[:12]
    assert attempt_key(pair, tmp_path, base_commit=base, force=True) == f"{base[:12]}-2"
    attempt_directory(tmp_path, "uk", pair.pair_id, f"{base[:12]}-2").mkdir(
        parents=True
    )
    assert attempt_key(pair, tmp_path, base_commit=base, force=True) == f"{base[:12]}-3"


@pytest.mark.parametrize(
    ("pr_state", "reset_fails"),
    [("ready", False), ("draft", False), ("absent", False), ("ready", True)],
)
def test_the_workflow_drafts_existing_prs_before_replacing_their_head(
    tmp_path, pr_state, reset_fails
):
    """Execute the workflow shell with local gh/git stand-ins and no remote writes."""

    import yaml

    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/certify-uk-release.yaml").read_text()
    )
    step = next(
        step
        for step in workflow["jobs"]["prepare"]["steps"]
        if step.get("name") == "Commit and push the candidate commit"
    )
    state_path = tmp_path / "pr-state.json"
    state_path.write_text(json.dumps({"status": pr_state}))
    log_path = tmp_path / "commands.jsonl"
    fake = f"""#!{sys.executable}
import json
import os
import sys
from pathlib import Path

command = Path(sys.argv[0]).name
args = sys.argv[1:]
state_path = Path(os.environ["PR_STATE"])
state = json.loads(state_path.read_text())
with Path(os.environ["COMMAND_LOG"]).open("a") as log:
    log.write(json.dumps([command, *args]) + "\\n")
if command == "gh" and args[:2] == ["pr", "list"]:
    if state["status"] == "ready":
        print("574")
elif command == "gh" and args[:2] == ["pr", "ready"]:
    assert args[2:] == ["574", "--undo"]
    if os.environ["RESET_FAILS"] == "1":
        sys.exit(42)
    state["status"] = "draft"
    state_path.write_text(json.dumps(state))
elif command == "git" and args[0] == "push":
    if state["status"] == "ready":
        sys.exit(91)
"""
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    for command in ("gh", "git"):
        executable = binary_dir / command
        executable.write_text(fake)
        executable.chmod(0o755)
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{binary_dir}{os.pathsep}{os.environ['PATH']}",
            "BRANCH": "candidate/uk/2.126.8-1.58.0",
            "PAIR_ID": "a" * 64,
            "GH_TOKEN": "local-workflow-test",
            "PR_STATE": str(state_path),
            "COMMAND_LOG": str(log_path),
            "RESET_FAILS": "1" if reset_fails else "0",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    commands = [json.loads(line) for line in log_path.read_text().splitlines()]
    pushes = [i for i, command in enumerate(commands) if command[:2] == ["git", "push"]]
    resets = [
        i for i, command in enumerate(commands) if command[:3] == ["gh", "pr", "ready"]
    ]
    if reset_fails:
        assert result.returncode == 42, result.stdout + result.stderr
        assert not pushes
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(pushes) == 1
        if pr_state == "ready":
            assert len(resets) == 1 and resets[0] < pushes[0]
            assert json.loads(state_path.read_text())["status"] == "draft"
        else:
            assert not resets
    assert step["env"]["GH_TOKEN"] == "${{ steps.app-token.outputs.token }}"


# --- Attempt lifecycle -----------------------------------------------------------------


def test_attempt_lifecycle(tmp_path):
    from policyengine.provenance.qualification import GateResult
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        attempt_is_waiting_for_replay,
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    attempt = attempt_directory(tmp_path, "uk", pair.pair_id, "abcdef123456")
    stage_attempt(
        attempt,
        {
            "pair": pair.canonical_payload(),
            "pair_id": pair.pair_id,
            "previous_certificate": None,
        },
        HARNESS,
    )
    local = [gate for gate in gates() if gate.gate_id != "replay"]
    write_gate_results(attempt, local, {gate.gate_id: {"ok": True} for gate in local})
    assert not attempt_is_waiting_for_replay(attempt)
    receipt = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    assert receipt.verdict == "incomplete"  # the replay never ran
    assert (
        read_json(tmp_path / "uk" / pair.pair_id / "qualification_receipt.json")[
            "verdict"
        ]
        == "incomplete"
    )

    request = build_replay_request(
        pair,
        HARNESS,
        release_bundle=golden("qualification_request_golden")["candidate"][
            "expected_release_bundle"
        ],
        issued_by=ISSUED,
    )
    write_json(attempt / "replay" / "request.json", request.document())
    assert attempt_is_waiting_for_replay(attempt)
    write_json(
        attempt / "replay" / "replay.result.json",
        GateResult(gate_id="replay", status="pass", summary="ok").canonical_payload(),
    )
    assert not attempt_is_waiting_for_replay(attempt)
    final = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert final.verdict == "qualified"
    assert final.replay.request_id == request.request_id
    assert (attempt / "receipts" / f"{receipt.receipt_sha256}.json").is_file()
    assert (attempt / "receipts" / f"{final.receipt_sha256}.json").is_file()
    assert (
        read_json(attempt / "receipts" / f"{receipt.receipt_sha256}.json")
        == receipt.canonical_payload()
    )


def test_older_attempt_finalization_preserves_latest_staged_attempt(tmp_path):
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    # The staging order deliberately differs from directory/commit order.
    older = attempt_directory(tmp_path, "uk", pair.pair_id, "ffffffffffff")
    newer = attempt_directory(tmp_path, "uk", pair.pair_id, "aaaaaaaaaaaa")
    payload = {"pair": pair.canonical_payload(), "previous_certificate": None}
    stage_attempt(older, payload, HARNESS)
    newer_harness = HARNESS.model_copy(update={"git_commit": "a" * 40})
    stage_attempt(newer, payload, newer_harness)
    for attempt in (older, newer):
        write_gate_results(attempt, gates(), {})
    newest = finalize_attempt(
        newer, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    old = finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    latest = read_json(tmp_path / "uk" / pair.pair_id / "qualification_receipt.json")
    assert latest == newest.canonical_payload()
    assert read_json(older / "qualification_receipt.json") == old.canonical_payload()
    assert read_json(newer / "qualification_receipt.json") == newest.canonical_payload()


def test_terminal_attempt_receipt_is_immutable_and_finalization_is_idempotent(tmp_path):
    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    attempt = attempt_directory(tmp_path, "uk", pair.pair_id, "abcdef123456")
    stage_attempt(attempt, {"pair": pair.canonical_payload()}, HARNESS)
    write_gate_results(attempt, gates(), {})
    original = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    original_bytes = (attempt / "qualification_receipt.json").read_bytes()
    write_gate_results(attempt, gates(replay="fail"), {})
    repeated = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert repeated == original
    assert (attempt / "qualification_receipt.json").read_bytes() == original_bytes


def test_new_staged_attempt_advances_a_legacy_latest_receipt(tmp_path):
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    legacy = make_receipt()
    latest_path = tmp_path / "uk" / legacy.pair_id / "qualification_receipt.json"
    write_json(latest_path, legacy.canonical_payload())
    attempt = attempt_directory(tmp_path, "uk", legacy.pair_id, "new-attempt")
    stage_attempt(attempt, {"pair": legacy.pair.canonical_payload()}, HARNESS)
    write_gate_results(attempt, gates(), {})
    current = finalize_attempt(
        attempt, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert read_json(latest_path) == current.canonical_payload()


@pytest.mark.parametrize(
    "interrupted", ["missing", "older", "missing-pointer", "missing-receipt"]
)
def test_terminal_finalization_repairs_interrupted_latest_publication(
    tmp_path, interrupted
):
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    payload = {"pair": pair.canonical_payload()}
    older = attempt_directory(tmp_path, "uk", pair.pair_id, "older")
    stage_attempt(older, payload, HARNESS)
    write_gate_results(older, gates(), {})
    old_receipt = finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T09:00:00Z"
    )
    current = attempt_directory(tmp_path, "uk", pair.pair_id, "newer")
    stage_attempt(current, payload, HARNESS.model_copy(update={"git_commit": "a" * 40}))
    write_gate_results(current, gates(), {})
    receipt = finalize_attempt(
        current, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    original_bytes = (current / "qualification_receipt.json").read_bytes()
    pair_dir = tmp_path / "uk" / pair.pair_id
    latest = pair_dir / "qualification_receipt.json"
    pointer = pair_dir / "latest_attempt.json"
    if interrupted == "older":
        write_json(latest, old_receipt.canonical_payload())
        write_json(pointer, {"attempt_key": "older", "sequence": 1})
    else:
        if interrupted != "missing-pointer":
            latest.unlink()
        if interrupted != "missing-receipt":
            pointer.unlink()
    repeated = finalize_attempt(
        current, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert repeated == receipt
    assert (current / "qualification_receipt.json").read_bytes() == original_bytes
    assert read_json(latest) == receipt.canonical_payload()
    assert read_json(pointer) == {"attempt_key": "newer", "sequence": 2}
    finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T12:00:00Z"
    )
    assert read_json(latest) == receipt.canonical_payload()


def test_stale_latest_pointer_cannot_replace_a_newer_incomplete_receipt(tmp_path):
    from policyengine.provenance.qualification_ledger import (
        attempt_directory,
        read_json,
    )
    from policyengine.provenance.uk_qualification import (
        finalize_attempt,
        stage_attempt,
        write_gate_results,
    )

    pair = make_pair()
    payload = {"pair": pair.canonical_payload()}
    older = attempt_directory(tmp_path, "uk", pair.pair_id, "older")
    stage_attempt(older, payload, HARNESS)
    write_gate_results(older, gates(), {})
    finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T09:00:00Z"
    )
    newer = attempt_directory(tmp_path, "uk", pair.pair_id, "newer")
    stage_attempt(newer, payload, HARNESS.model_copy(update={"git_commit": "a" * 40}))
    write_gate_results(newer, gates(replay="unavailable"), {})
    current = finalize_attempt(
        newer, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T10:00:00Z"
    )
    pair_dir = tmp_path / "uk" / pair.pair_id
    write_json(
        pair_dir / "latest_attempt.json", {"attempt_key": "older", "sequence": 1}
    )
    finalize_attempt(
        older, tmp_path, issued_by=ISSUED, completed_at="2026-10-15T11:00:00Z"
    )
    assert (
        read_json(pair_dir / "qualification_receipt.json")
        == current.canonical_payload()
    )
    assert read_json(pair_dir / "latest_attempt.json") == {
        "attempt_key": "newer",
        "sequence": 2,
    }


# --- Release dispatch ----------------------------------------------------------------


def test_release_payload_keeps_version_first_and_carries_identity():
    from policyengine.provenance.receipt import certificate_sha256
    from policyengine.provenance.uk_qualification import release_dispatch_payload

    version = BUNDLE["policyengine_version"]
    payload = release_dispatch_payload(BUNDLE, version=version)
    assert payload["event_type"] == "policyengine-release"
    body = payload["client_payload"]
    assert list(body)[0] == "version" and body["version"] == version
    uk = body["bundle"]["uk"]
    record = BUNDLE["data_releases"]["uk"]
    assert uk["model_version"] == record["model_package"]["version"]
    assert uk["dataset_sha256"] == record["certified_data_artifact"]["sha256"]
    assert uk["certificate_sha256"] == certificate_sha256(record)
    assert body["qualification"] is None  # the committed pair was not auto-qualified
    assert len(body) <= 10  # repository_dispatch limit on top-level keys
    with pytest.raises(ValueError):
        release_dispatch_payload(BUNDLE, version="0.0.0")


def test_release_payload_names_the_qualification_receipt():
    from policyengine.provenance.uk_qualification import release_dispatch_payload

    bundle = json.loads(json.dumps(BUNDLE))
    receipt = make_receipt()
    bundle["data_releases"]["uk"]["certification"].update(
        compatibility_basis="qualified_exact_pair",
        qualification_pair_id=receipt.pair_id,
    )
    payload = release_dispatch_payload(
        bundle,
        version=bundle["policyengine_version"],
        fetch_receipt=lambda country, pair_id: receipt,
    )
    assert payload["client_payload"]["qualification"] == {
        "uk": {
            "pair_id": receipt.pair_id,
            "verdict": "qualified",
            "promotable": True,
            "receipt_sha256": receipt.receipt_sha256,
        }
    }


def test_released_bundle_request_is_valid_for_the_scorecard():
    from policyengine.provenance.uk_qualification import released_bundle_request

    record = BUNDLE["data_releases"]["uk"]
    dataset = record["default_dataset"]
    manifest = {
        "schema_version": 1,
        "data_package": {
            "name": "policyengine-uk-data",
            "version": record["data_package"]["version"],
        },
        "default_datasets": {"national": dataset},
        "artifacts": {
            dataset: {
                "kind": "microdata",
                "path": record["datasets"][dataset]["path"],
                "repo_id": record["datasets"][dataset]["repo_id"],
                "revision": record["datasets"][dataset]["revision"],
                "sha256": record["datasets"][dataset]["sha256"],
                "size_bytes": 128369110,
            }
        },
    }
    core = BUNDLE["packages"]["policyengine-core"]["version"]
    request = released_bundle_request(
        BUNDLE,
        version=BUNDLE["policyengine_version"],
        wheel_sha256=sha("7"),
        packaged_manifest_sha256=sha("8"),
        release_bundle=golden("qualification_request_golden")["candidate"][
            "expected_release_bundle"
        ],
        hf_file=lambda repo, rev, path: json.dumps(manifest).encode(),
        pypi_project=lambda name: {
            "releases": {core: [_wheel("policyengine-core", core, sha("6"))]}
        },
        requested_by={
            "repository": "PolicyEngine/policyengine.py",
            "workflow_run_id": 5,
            "commit": "e" * 40,
        },
    )
    schema = json.loads(
        (VENDORED_SCHEMAS / "qualification_request.v1.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(request.document())
    assert request.kind == "released_bundle"
    assert request.document()["candidate"]["policyengine"]["source"] == {
        "pypi": {"wheel_sha256": sha("7")}
    }


def test_expected_release_bundle_uses_the_scorecard_certification_environment(
    monkeypatch, tmp_path
):
    """W6 interface point 4: no tokens, no proxy exceptions, no network."""

    from policyengine.provenance import uk_qualification

    environ = {
        "PATH": "/usr/bin",
        "HF_TOKEN": "t",
        "HUGGING_FACE_TOKEN": "t",
        "HUGGINGFACE_HUB_TOKEN": "t",
        "NO_PROXY": "huggingface.co",
        "no_proxy": "huggingface.co",
        "HTTPS_PROXY": "http://corporate:3128",
        "POLICYENGINE_SKIP_COUNTRY_IMPORTS": "1",
    }
    env = uk_qualification.certification_environment(environ)
    assert env["PATH"] == "/usr/bin"
    for name in ("HF_TOKEN", "HUGGING_FACE_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        assert name not in env
    assert "NO_PROXY" not in env and "no_proxy" not in env
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        assert env[name] == env[name.lower()] == "http://127.0.0.1:9"
    assert env["HF_HUB_OFFLINE"] == "1"

    seen = {}

    def run(args, *, cwd, env, check, capture_output, text):
        seen["env"] = env
        return type("Done", (), {"stdout": '{"policyengine_version": "6.2.6"}\n'})()

    monkeypatch.setattr(uk_qualification.subprocess, "run", run)
    monkeypatch.setattr(uk_qualification.os, "environ", environ)
    assert uk_qualification.expected_release_bundle("python", cwd=tmp_path) == {
        "policyengine_version": "6.2.6"
    }
    assert seen["env"] == env


def test_the_certification_environment_falls_back_to_the_packaged_certificate():
    """Executed: with the proxies, the manifest request fails and the bundled
    certification is used (the mechanism W6's recipe relies on)."""

    import os
    import subprocess
    import sys

    from policyengine.provenance import uk_qualification

    script = (
        "import json\n"
        "from policyengine.provenance import manifest\n"
        "try:\n"
        "    manifest.get_data_release_manifest('uk')\n"
        "    print('reached')\n"
        "except manifest.DataReleaseManifestUnavailableError:\n"
        "    print('unavailable')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=uk_qualification.certification_environment(os.environ),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.stdout.strip().splitlines()[-1] == "unavailable", result.stderr
