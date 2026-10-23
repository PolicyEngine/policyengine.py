"""The agent-notes guard (.github/check-agent-notes.sh) and its workflow.

Invariants:

1. The guard fails exactly when the tree holds a note: a path with a
   ``.job``, ``.job-git`` or ``.diag`` component at any depth, or a root-level
   entry named ``HANDOFF.md``, ``handoffs.jsonl``, ``PR_BODY.md``,
   ``PR-BODY.md``, ``REPORT.md`` or ``PROGRESS.md``, matched without regard to
   ASCII case. It reports every such path and no other.
2. Given a commit, it judges that commit's tree, whatever the index holds,
   and leaves the index as it was.
3. A git failure fails the guard instead of passing it.
4. The runner reads no path it prints as a workflow command: the only
   commands are its own stop-commands, the matching resume and one error.
5. The workflow checks every pull request's head, with no path or branch
   filter, and checks main on every push and on a schedule, which "[skip ci]"
   cannot skip. It holds a read-only token and no pull_request_target.

Invariant 1 is checked on examples and, against a Python reference, on
generated trees, where invariant 2 is checked against the index mode. The
trees are built in the index alone, which is what the guard reads, so they
need no files on disk.
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
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.org",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.org",
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


def _commit(repo: Path, paths) -> str:
    """A commit whose tree holds exactly these paths."""
    tree = _git("write-tree", cwd=_tree(repo, paths)).stdout.decode().strip()
    commit = _git("commit-tree", tree, "-m", "tree", cwd=repo)
    return commit.stdout.decode().strip()


def _check(cwd: Path, *args, env=None):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
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


# How the GitHub Actions runner reads a step's output, from actions/runner's
# src/Runner.Common/ActionCommand.cs (TryParseV2, TryParse, UnescapeData) and
# src/Runner.Worker/ActionCommandManager.cs (TryProcessCommand). A line is a
# command when, after leading whitespace, it starts with "::name ...::data",
# or when "##[name ...]data" appears anywhere in it, and the name is
# registered. While commands are stopped, only the stop token resumes them.

RUNNER_COMMANDS = {
    "add-mask",
    "add-matcher",
    "add-path",
    "debug",
    "echo",
    "endgroup",
    "error",
    "group",
    "notice",
    "remove-matcher",
    "save-state",
    "set-env",
    "set-output",
    "stop-commands",
    "warning",
}


def _parse_command(line: str, registered: set[str]):
    message = line.lstrip()
    if message.startswith("::"):
        end = message.find("::", 2)
        if end >= 0:
            name = message[2:end].split(" ", 1)[0]
            if name in registered:
                return name, message[end + 2 :]
    start = line.find("##[")
    if start >= 0:
        end = line.find("]", start)
        if end >= 0:
            name = line[start + 3 : end].split(" ", 1)[0]
            if name in registered:
                return name, line[end + 1 :]
    return None


def _unescape_data(data: str) -> str:
    return data.replace("%0D", "\r").replace("%0A", "\n").replace("%25", "%")


def _runner_commands(stdout: str) -> list[tuple[str, str]]:
    registered = set(RUNNER_COMMANDS)
    processed, token = [], None
    for line in stdout.splitlines():
        command = _parse_command(line, registered)
        if command is None:
            continue
        name, data = command
        if token is not None:
            if name.lower() == token.lower():
                processed.append((name, data))
                registered.discard(token)
                token = None
            continue
        if name == "stop-commands":
            token = data
            registered.add(token)
        processed.append((name, _unescape_data(data)))
    return processed


def test_a_job_hand_off_fails(repo):
    """What #704 committed."""
    result = _check(_tree(repo, [".job/HANDOFF.md", "src/policyengine/x.py"]))
    assert result.returncode == 1
    assert _reported(result) == {".job/HANDOFF.md"}
    assert _runner_commands(result.stdout)[-1] == (
        "error",
        "1 agent or job note path(s) in the tree, starting with .job/HANDOFF.md "
        "(all listed in the log) - post their content on the pull request and "
        "remove them.",
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
    assert _runner_commands(result.stdout) == []
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


def test_a_commit_is_judged_by_its_tree_not_the_index(repo):
    """Invariant 2."""
    with_note = _commit(repo, [".job/HANDOFF.md", "src/policyengine/x.py"])
    clean = _commit(repo, ["src/policyengine/x.py"])
    index = _tree(repo, ["PROGRESS.md"]) / ".git" / "index"
    before = index.read_bytes()

    result = _check(repo, with_note)
    assert result.returncode == 1, result.stdout
    assert _reported(result) == {".job/HANDOFF.md"}

    result = _check(repo, clean)
    assert result.returncode == 0, result.stdout

    assert index.read_bytes() == before
    assert _reported(_check(repo)) == {"PROGRESS.md"}


def test_the_runner_reads_no_path_as_a_command(repo):
    """Invariant 4, with names built from both command syntaxes.

    Before stop-commands, a "##[stop-commands]" folder name stopped the
    runner's commands and swallowed the error annotation.
    """
    paths = [
        ".job/##[stop-commands]agent-note-stop",
        ".job/##[add-mask]x",
        "::warning::x/.job/HANDOFF.md",
        "  ::error::forged/.job/y",
        "a\nb/.job/y",
    ]
    result = _check(_tree(repo, paths))
    assert result.returncode == 1
    commands = _runner_commands(result.stdout)
    assert [name for name, _ in commands][0] == "stop-commands"
    token = commands[0][1]
    assert len(token) == 32 and all(c in "0123456789abcdef" for c in token)
    assert [name for name, _ in commands] == ["stop-commands", token, "error"]
    assert commands[2][1].startswith("5 agent or job note path(s) in the tree")
    # Git quotes a name that holds a newline, so each path is one line.
    assert _reported(result) == {*paths[:4], '"a\\nb/.job/y"'}


def test_the_annotation_shows_a_percent_sign_as_written(repo):
    result = _check(_tree(repo, [".job/%0Aforged%25"]))
    (*_, (name, data)) = _runner_commands(result.stdout)
    assert name == "error"
    assert "starting with .job/%0Aforged%25 (all listed" in data


def test_a_git_failure_fails(tmp_path, repo):
    """Invariant 3: outside a repository, or given no commit, git fails."""
    env = {**ISOLATED_GIT, "GIT_CEILING_DIRECTORIES": str(tmp_path.parent)}
    for result in (
        _check(tmp_path, env=env),
        _check(repo, "0123456789abcdef0123456789abcdef01234567"),
    ):
        assert result.returncode != 0
        assert "No agent or job notes in the tree." not in result.stdout


@pytest.mark.skipif(not (REPO_ROOT / ".git").exists(), reason="needs a git checkout")
@pytest.mark.parametrize("args", [(), ("HEAD",)])
def test_this_repository_has_no_notes(args):
    result = subprocess.run(
        ["bash", str(SCRIPT), *args], cwd=REPO_ROOT, capture_output=True, text=True
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


def test_the_workflow_checks_every_pull_request_head_and_main():
    """Invariant 5."""
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    # PyYAML reads the bare key "on" as True.
    triggers = workflow.get("on", workflow.get(True))
    # No pull_request_target: pull request workflows here never use it
    # (docs/release-bundles.md).
    assert set(triggers) == {"pull_request", "push", "schedule", "workflow_dispatch"}
    assert triggers["pull_request"] is None, "no filters or types"
    assert triggers["push"] == {"branches": ["main"]}
    assert len(triggers["schedule"]) == 1
    assert workflow["permissions"] == {"contents": "read"}
    assert "secrets." not in text
    (job,) = workflow["jobs"].values()
    assert "continue-on-error" not in job
    checkout, fetch, guard = job["steps"]
    assert checkout == {"uses": "actions/checkout@v6"}
    assert fetch["if"] == "github.event_name == 'pull_request'"
    assert fetch["env"] == {"HEAD_SHA": "${{ github.event.pull_request.head.sha }}"}
    assert fetch["run"] == 'git fetch --no-tags --depth=1 origin "$HEAD_SHA"'
    assert guard["run"] == '.github/check-agent-notes.sh "$COMMIT"'
    assert guard["env"] == {
        "COMMIT": "${{ github.event.pull_request.head.sha || github.sha }}"
    }
    assert guard["shell"] == "bash"
    assert "if" not in guard and "continue-on-error" not in guard
    assert os.access(SCRIPT, os.X_OK)


# Invariants 1 and 2 on generated trees. Segments mix the note names, in any
# ASCII case, with near misses and arbitrary names, including glob
# characters, colons and letters outside ASCII.

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


@settings(max_examples=150, deadline=None)
@given(paths=TREE)
def test_the_guard_matches_the_reference_on_generated_trees(repo, paths):
    expected = {path for path in paths if is_note(path)}
    commit = _commit(repo, paths)
    for result in (_check(_tree(repo, paths)), _check(_tree(repo, []), commit)):
        assert result.returncode == (1 if expected else 0), (paths, result.stdout)
        assert _reported(result) == expected
        if expected:
            (*_, (name, data)) = _runner_commands(result.stdout)
            assert name == "error"
            assert data.startswith(f"{len(expected)} agent or job note path(s)")
