"""The agent-notes guard (.github/check-agent-notes.sh) and its workflow.

Invariants:

1. The guard fails exactly when the tree holds a note: a path with a
   ``.job``, ``.job-git`` or ``.diag`` component at any depth, or a root-level
   entry named ``HANDOFF.md``, ``handoffs.jsonl``, ``PR_BODY.md``,
   ``PR-BODY.md``, ``REPORT.md`` or ``PROGRESS.md``, matched without regard to
   ASCII case. It reports every such path and no other.
2. A git failure fails the guard instead of passing it.
3. No line it prints for a path can be read as a workflow command.
4. The workflow runs it on every pull request: no path or branch filter.

Invariant 1 is checked on examples and, against a Python reference, on
generated trees. The trees are built in the index alone, which is what the
guard reads, so they need no files on disk.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / ".github" / "check-agent-notes.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pr_agent_notes.yaml"

PREFIX = "Agent or job note: "
NOTE_DIRS = (".job", ".job-git", ".diag")
ROOT_NOTES = (
    "HANDOFF.md",
    "handoffs.jsonl",
    "PR_BODY.md",
    "PR-BODY.md",
    "REPORT.md",
    "PROGRESS.md",
)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")

ISOLATED_GIT = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _git(*args, cwd, input=None):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=ISOLATED_GIT,
        input=input,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    root = tmp_path_factory.mktemp("notes")
    _git("init", "--quiet", cwd=root)
    return root


def _tree(repo: Path, paths) -> Path:
    """Make the index hold exactly these paths, each a one-line file."""
    (repo / ".git" / "index").unlink(missing_ok=True)
    blob = _git("hash-object", "-w", "--stdin", cwd=repo, input=b"x\n")
    blob_id = blob.stdout.decode().strip()
    entries = b"".join(f"100644 {blob_id}\t{path}".encode() + b"\0" for path in paths)
    _git("update-index", "-z", "--add", "--index-info", cwd=repo, input=entries)
    return repo


def _check(cwd: Path, env=None):
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=cwd,
        env=env or ISOLATED_GIT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _reported(result) -> set[str]:
    return {
        line[len(PREFIX) :]
        for line in result.stdout.splitlines()
        if line.startswith(PREFIX)
    }


def is_note(path: str) -> bool:
    """Invariant 1's reference: git's icase folds ASCII letters only."""
    parts = [part.encode().lower() for part in path.split("/")]
    note_dirs = {name.encode().lower() for name in NOTE_DIRS}
    root_notes = {name.encode().lower() for name in ROOT_NOTES}
    return any(part in note_dirs for part in parts) or parts[0] in root_notes


def test_a_job_hand_off_fails(repo):
    """What #704 committed."""
    result = _check(_tree(repo, [".job/HANDOFF.md", "src/policyengine/x.py"]))
    assert result.returncode == 1
    assert _reported(result) == {".job/HANDOFF.md"}
    assert (
        "::error::1 agent or job note path(s) in the tree, starting with "
        ".job/HANDOFF.md" in result.stdout
    )


def test_a_normal_change_passes(repo):
    result = _check(
        _tree(
            repo,
            [
                "src/policyengine/core/simulation.py",
                "tests/test_simulation.py",
                "changelog.d/712.added.md",
                "README.md",
                "CHANGELOG.md",
                "docs/engineering/skills/github-prs.md",
            ],
        )
    )
    assert result.returncode == 0, result.stdout
    assert _reported(result) == set()
    assert "No agent or job notes in the tree." in result.stdout


@pytest.mark.parametrize(
    "path",
    [
        ".job/PR_BODY.md",
        ".job/env",
        ".job/repo.git/HEAD",
        ".JOB/HANDOFF.md",
        "src/.job/HANDOFF.md",
        ".job",
        ".job-git/HEAD",
        "tests/fixtures/.job-git",
        ".diag/run.log",
        "docs/.Diag/notes.md",
        "HANDOFF.md",
        "handoff.md",
        "handoffs.jsonl",
        "PR_BODY.md",
        "pr_body.md",
        "pr-body.md",
        "PR-BODY.md",
        "REPORT.md",
        "Report.md",
        "PROGRESS.md",
        "progress.MD",
    ],
)
def test_each_note_fails(repo, path):
    result = _check(_tree(repo, [path, "src/policyengine/x.py"]))
    assert result.returncode == 1, result.stdout
    assert _reported(result) == {path}


@pytest.mark.parametrize(
    "path",
    [
        "docs/HANDOFF.md",
        "docs/report.md",
        "tests/fixtures/PROGRESS.md",
        ".jobs/x",
        "job/x",
        "x.job/y",
        "my.job",
        ".job.md",
        ".job-gitx/y",
        ".diagnostics/y",
        "HANDOFF.txt",
        "REPORTS.md",
        "PR BODY.md",
    ],
)
def test_near_misses_pass(repo, path):
    result = _check(_tree(repo, [path]))
    assert result.returncode == 0, result.stdout


