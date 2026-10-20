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
from tests.qualification_fixtures import (
    HARNESS,
    UK_DATA_LINE_BUNDLE_PATH,
    gates,
    graphql_base_changes_output,
    make_pair,
    make_receipt,
    rest_pulls_output,
)

PULLS = ["repos/PolicyEngine/policyengine.py/pulls"]

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/certify-uk-release.yaml"


def _cli():
    spec = importlib.util.spec_from_file_location(
        "qualification_workflow_cli", REPO_ROOT / "scripts/check_uk_candidate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # These tests build candidates on the policyengine-uk-data line.
    module.BUNDLE_PATH = UK_DATA_LINE_BUNDLE_PATH
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


def test_every_uv_step_runs_the_environment_its_job_installed():
    """The repository's .python-version asks for a newer Python than the 3.13
    environment each job installs. A syncing `uv run` would replace that
    environment, extras and all, so every step and the ledger re-derivation
    must run the interpreter the job provisioned."""
    workflow = _workflow()
    assert (REPO_ROOT / ".python-version").read_text().strip() != (
        workflow["env"]["PYTHON_VERSION"]
    )
    assert workflow["env"]["UV_PYTHON"] == workflow["env"]["PYTHON_VERSION"]
    command = "${{ github.workspace }}/scripts/check_uk_candidate.py rederive-ledger"
    publishing_jobs = []
    for name, job in workflow["jobs"].items():
        runs = [step.get("run", "") for step in job["steps"]]
        synced = any(
            "uv sync --frozen --extra uk --extra dev --python "
            "${{ env.PYTHON_VERSION }}" in run
            for run in runs
        )
        system = any("uv pip install --system" in run for run in runs)
        assert not (synced and system), name
        for line in (line for run in runs for line in run.splitlines()):
            if "uv run" in line:
                assert synced, (name, line)
                assert "uv run --no-sync " in line, (name, line)
        if any(".github/qualification-ledger.sh publish" in run for run in runs):
            publishing_jobs.append(name)
            rederive = job.get("env", {}).get(
                "LEDGER_REDERIVE", workflow["env"]["LEDGER_REDERIVE"]
            )
            if synced:
                interpreter = "${{ github.workspace }}/.venv/bin/python"
            else:
                assert system, name
                interpreter = "python"
            assert rederive == f"{interpreter} {command}", name
    assert sorted(publishing_jobs) == [
        "accept",
        "catch-up",
        "prepare",
        "qualify",
        "replay",
    ]


def test_catch_up_requalifies_a_stale_target_after_finishing_receipts():
    """The requalification dispatch runs without force, after waiting
    receipts are finished and published, so it reads the newest ledger."""

    job = _workflow()["jobs"]["catch-up"]
    runs = [step.get("run", "") for step in job["steps"]]
    requalify = next(
        index
        for index, run in enumerate(runs)
        if "check_uk_candidate.py requalify" in run
    )
    published = next(
        index
        for index, run in enumerate(runs)
        if "qualification-ledger.sh publish" in run
    )
    assert published < requalify
    assert '"-f", "force=false"' in runs[requalify]
    assert "force=true" not in runs[requalify]
    assert job["steps"][requalify]["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert job["permissions"]["actions"] == "write"


def test_every_dispatch_names_the_exact_pair():
    """Recovery and requalification dispatch one pair: its versions, its core
    and its id, which resolve checks, so another pair is never qualified in
    its place."""

    workflow = _workflow()
    inputs = workflow[True]["workflow_dispatch"]["inputs"]
    assert {"core_version", "pair_id"} <= set(inputs)
    resolve = next(
        step
        for step in workflow["jobs"]["resolve"]["steps"]
        if step.get("name") == "Resolve and deduplicate the candidate"
    )
    assert '--core-version "$INPUT_CORE"' in resolve["run"]
    assert '--pair-id "$INPUT_PAIR_ID"' in resolve["run"]
    dispatches = [
        step["run"]
        for step in workflow["jobs"]["catch-up"]["steps"]
        if 'gh", "workflow", "run' in step.get("run", "")
        or '"gh", "workflow", "run"' in step.get("run", "")
    ]
    assert len(dispatches) == 2
    for run in dispatches:
        assert "core_version={pair['core']['version']}" in run
        assert "pair_id={pair_id}" in run
        assert 'entry["pair_id"]' in run


def test_preparation_rechecks_eligibility_and_tests_the_candidates_own_tree():
    """Round 2 of #635: under the preparation lock, a run whose pair another
    run is already qualifying (from any main commit) stops; and the
    code-changes workflow runs on the candidate branch itself, the tree
    promotion would put on main."""

    job = _workflow()["jobs"]["prepare"]
    steps = job["steps"]
    names = [step.get("name") for step in steps]
    duplicate = steps[names.index("Check for an attempt staged by another run")]
    assert "check_uk_candidate.py still-eligible" in duplicate["run"]
    # It asks gh whether an earlier attempt's run failed (round 3 of #635).
    assert duplicate["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert names.index("Install the base environment") < names.index(
        "Check for an attempt staged by another run"
    )
    own_tree = steps[names.index("Test the candidate commit's own tree")]
    assert own_tree["run"].startswith("gh workflow run pr_code_changes.yaml")
    assert '--ref "$BRANCH"' in own_tree["run"]
    assert own_tree["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert names.index("Commit and push the candidate commit") < names.index(
        "Test the candidate commit's own tree"
    )
    assert job["permissions"]["actions"] == "write"
    triggers = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/pr_code_changes.yaml").read_text()
    )[True]
    assert "workflow_dispatch" in triggers


def test_still_eligible_reports_a_pair_another_run_is_qualifying(monkeypatch, tmp_path):
    from policyengine.provenance.qualification_ledger import attempt_directory
    from policyengine.provenance.uk_qualification import stage_attempt

    cli = _cli()
    pair = make_pair(model="2.200.0")
    candidate = tmp_path / "candidate.json"
    candidate.write_text(
        json.dumps(
            {
                "pair": pair.canonical_payload(),
                "pair_id": pair.pair_id,
                "base_commit": "b" * 40,
                "force": False,
            }
        )
    )
    outputs = []
    monkeypatch.setattr(cli, "set_output", lambda **kwargs: outputs.append(kwargs))
    monkeypatch.setattr(cli, "utc_now", lambda: "2026-10-16T10:00:00Z")
    args = argparse.Namespace(candidate=str(candidate), ledger=str(tmp_path))
    assert cli.cmd_still_eligible(args) == 0
    assert outputs[-1] == {"duplicate": "false"}
    stage_attempt(
        attempt_directory(tmp_path, "uk", pair.pair_id, "a" * 12),
        {"pair": pair.canonical_payload(), "pair_id": pair.pair_id},
        HARNESS,
        owner_run_id="7",
        staged_at="2026-10-16T09:30:00Z",
    )
    assert cli.cmd_still_eligible(args) == 0
    assert outputs[-1] == {"duplicate": "true"}
    # A forced run is never turned into a duplicate (round 3 of #635: the
    # recheck dropped force and still passed every test).
    payload = json.loads(candidate.read_text())
    candidate.write_text(json.dumps({**payload, "force": True}))
    assert cli.cmd_still_eligible(args) == 0
    assert outputs[-1] == {"duplicate": "false"}


def test_preparation_syncs_the_candidate_lock_before_using_it():
    """Snapshots, the bundle check and staging must run in the candidate's
    environment: synced from the lock preparation regenerates, after it is
    regenerated, with the 3.13 interpreter and both extras."""

    steps = _workflow()["jobs"]["prepare"]["steps"]
    runs = [step.get("run", "") for step in steps]
    sync = "uv sync --frozen --extra uk --extra dev --python ${{ env.PYTHON_VERSION }}"

    def position(text):
        return next(index for index, run in enumerate(runs) if text in run)

    syncs = [index for index, run in enumerate(runs) if sync in run]
    regenerate = position("check_uk_candidate.py prepare")
    assert len(syncs) == 2 and syncs[0] < regenerate < syncs[1]
    for later in (
        "tests/test_household_calculator_snapshot.py",
        "scripts/bundle.py check",
        "check_uk_candidate.py stage",
    ):
        assert syncs[1] < position(later), later


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
if command == "gh" and args[:1] == ["api"] and "--paginate" in args:
    # The REST listing of this repository's pull request to main, through
    # the step's jq (only a ready one's number is printed).
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
                "GITHUB_REPOSITORY": "PolicyEngine/policyengine.py",
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
                    [
                        {
                            "number": 1,
                            "headRefName": branch,
                            "headRefOid": state["head"],
                            "isDraft": state["status"] != "ready",
                            "isCrossRepository": False,
                            "baseRefName": "main",
                        }
                    ]
                )
            )
        # Promotion reads the branch head and checks main is its parent.
        if argv[:2] == ["git", "fetch"]:
            return SimpleNamespace(returncode=0, stdout="")
        if argv[:3] == ["git", "rev-parse", "FETCH_HEAD"]:
            head = json.loads(state_path.read_text())["head"]
            return SimpleNamespace(returncode=0, stdout=head)
        if argv[:2] == ["git", "rev-parse"]:
            return SimpleNamespace(returncode=0, stdout="p" * 40)
        if argv[:2] == ["git", "ls-remote"]:
            return SimpleNamespace(returncode=0, stdout="p" * 40 + "\trefs/heads/main")
        assert argv[:3] == ["gh", "pr", "ready"]
        if "--undo" in argv:
            return SimpleNamespace(returncode=0)
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
    candidate_path.write_text(
        json.dumps({"pair": pair.canonical_payload(), "pair_id": pair.pair_id})
    )
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
            f"core_version={pair.core.version}",
            "-f",
            f"pair_id={pair.pair_id}",
            "-f",
            "force=false",
        ]
    ]
    assert job["permissions"]["actions"] == "write"
    assert step["env"]["GH_TOKEN"] == "${{ github.token }}"


