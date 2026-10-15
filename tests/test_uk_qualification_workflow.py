"""Qualification workflow readiness and failed-check refresh (no remote writes)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from policyengine.provenance.uk_qualification import (
    accept_review,
    candidate_branch,
    previous_certificate,
)
from tests.qualification_fixtures import gates, make_pair, make_receipt

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/certify-uk-release.yaml"


def _cli():
    spec = importlib.util.spec_from_file_location(
        "qualification_workflow_cli", REPO_ROOT / "scripts/check_uk_candidate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _workflow():
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def test_resolution_can_authenticate_the_staged_attempt_owner_lookup():
    resolve = _workflow()["jobs"]["resolve"]
    assert resolve["permissions"]["contents"] == "read"
    assert resolve["permissions"]["actions"] == "read"
    step = next(
        step
        for step in resolve["steps"]
        if step.get("name") == "Resolve and deduplicate the candidate"
    )
    assert step["env"]["GH_TOKEN"] == "${{ github.token }}"


@pytest.mark.parametrize("prepare_first", [False, True])
def test_head_replacement_and_readiness_share_one_serialization(
    monkeypatch, tmp_path, prepare_first
):
    """Replay a branch replacement after the real promotion's head snapshot.

    The scheduler's locks come from the workflow, and preparation executes its
    actual draft-and-push shell with command stand-ins. Different lock groups
    allow the reviewer's failing interleaving; one shared group defers it.
    """

    cli = _cli()
    workflow = _workflow()
    jobs = workflow["jobs"]
    bundle = json.loads(cli.BUNDLE_PATH.read_text())
    qualified = make_receipt(
        pair=make_pair(
            model="2.200.0",
            data=bundle["data_releases"]["uk"]["data_package"]["version"],
            core=bundle["packages"]["policyengine-core"]["version"],
        )
    ).model_copy(update={"previous_certificate": previous_certificate(bundle)})
    branch = candidate_branch(qualified.pair)
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps({"status": "ready", "head": qualified.harness.git_commit})
    )
    new_head = "f" * 40
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    fake = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
path = Path(os.environ["PR_STATE"])
state = json.loads(path.read_text())
command, args = Path(sys.argv[0]).name, sys.argv[1:]
if command == "gh" and args[:2] == ["pr", "list"]:
    if state["status"] == "ready":
        print("574")
elif command == "gh" and args[:2] == ["pr", "ready"]:
    assert args[2:] == ["574", "--undo"]
    state["status"] = "draft"
    path.write_text(json.dumps(state))
elif command == "git" and args[0] == "push":
    assert state["status"] == "draft"
    state["head"] = {new_head!r}
    path.write_text(json.dumps(state))
"""
    for command in ("gh", "git"):
        executable = binary_dir / command
        executable.write_text(fake)
        executable.chmod(0o755)
    push_step = next(
        step
        for step in jobs["prepare"]["steps"]
        if step.get("name") == "Commit and push the candidate commit"
    )
    groups = {
        job: jobs[job]["concurrency"]["group"].replace(
            "${{ needs.resolve.outputs.pair_id }}", qualified.pair_id
        )
        for job in ("prepare", "promote")
    }
    running = set()
    deferred = []
    ready_heads = []

    def prepare():
        subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", push_step["run"]],
            cwd=tmp_path,
            env={
                **os.environ,
                "PATH": f"{binary_dir}{os.pathsep}{os.environ['PATH']}",
                "BRANCH": branch,
                "PAIR_ID": qualified.pair_id,
                "PR_STATE": str(state_path),
            },
            check=True,
            capture_output=True,
            timeout=30,
        )

    def schedule(job, operation):
        if groups[job] in running:
            deferred.append((job, operation))
            return
        running.add(groups[job])
        try:
            operation()
        finally:
            running.remove(groups[job])

    def fake_run(argv, **kwargs):
        if argv[:3] == ["gh", "pr", "list"]:
            state = json.loads(state_path.read_text())
            return SimpleNamespace(
                stdout=json.dumps(
                    [{"headRefName": branch, "headRefOid": state["head"]}]
                )
            )
        assert argv[:3] == ["gh", "pr", "ready"]
        if not prepare_first:
            schedule("prepare", prepare)
        state = json.loads(state_path.read_text())
        ready_heads.append(state["head"])
        state["status"] = "ready"
        state_path.write_text(json.dumps(state))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli, "latest_receipts", lambda root, **_: [qualified])
    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=fake_run))
    monkeypatch.setattr(cli, "config", lambda: {"promotion": {"automatic": False}})
    if prepare_first:
        schedule("prepare", prepare)
    schedule(
        "promote",
        lambda: cli.cmd_promote(argparse.Namespace(ledger=str(tmp_path), apply=True)),
    )
    for job, operation in deferred:
        schedule(job, operation)
    assert all(head == qualified.harness.git_commit for head in ready_heads)
    assert json.loads(state_path.read_text()) == {"status": "draft", "head": new_head}
    assert jobs["prepare"]["concurrency"]["cancel-in-progress"] is False
    assert jobs["promote"]["concurrency"]["cancel-in-progress"] is False


