"""Check the release lock, or refresh only its post-bump root version.

Resolve reviewed dependency changes with ordinary ``uv lock`` before the PR is
reviewed. Versioning must not introduce a new dependency graph after review.
"""

from __future__ import annotations

import argparse
import copy
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPI = "https://pypi.org/simple"


def validate_registry_artifacts(package: dict) -> None:
    """PyPI's source label alone does not constrain uv's download locations."""
    artifacts = [*package.get("wheels", [])]
    if package.get("sdist"):
        artifacts.append(package["sdist"])
    if not artifacts:
        raise ValueError(
            f"Release lock dependency {package['name']} has no registry artifacts"
        )
    for artifact in artifacts:
        url = urlsplit(artifact.get("url", ""))
        if (
            url.scheme != "https"
            or url.hostname != "files.pythonhosted.org"
            or url.username is not None
            or url.password is not None
            or url.port not in (None, 443)
            or not url.path.startswith("/packages/")
            or url.query
            or url.fragment
        ):
            raise ValueError(
                f"Release lock dependency {package['name']} has a non-PyPI artifact URL"
            )
        if re.fullmatch(r"sha256:[0-9a-f]{64}", artifact.get("hash", "")) is None:
            raise ValueError(
                f"Release lock dependency {package['name']} has an invalid artifact SHA256"
            )


def load_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text())


def validate_registry_project(project: dict) -> None:
    """Reject development sources in public package and resolver metadata."""
    uv = project.get("tool", {}).get("uv", {})
    if uv.get("sources") or uv.get("index") or uv.get("workspace"):
        raise ValueError(
            "Release metadata must use registry dependencies without uv source/index/workspace overrides"
        )

    def reject_urls(value):
        if isinstance(value, str) and "@" in value:
            raise ValueError(
                "Release requirements must be registry dependencies, not direct URLs or local paths"
            )
        if isinstance(value, list):
            for item in value:
                reject_urls(item)
        if isinstance(value, dict):
            for item in value.values():
                reject_urls(item)

    metadata = project.get("project", {})
    for value in (
        metadata.get("dependencies", []),
        metadata.get("optional-dependencies", {}),
        project.get("dependency-groups", {}),
        project.get("build-system", {}).get("requires", []),
        uv.get("constraint-dependencies", []),
        uv.get("override-dependencies", []),
    ):
        reject_urls(value)


def _normalized_python_range(value: object) -> str:
    """Compare the reviewed range by content, not by spelling.

    ``uv lock`` writes a canonically spaced specifier set, so an unchanged
    range can differ from ``pyproject.toml`` by whitespace alone. Any real
    change to a clause still fails the comparison.
    """
    if not isinstance(value, str):
        return ""
    return ",".join(clause.strip() for clause in value.split(","))


def validate_registry_lock(
    project: dict, lock: dict, *, allow_previous_version: bool = False
) -> None:
    """The checkout itself is the only permitted non-registry package."""
    metadata = project["project"]
    if _normalized_python_range(lock.get("requires-python")) != (
        _normalized_python_range(metadata["requires-python"])
    ):
        raise ValueError("Release lock Python range differs from pyproject.toml")
    root_name = metadata["name"].lower().replace("_", "-")
    roots = []
    for package in lock.get("package", []):
        if package["name"] == root_name:
            roots.append(package)
            if package.get("source") != {"editable": "."}:
                raise ValueError(
                    "Release lock root must be the current checkout; dependencies must use the registry"
                )
        elif package.get("source") != {"registry": PYPI}:
            raise ValueError(
                f"Release lock dependency {package['name']} is not from the PyPI registry"
            )
        else:
            validate_registry_artifacts(package)
    if len(roots) != 1:
        raise ValueError("Release lock must contain exactly one root package")
    if not allow_previous_version and roots[0]["version"] != metadata["version"]:
        raise ValueError("Release lock root version differs from pyproject.toml")


def without_root_version(lock: dict, root_name: str) -> dict:
    result = copy.deepcopy(lock)
    for package in result["package"]:
        if package["name"] == root_name:
            package.pop("version")
    return result


def resolver_environment() -> dict[str, str]:
    # Do not let an inherited development index, find-links directory, project
    # path, frozen mode, or resolver option change this publication boundary.
    env = {key: value for key, value in os.environ.items() if not key.startswith("UV_")}
    env["UV_FROZEN"] = "0"
    return env


def check_release_lock(root: Path = REPO_ROOT, *, refresh: bool = False) -> None:
    project = load_toml(root / "pyproject.toml")
    validate_registry_project(project)
    lock_path = root / "uv.lock"
    before_bytes = lock_path.read_bytes()
    before = tomllib.loads(before_bytes.decode())
    validate_registry_lock(project, before, allow_previous_version=refresh)
    command = [
        "uv",
        "lock",
        "--no-config",
        "--no-sources",
        "--default-index",
        PYPI,
        "--python",
        sys.executable,
    ]
    kwargs = {"cwd": root, "env": resolver_environment(), "check": True}
    try:
        if refresh:
            subprocess.run(command, **kwargs)
            after = load_toml(lock_path)
            validate_registry_lock(project, after)
            name = project["project"]["name"].lower().replace("_", "-")
            if without_root_version(before, name) != without_root_version(after, name):
                raise ValueError(
                    "Versioning changed the reviewed dependency graph; prepare and review the lock before release"
                )
        subprocess.run([*command, "--check"], **kwargs)
    except (ValueError, OSError, subprocess.CalledProcessError):
        if refresh:
            lock_path.write_bytes(before_bytes)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh only the root package version after the automatic bump",
    )
    args = parser.parse_args()
    try:
        check_release_lock(refresh=args.refresh)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