@pytest.mark.parametrize("head_matches", [False, True])
@pytest.mark.parametrize("verdict", ["qualified", "rejected", "accepted_review"])
def test_refresh_checks_reruns_only_failed_pr_runs_for_the_qualified_head(
    monkeypatch, tmp_path, capsys, head_matches, verdict
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
    monkeypatch.setattr(
        cli, "_candidate_pull_requests", lambda: [_candidate_pr(1, branch, head)]
    )
    monkeypatch.setattr(cli, "_now", lambda: _instant(NOW))
    code, docs, guard, old = (
        ".github/workflows/pr_code_changes.yaml",
        ".github/workflows/pr_docs.yaml",
        ".github/workflows/guard.yaml",
        ".github/workflows/old.yaml",
    )
    fork = {"head_repository": "someone/policyengine.py"}
    other = {"head_branch": "candidate/uk/other"}
    runs = [
        _listed_run(identifier, sha, branch, path, event, status, conclusion, attempt)
        | extra
        for identifier, sha, path, event, status, conclusion, attempt, extra in (
            # Replaced by run 16 of the same workflow and event: left alone,
            # so its checks cannot come back newer (round 3 of #635).
            (11, head, code, "pull_request", "completed", "failure", 1, {}),
            (12, head, docs, "pull_request", "completed", "success", 1, {}),
            (13, head, guard, "pull_request", "in_progress", None, 1, {}),
            (14, "a" * 40, code, "pull_request", "completed", "failure", 1, {}),
            (15, head, code, "push", "completed", "failure", 1, {}),
            # GitHub refuses this re-run: refresh warns and the rest still go
            # (round 4; round 5 lists it first).
            (16, head, code, "pull_request", "completed", "timed_out", 1, {}),
            # The run on the candidate's own tree that promotion requires; a
            # job timeout cancels the run (round 3 of #635).
            (17, head, code, "workflow_dispatch", "completed", "cancelled", 1, {}),
            # Already run as often as the cap allows (four attempts).
            (18, head, docs, "workflow_dispatch", "completed", "failure", 4, {}),
            (19, head, guard, "workflow_dispatch", "completed", "failure", 3, {}),
            # Round 5 of #635: a fork's newer run at the same commit, and one
            # of another branch here, are not the candidate's: neither is
            # re-run, nor replaces the candidate's own runs 16 and 12.
            (21, head, code, "pull_request", "completed", "failure", 1, fork),
            (22, head, docs, "pull_request", "completed", "failure", 1, other),
            # Round 5: GitHub re-runs only within 30 days of the first attempt,
            # and refresh re-runs only failures, timeouts and cancellations.
            (
                23,
                head,
                old,
                "workflow_dispatch",
                "completed",
                "failure",
                1,
                {"created_at": OLD},
            ),
            (24, head, old, "pull_request", "completed", "action_required", 1, {}),
        )
    ]
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[:3] == ["gh", "api", "graphql"]:
            return SimpleNamespace(
                returncode=0, stdout=graphql_base_changes_output(argv, set())
            )
        if argv[:2] == ["gh", "api"] and argv[4:5] == PULLS:
            assert f"head=PolicyEngine:{branch}" in argv
            return SimpleNamespace(
                returncode=0,
                stdout=rest_pulls_output(argv, [_candidate_pr(1, branch, head)]),
            )
        if argv[:2] == ["gh", "api"]:
            assert "--paginate" in argv
            assert f"head_sha={receipt.harness.git_commit}" in argv[2]
            return SimpleNamespace(
                returncode=0, stdout="\n".join(json.dumps(run) for run in runs)
            )
        assert argv[:3] == ["gh", "run", "rerun"] and kwargs["check"] is False
        return SimpleNamespace(returncode=1 if argv[3] == "16" else 0)

    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=fake_run))
    args = cli.parser().parse_args(["refresh-pr-checks", "--ledger", str(tmp_path)])
    assert args.func(args) == 0
    reruns = [
        (call[3], "--failed" in call)
        for call in calls
        if call[:3] == ["gh", "run", "rerun"]
    ]
    output = capsys.readouterr().out
    if receipt.promotable and head_matches:
        # Failed jobs only for failed and timed-out runs; the cancelled one in
        # full; the one at the cap, the old one and the fork's not at all.
        assert reruns == [("16", True), ("17", False), ("19", True)]
        assert "::warning::GitHub did not re-run timed_out run 16" in output
    else:
        assert calls == []