@pytest.mark.parametrize("job", ["replay", "catch-up", "accept"])
def test_workflow_refreshes_failed_checks_after_publishing_receipts(job):
    workflow = _workflow()
    configured = workflow["jobs"][job]
    refresh = next(
        step
        for step in configured["steps"]
        if "refresh-pr-checks" in step.get("run", "")
    )
    assert configured["permissions"]["actions"] == "write"
    assert refresh["env"]["GH_TOKEN"] == "${{ github.token }}"
    steps = configured["steps"]
    publish_positions = [
        index
        for index, step in enumerate(steps)
        if ".github/qualification-ledger.sh publish" in step.get("run", "")
    ]
    assert publish_positions
    assert max(publish_positions) < steps.index(refresh)


def test_catch_up_dispatches_recovery_for_the_original_pair(tmp_path):
    workflow = _workflow()
    job = workflow["jobs"]["catch-up"]
    step = next(
        step for step in job["steps"] if "recoverable --ledger" in step.get("run", "")
    )
    pair = make_pair(model="2.200.0", data="1.58.9")
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps({"pair": pair.canonical_payload()}))
    command_log = tmp_path / "commands.jsonl"
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    fake = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
command, args = Path(sys.argv[0]).name, sys.argv[1:]
if command == "python":
    if args == ["scripts/check_uk_candidate.py", "recoverable", "--ledger", "ledger"]:
        assert Path("ledger").is_dir()
        print(Path(os.environ["RECOVERY_CANDIDATE"]).read_text())
    else:
        assert args == ["-"]
        os.execv(sys.executable, [sys.executable, *args])
else:
    assert command == "gh"
    assert Path("ledger").is_dir()
    with Path(os.environ["COMMAND_LOG"]).open("a") as stream:
        stream.write(json.dumps(args) + "\\n")
"""
    for command in ("python", "gh"):
        executable = binary_dir / command
        executable.write_text(fake)
        executable.chmod(0o755)
    ledger_script = tmp_path / ".github" / "qualification-ledger.sh"
    ledger_script.parent.mkdir()
    ledger_script.write_text("#!/bin/bash\nset -e\nmkdir ledger\n")
    ledger_script.chmod(0o755)
    subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{binary_dir}{os.pathsep}{os.environ['PATH']}",
            "RECOVERY_CANDIDATE": str(candidate_path),
            "COMMAND_LOG": str(command_log),
            "GITHUB_REPOSITORY": "PolicyEngine/policyengine.py",
        },
        check=True,
        capture_output=True,
        timeout=30,
    )
    assert [json.loads(line) for line in command_log.read_text().splitlines()] == [
        [
            "workflow",
            "run",
            "certify-uk-release.yaml",
            "--repo",
            "PolicyEngine/policyengine.py",
            "--ref",
            "main",
            "-f",
            "model_version=2.200.0",
            "-f",
            "data_version=1.58.9",
            "-f",
            "force=false",
        ]
    ]
    assert job["permissions"]["actions"] == "write"
    assert step["env"]["GH_TOKEN"] == "${{ github.token }}"


@pytest.mark.parametrize("head_matches", [False, True])
@pytest.mark.parametrize("verdict", ["qualified", "rejected", "accepted_review"])
def test_refresh_checks_reruns_only_failed_pr_runs_for_the_qualified_head(
    monkeypatch, tmp_path, head_matches, verdict
):
    cli = _cli()
    receipt = make_receipt(
        gate_results={
            "qualified": gates(),
            "rejected": gates(replay="fail"),
            "accepted_review": gates(metrics_review="needs_review"),
        }[verdict]
    )
    if verdict == "accepted_review":
        receipt = accept_review(
            receipt,
            reviewer="reviewer",
            accepted_receipt_sha256=receipt.unreviewed_sha256,
            explanation="Expected change checked by the reviewer.",
            accepted_at="2026-10-16T09:00:00Z",
        )
    branch = candidate_branch(receipt.pair)
    head = receipt.harness.git_commit if head_matches else "f" * 40
    monkeypatch.setattr(cli, "latest_receipts", lambda root, **_: [receipt])
    monkeypatch.setattr(cli, "_open_candidate_branches", lambda: {branch: head})
    runs = [
        {
            "id": identifier,
            "head_sha": sha,
            "event": event,
            "status": status,
            "conclusion": conclusion,
        }
        for identifier, sha, event, status, conclusion in (
            (11, head, "pull_request", "completed", "failure"),
            (12, head, "pull_request", "completed", "success"),
            (13, head, "pull_request", "in_progress", "failure"),
            (14, "a" * 40, "pull_request", "completed", "failure"),
            (15, head, "push", "completed", "failure"),
            (16, head, "pull_request", "completed", "timed_out"),
        )
    ]
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[:2] == ["gh", "api"]:
            assert "--paginate" in argv
            assert f"head_sha={receipt.harness.git_commit}" in argv[2]
            assert "event=pull_request" in argv[2]
            return SimpleNamespace(stdout="\n".join(json.dumps(run) for run in runs))
        assert argv[:3] == ["gh", "run", "rerun"]
        assert "--failed" in argv and kwargs["check"] is True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=fake_run))
    args = cli.parser().parse_args(["refresh-pr-checks", "--ledger", str(tmp_path)])
    assert args.func(args) == 0
    reruns = [call[3] for call in calls if call[:3] == ["gh", "run", "rerun"]]
    if receipt.promotable and head_matches:
        assert reruns == ["11", "16"]
    else:
        assert calls == []
