"""The ledger publish script (.github/qualification-ledger.sh) under concurrency.

Invariant: publishes from concurrent runs never lose evidence. Each run's new
directory ends up on the ledger branch, including when both runs found no
ledger yet and each made the branch's first commit.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "qualification-ledger.sh"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _run(*args, cwd, check=True):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.org",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.org",
        "GIT_TERMINAL_PROMPT": "0",
        "LEDGER_RETRY_DELAY": "0",
    }
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _clone(root: Path, origin: Path, name: str) -> Path:
    clone = root / name
    _run(
        "git", "clone", "--quiet", "--branch", "main", str(origin), str(clone), cwd=root
    )
    return clone


def _origin(root: Path) -> Path:
    origin = root / "origin.git"
    _run("git", "init", "--quiet", "--bare", "-b", "main", str(origin), cwd=root)
    seed = root / "seed"
    _run("git", "clone", "--quiet", str(origin), str(seed), cwd=root)
    (seed / "seed").write_text("seed")
    _run("git", "add", "seed", cwd=seed)
    _run("git", "commit", "--quiet", "-m", "seed", cwd=seed)
    _run("git", "push", "--quiet", "origin", "HEAD:refs/heads/main", cwd=seed)
    return origin


def _ledger_files(origin: Path) -> set[str]:
    listing = _run(
        "git", "ls-tree", "-r", "--name-only", "uk-qualification-ledger", cwd=origin
    )
    return set(listing.stdout.split())


@pytest.mark.parametrize("ledger_exists", [False, True])
def test_concurrent_publishes_keep_both_runs_evidence(tmp_path, ledger_exists):
    """Interrupted review of #574: the second first-ever publish failed on HEAD~1."""

    origin = _origin(tmp_path)
    if ledger_exists:
        first = _clone(tmp_path, origin, "first")
        _run("bash", str(SCRIPT), "checkout", "ledger", cwd=first)
        (first / "ledger" / "existing").write_text("existing")
        _run("bash", str(SCRIPT), "publish", "ledger", "existing", cwd=first)
    clones = []
    for name in ("a", "b"):
        clone = _clone(tmp_path, origin, name)
        _run("bash", str(SCRIPT), "checkout", "ledger", cwd=clone)
        (clone / "ledger" / "uk" / name).mkdir(parents=True)
        (clone / "ledger" / "uk" / name / "receipt.json").write_text(name)
        clones.append(clone)
    for clone, name in zip(clones, ("a", "b")):
        result = _run(
            "bash",
            str(SCRIPT),
            "publish",
            "ledger",
            f"attempt {name}",
            cwd=clone,
            check=False,
        )
        assert result.returncode == 0, result.stdout
    files = _ledger_files(origin)
    assert {"uk/a/receipt.json", "uk/b/receipt.json"} <= files
    if ledger_exists:
        assert "existing" in files


def test_an_unchanged_ledger_publishes_nothing(tmp_path):
    origin = _origin(tmp_path)
    clone = _clone(tmp_path, origin, "a")
    _run("bash", str(SCRIPT), "checkout", "ledger", cwd=clone)
    (clone / "ledger" / "x").write_text("x")
    _run("bash", str(SCRIPT), "publish", "ledger", "first", cwd=clone)
    again = _run("bash", str(SCRIPT), "publish", "ledger", "again", cwd=clone)
    assert "Ledger unchanged." in again.stdout