NOW = "2026-10-16T12:00:00Z"
OLD = "2026-09-15T11:00:00Z"


def _candidate_pr(number, branch, head, **fields):
    """A same-repository pull request from ``branch`` to main, open, as
    `gh pr list` reads it."""

    return {
        "number": number,
        "baseRefName": "main",
        "headRefName": branch,
        "headRefOid": head,
        "isDraft": True,
        "isCrossRepository": False,
        "state": "OPEN",
        **fields,
    }


def _instant(text):
    import datetime

    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))


def _listed_run(identifier, sha, branch, path, event, status, conclusion, attempt):
    """A run as `_commit_runs` reads it: the candidate's own by default."""

    return {
        "id": identifier,
        "head_sha": sha,
        "head_branch": branch,
        "head_repository": "PolicyEngine/policyengine.py",
        "path": path,
        "event": event,
        "status": status,
        "conclusion": conclusion,
        "check_suite_id": 1000 + identifier,
        "run_attempt": attempt,
        "created_at": "2026-10-16T06:00:00Z",
    }


def test_refresh_reruns_each_candidate_only_its_own_runs(monkeypatch, tmp_path, capsys):
    """Round 5 of #635: two candidates qualified at the same commit share its
    runs listing; each re-runs only its own branch's runs, and one whose runs
    cannot be read is reported while the other is still refreshed."""

    cli = _cli()
    first = make_receipt(pair=make_pair(model="2.200.0"))
    second = make_receipt(pair=make_pair(model="2.201.0"))
    head = first.harness.git_commit
    assert second.harness.git_commit == head
    branches = {candidate_branch(r.pair): head for r in (first, second)}
    pull_requests = [
        _candidate_pr(number, name, head)
        for number, name in enumerate(branches, start=1)
    ]
    monkeypatch.setattr(cli, "latest_receipts", lambda root, **_: [first, second])
    monkeypatch.setattr(cli, "_candidate_pull_requests", lambda: pull_requests)
    monkeypatch.setattr(cli, "_now", lambda: _instant(NOW))
    code = ".github/workflows/pr_code_changes.yaml"
    first_branch, second_branch = branches
    runs = [
        _listed_run(
            31, head, first_branch, code, "pull_request", "completed", "failure", 1
        ),
        _listed_run(
            32, head, second_branch, code, "pull_request", "completed", "failure", 1
        ),
    ]
    calls = []
    unreadable = {"once": True}

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[:3] == ["gh", "api", "graphql"]:
            return SimpleNamespace(
                returncode=0, stdout=graphql_base_changes_output(argv, set())
            )
        if argv[:2] == ["gh", "api"] and argv[4:5] == PULLS:
            return SimpleNamespace(
                returncode=0, stdout=rest_pulls_output(argv, pull_requests)
            )
        if argv[:2] == ["gh", "api"]:
            if unreadable.pop("once", False):
                return SimpleNamespace(returncode=1, stdout="")
            return SimpleNamespace(
                returncode=0, stdout="\n".join(json.dumps(run) for run in runs)
            )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=fake_run))
    args = cli.parser().parse_args(["refresh-pr-checks", "--ledger", str(tmp_path)])
    assert args.func(args) == 0
    output = capsys.readouterr().out
    assert f"::warning::could not read the runs of {first_branch}" in output
    assert [call[3] for call in calls if call[:3] == ["gh", "run", "rerun"]] == ["32"]