def test_every_path_of_a_tracked_job_folder_is_reported(repo):
    paths = [".job/repo.git/HEAD", ".job/repo.git/config", ".job/HANDOFF.md"]
    result = _check(_tree(repo, [*paths, "README.md"]))
    assert result.returncode == 1
    assert _reported(result) == set(paths)
    assert "::error::3 agent or job note path(s)" in result.stdout


def test_no_path_line_is_a_workflow_command(repo):
    """Invariant 3: a folder named like a command is printed after a prefix."""
    result = _check(_tree(repo, ["::warning::x/.job/HANDOFF.md", "a\nb/.job/y"]))
    assert result.returncode == 1
    commands = [line for line in result.stdout.splitlines() if line.startswith("::")]
    assert len(commands) == 1 and commands[0].startswith("::error::2 ")
    # git quotes a name that holds a newline, so each path is one line.
    assert _reported(result) == {"::warning::x/.job/HANDOFF.md", '"a\\nb/.job/y"'}


def test_a_git_failure_fails(tmp_path):
    """Invariant 2: outside a repository git fails, and so does the guard."""
    env = {**ISOLATED_GIT, "GIT_CEILING_DIRECTORIES": str(tmp_path.parent)}
    result = _check(tmp_path, env=env)
    assert result.returncode != 0
    assert "No agent or job notes in the tree." not in result.stdout


@pytest.mark.skipif(not (REPO_ROOT / ".git").exists(), reason="needs a git checkout")
def test_this_repository_has_no_notes():
    result = subprocess.run(
        ["bash", str(SCRIPT)], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout


@pytest.mark.skipif(not (REPO_ROOT / ".git").exists(), reason="needs a git checkout")
@pytest.mark.parametrize(
    "path", [".job/HANDOFF.md", ".job-git/HEAD", ".diag/run.log", "src/.job/env"]
)
def test_gitignore_keeps_the_folders_out(path):
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", path], cwd=REPO_ROOT
    )
    assert result.returncode == 0, path


def test_the_workflow_runs_the_guard_on_every_pull_request():
    """Invariant 4."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML reads the bare key "on" as True.
    triggers = workflow.get("on", workflow.get(True))
    assert "pull_request" in triggers
    assert not (triggers["pull_request"] or {}), "no filters on pull_request"
    assert workflow["permissions"] == {"contents": "read"}
    (job,) = workflow["jobs"].values()
    step = next(step for step in job["steps"] if "run" in step)
    assert step["run"] == ".github/check-agent-notes.sh"
    assert step["shell"] == "bash"
    assert "if" not in step and "continue-on-error" not in step
    assert "continue-on-error" not in job
    assert os.access(SCRIPT, os.X_OK)


# Invariant 1 on generated trees. Segments mix the note names, in any ASCII
# case, with near misses and arbitrary names, including glob characters,
# colons and letters outside ASCII.

NEAR_MISSES = (".jobs", "job", ".job.md", "x.job", ".job-gi", ".dia", "HANDOFF")


def _any_case(name: str):
    return st.lists(st.booleans(), min_size=len(name), max_size=len(name)).map(
        lambda upper: "".join(
            c.upper() if u else c.lower() for c, u in zip(name, upper)
        )
    )


SEGMENT = st.one_of(
    st.sampled_from(NOTE_DIRS + ROOT_NOTES + NEAR_MISSES).flatmap(_any_case),
    st.text(
        alphabet="abcxyzHJ019._- :[]*?éüßſİ",
        min_size=1,
        max_size=8,
    ).filter(
        lambda segment: (
            segment not in (".", "..")
            and segment.rstrip(". ").lower() not in (".git", "git~1", "")
        )
    ),
)
PATH = st.lists(SEGMENT, min_size=1, max_size=4).map("/".join)


def _without_conflicts(paths):
    """A path cannot be both a file and a folder of another path."""
    unique = sorted(set(paths))
    return [
        path
        for path in unique
        if not any(other.startswith(path + "/") for other in unique)
    ]


TREE = st.lists(PATH, max_size=8).map(_without_conflicts)


@settings(max_examples=200, deadline=None)
@given(paths=TREE)
def test_the_guard_matches_the_reference_on_generated_trees(repo, paths):
    expected = {path for path in paths if is_note(path)}
    result = _check(_tree(repo, paths))
    assert result.returncode == (1 if expected else 0), (paths, result.stdout)
    assert _reported(result) == expected
    if expected:
        assert f"::error::{len(expected)} agent or job note path(s)" in result.stdout
