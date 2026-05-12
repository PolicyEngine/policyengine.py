"""Infer semver bump from towncrier fragment types and update version."""

import json
import re
import subprocess
import sys
from pathlib import Path

SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_version(version: str) -> tuple[int, int, int]:
    match = SEMVER_PATTERN.match(version)
    if not match:
        raise ValueError(f"Invalid semver: {version}")
    return tuple(int(part) for part in match.groups())


def get_pyproject_version(pyproject_path: Path) -> str:
    text = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"', text, re.MULTILINE)
    if not match:
        print(
            "Could not find version in pyproject.toml",
            file=sys.stderr,
        )
        sys.exit(1)
    return match.group(1)


def get_changelog_versions(changelog_path: Path) -> list[str]:
    if not changelog_path.exists():
        return []
    return re.findall(
        r"^## \[(\d+\.\d+\.\d+)\]", changelog_path.read_text(), re.MULTILINE
    )


def get_git_tag_versions(repo_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "tag"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    versions = []
    for tag in result.stdout.splitlines():
        normalized = tag.removeprefix("v").strip()
        if SEMVER_PATTERN.match(normalized):
            versions.append(normalized)
    return versions


def get_current_version(
    pyproject_path: Path,
    changelog_path: Path,
    repo_root: Path,
) -> str:
    candidates = [get_pyproject_version(pyproject_path)]
    candidates.extend(get_changelog_versions(changelog_path))
    candidates.extend(get_git_tag_versions(repo_root))
    return max(candidates, key=parse_version)


def infer_bump(changelog_dir: Path) -> str:
    fragments = [
        f for f in changelog_dir.iterdir() if f.is_file() and f.name != ".gitkeep"
    ]
    if not fragments:
        print("No changelog fragments found", file=sys.stderr)
        sys.exit(1)

    categories = {f.suffix.lstrip(".") for f in fragments}
    for f in fragments:
        parts = f.stem.split(".")
        if len(parts) >= 2:
            categories.add(parts[-1])

    if "breaking" in categories:
        return "major"
    if "added" in categories or "removed" in categories:
        return "minor"
    return "patch"


def bump_version(version: str, bump: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    elif bump == "minor":
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def update_file(path: Path, new_version: str):
    text = path.read_text()
    updated, replacements = re.subn(
        r'(^version\s*=\s*")(\d+\.\d+\.\d+)(")',
        rf"\g<1>{new_version}\g<3>",
        text,
        flags=re.MULTILINE,
    )
    if replacements == 0:
        print(
            f"Could not update version in {path}",
            file=sys.stderr,
        )
        sys.exit(1)
    if updated != text:
        path.write_text(updated)
        print(f"  Updated {path}")


def validate_vendored_bundle_version(repo_root: Path, new_version: str):
    bundle_path = repo_root / "src" / "policyengine" / "data" / "bundle.json"
    if not bundle_path.exists():
        print(
            f"Could not find vendored bundle manifest at {bundle_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    bundle = json.loads(bundle_path.read_text())
    bundle_version = bundle.get("bundle_version")
    policyengine_version = (bundle.get("policyengine") or {}).get("version")
    if bundle_version != new_version or policyengine_version != new_version:
        print(
            "Vendored bundle version must be updated before bumping "
            "policyengine.py: "
            f"expected {new_version}, got bundle_version={bundle_version}, "
            f"policyengine.version={policyengine_version}",
            file=sys.stderr,
        )
        sys.exit(1)


def vendored_bundle_matches(repo_root: Path, new_version: str) -> bool:
    bundle_path = repo_root / "src" / "policyengine" / "data" / "bundle.json"
    if not bundle_path.exists():
        return False
    bundle = json.loads(bundle_path.read_text())
    return (
        bundle.get("bundle_version") == new_version
        and (bundle.get("policyengine") or {}).get("version") == new_version
    )


def vendor_matching_bundle(repo_root: Path, new_version: str):
    if vendored_bundle_matches(repo_root, new_version):
        return
    subprocess.run(
        [
            sys.executable,
            str(repo_root / ".github" / "vendor_release_bundle.py"),
            "--version",
            new_version,
        ],
        cwd=repo_root,
        check=True,
    )


def main():
    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"
    changelog = root / "CHANGELOG.md"
    changelog_dir = root / "changelog.d"

    current = get_current_version(pyproject, changelog, root)
    bump = infer_bump(changelog_dir)
    new = bump_version(current, bump)

    print(f"Version: {current} -> {new} ({bump})")

    vendor_matching_bundle(root, new)
    validate_vendored_bundle_version(root, new)
    update_file(pyproject, new)


if __name__ == "__main__":
    main()