@pytest.mark.parametrize(
    "shared", ["another base", "a base change", "unreadable", "unreadable history"]
)
def test_refresh_leaves_a_candidate_whose_branch_runs_are_shared(
    monkeypatch, tmp_path, capsys, shared
):
    """Round 6 of #635: a pull request from the candidate branch to another
    base runs on the same commit and branch, so the candidate's runs cannot
    be told from its runs; refresh re-runs none of them (promotion refuses
    the candidate anyway), and the next candidate is still refreshed. Round
    7: so does the candidate's own pull request once its base was changed.
    The same holds while that branch's pull requests, or their base history,
    cannot be read."""

    cli = _cli()
    first = make_receipt(pair=make_pair(model="2.200.0"))
    second = make_receipt(pair=make_pair(model="2.201.0"))
    head = first.harness.git_commit
    first_branch, second_branch = (candidate_branch(r.pair) for r in (first, second))
    pull_requests = [
        _candidate_pr(1, first_branch, head),
        _candidate_pr(2, second_branch, head),
    ]
    other = _candidate_pr(7, first_branch, head, baseRefName="release")
    monkeypatch.setattr(cli, "latest_receipts", lambda root, **_: [first, second])
    monkeypatch.setattr(cli, "_candidate_pull_requests", lambda: pull_requests)
    monkeypatch.setattr(cli, "_now", lambda: _instant(NOW))
    code = ".github/workflows/pr_code_changes.yaml"
    runs = [
        _listed_run(
            31, head, first_branch, code, "pull_request", "completed", "failure", 1
        ),
        _listed_run(
            32, head, second_branch, code, "pull_request", "completed", "failure", 1
        ),
    ]
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[:3] == ["gh", "api", "graphql"]:
            number = int(next(v for v in argv if v.startswith("number="))[7:])
            if number == 1 and shared == "unreadable history":
                return SimpleNamespace(returncode=1, stdout="")
            changed = {1} if shared == "a base change" else set()
            return SimpleNamespace(
                returncode=0, stdout=graphql_base_changes_output(argv, changed)
            )
        if argv[:2] == ["gh", "api"] and argv[4:5] == PULLS:
            if f"head=PolicyEngine:{first_branch}" in argv and shared == "unreadable":
                return SimpleNamespace(returncode=1, stdout="")
            listing = [*pull_requests, other] if shared == "another base" else []
            return SimpleNamespace(
                returncode=0,
                stdout=rest_pulls_output(argv, listing or pull_requests),
            )
        if argv[:2] == ["gh", "api"]:
            return SimpleNamespace(
                returncode=0, stdout="\n".join(json.dumps(run) for run in runs)
            )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli, "subprocess", SimpleNamespace(run=fake_run))
    args = cli.parser().parse_args(["refresh-pr-checks", "--ledger", str(tmp_path)])
    assert args.func(args) == 0
    output = capsys.readouterr().out
    if shared.startswith("unreadable"):
        assert f"::warning::could not read the pull requests from {first_branch}" in (
            output
        )
    else:
        assert f"::warning::not re-running {first_branch}'s runs" in output
        assert (
            "#7 (to release, open)"
            if shared == "another base"
            else "#1 (the candidate's own, after a base change)"
        ) in output
    assert [call[3] for call in calls if call[:3] == ["gh", "run", "rerun"]] == ["32"]
