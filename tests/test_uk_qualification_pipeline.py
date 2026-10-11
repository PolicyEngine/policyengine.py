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
import shutil
from pathlib import Path

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
    branches = [candidate_branch(r.pair) for r in (newest, older, rejected, stale)] + [
        "candidate/uk/unknown"
    ]
    plan = plan_promotion([newest, older, rejected, stale], BUNDLE, branches)
    assert plan.target == newest
    assert plan.ready_branch == candidate_branch(newest.pair)
    assert plan.close_branches == sorted(
        [candidate_branch(older.pair), candidate_branch(stale.pair)]
    )
    assert candidate_branch(rejected.pair) not in plan.close_branches


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
