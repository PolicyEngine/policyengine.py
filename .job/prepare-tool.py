#!/usr/bin/env python3
"""Restore the locally patched #1348 tool without changing an existing checkout.

This performs Git operations only; it never runs the certification tool, imports
a country model, installs dependencies, or loads national data. The original
rehearsal patch files are immutable inputs checked against tool-patches.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

UPSTREAM = "61e25de8a673f4187b2d882acab02d94d4a6da99"
OLD_BUILD = "810315ac2"
NEW_BUILD = "829c1bc26"
TOOL = "tools/certify_uk_cut_in_policyengine_py.py"


def git(repo: Path, *args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-repository",
        default=str(Path("~/PolicyEngine/microcosm").expanduser()),
        help="read-only clone source; may be a local repository or Git URL",
    )
    parser.add_argument("--destination", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse()
    job = Path(__file__).resolve().parent
    workspace = job.parent
    repo = (args.destination or job / "microcosm").resolve()
    if not repo.is_relative_to(workspace) or repo == workspace:
        raise ValueError("The tool checkout must be inside the assigned workspace.")
    receipt = json.loads((job / "tool-patches.json").read_text())
    patches = job / "tool-patches"
    for patch in receipt["patches"]:
        if digest(patches / patch["patch"]) != patch["sha256"]:
            raise ValueError(f"Patch digest differs: {patch['patch']}")
    adaptation = receipt["local_adaptation"]
    if digest(patches / adaptation["patch"]) != adaptation["sha256"]:
        raise ValueError("Local adaptation patch digest differs.")
    preparation = receipt["compatibility_preparation"]
    if digest(patches / preparation["patch"]) != preparation["sha256"]:
        raise ValueError("EOF compatibility patch digest differs.")
    expected = receipt["portable_source"]["sha256"]
    expected_tree = receipt["local_adaptation"]["tree"]
    if digest(job / "certify_uk_cut_in_policyengine_py.py") != expected:
        raise ValueError("Portable tool snapshot digest differs.")

    reused = repo.exists()
    if reused:
        if not (repo / ".git").is_dir():
            raise ValueError(f"Existing destination is not this tool's clone: {repo}")
        if git(repo, "status", "--porcelain", capture=True):
            raise ValueError("Existing tool checkout is dirty; it was preserved.")
        if digest(repo / TOOL) != expected:
            raise ValueError("Existing tool source differs; it was preserved.")
        if git(repo, "rev-parse", "HEAD^{tree}", capture=True) != expected_tree:
            raise ValueError("Existing tool tree differs; it was preserved.")
        git(repo, "merge-base", "--is-ancestor", UPSTREAM, "HEAD")
    else:
        source = args.source_repository
        if source == str(Path("~/PolicyEngine/microcosm").expanduser()):
            if not Path(source).is_dir():
                source = "https://github.com/PolicyEngine/microcosm.git"
        subprocess.run(["git", "clone", "--no-checkout", source, str(repo)], check=True)
        try:
            git(repo, "cat-file", "-e", UPSTREAM + "^{commit}")
        except subprocess.CalledProcessError:
            git(repo, "fetch", "origin", UPSTREAM)
        git(repo, "checkout", "-b", "uk-cut-anyone-budget-prepared", UPSTREAM)
        for name, message in (
            (preparation["patch"], "Align EOF with rehearsal patch source"),
            *[(patch["patch"], "") for patch in receipt["patches"]],
            (adaptation["patch"], "Guard certification steps and preserve provenance"),
        ):
            path = patches / name
            if message:
                git(repo, "apply", "--check", str(path))
                git(repo, "apply", "--index", str(path))
                git(repo, "commit", "-m", message)
            else:
                # Never use a three-way fallback: failures require inspection.
                git(repo, "am", "--no-3way", str(path))
            if git(repo, "status", "--porcelain", capture=True):
                raise ValueError(f"Patch left a dirty checkout: {name}")
        if digest(repo / TOOL) != expected:
            raise ValueError("Reconstructed tool differs from the reviewed snapshot.")
        if git(repo, "rev-parse", "HEAD^{tree}", capture=True) != expected_tree:
            raise ValueError("Reconstructed tool tree differs from the reviewed tree.")

    for build in (OLD_BUILD, NEW_BUILD):
        try:
            git(repo, "cat-file", "-e", build + "^{commit}")
        except subprocess.CalledProcessError:
            raise ValueError(
                f"Source checkout lacks build {build}; fetch the build commit "
                "from microcosm before attribution. No existing files were replaced."
            ) from None
    git(repo, "merge-base", "--is-ancestor", OLD_BUILD, NEW_BUILD)
    result = {
        "schema_version": 1,
        "reused_checkout": reused,
        "checkout": str(repo),
        "head": git(repo, "rev-parse", "HEAD", capture=True),
        "tree": git(repo, "rev-parse", "HEAD^{tree}", capture=True),
        "tool_sha256": digest(repo / TOOL),
        "old_build": git(repo, "rev-parse", OLD_BUILD, capture=True),
        "new_build": git(repo, "rev-parse", NEW_BUILD, capture=True),
        "old_build_is_ancestor": True,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        raise SystemExit(2)
