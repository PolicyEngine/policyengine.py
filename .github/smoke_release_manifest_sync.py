"""Smoke test release manifest version syncing against sample data.

This script copies the checked-in release manifests to a temporary directory,
applies the release-version sync to the copy, and prints before/after summaries
plus unified diffs. It intentionally never writes to the repository manifests.
"""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST_DIR = REPO_ROOT / "src" / "policyengine" / "data" / "release_manifests"
BUMP_VERSION_SCRIPT = REPO_ROOT / ".github" / "bump_version.py"
DEFAULT_TARGET_VERSION = "9.8.7"


def load_sync_release_manifest_versions() -> Callable[[Path, str], None]:
    spec = importlib.util.spec_from_file_location(
        "policyengine_bump_version",
        BUMP_VERSION_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {BUMP_VERSION_SCRIPT}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.sync_release_manifest_versions


def manifest_summary(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    return {
        "file": manifest_path.name,
        "country_id": manifest.get("country_id", manifest_path.stem),
        "bundle_id": manifest.get("bundle_id"),
        "policyengine_version": manifest.get("policyengine_version"),
    }


def print_manifest_summaries(title: str, sample_dir: Path) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for path in sorted(sample_dir.glob("*.json")):
        summary = manifest_summary(path)
        print(
            f"{summary['file']}: "
            f"country_id={summary['country_id']}; "
            f"bundle_id={summary['bundle_id']}; "
            f"policyengine_version={summary['policyengine_version']}"
        )


def copy_sample_manifests(sample_dir: Path) -> dict[str, str]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    before: dict[str, str] = {}
    source_paths = sorted(SOURCE_MANIFEST_DIR.glob("*.json"))
    if not source_paths:
        raise RuntimeError(f"No release manifests found in {SOURCE_MANIFEST_DIR}")

    for source_path in source_paths:
        sample_path = sample_dir / source_path.name
        shutil.copy2(source_path, sample_path)
        before[sample_path.name] = sample_path.read_text()

    return before


def unified_diff(
    manifest_name: str,
    before_text: str,
    after_text: str,
) -> str:
    diff = difflib.unified_diff(
        before_text.splitlines(keepends=True),
        after_text.splitlines(keepends=True),
        fromfile=f"sample/{manifest_name} before",
        tofile=f"sample/{manifest_name} after",
    )
    return "".join(diff)


def validate_sample_manifests(sample_dir: Path, target_version: str) -> None:
    errors: list[str] = []
    for path in sorted(sample_dir.glob("*.json")):
        manifest = json.loads(path.read_text())
        country_id = manifest.get("country_id", path.stem)
        expected_bundle_id = f"{country_id}-{target_version}"
        if manifest.get("bundle_id") != expected_bundle_id:
            errors.append(
                f"{path.name}: bundle_id={manifest.get('bundle_id')!r}, "
                f"expected {expected_bundle_id!r}"
            )
        if manifest.get("policyengine_version") != target_version:
            errors.append(
                f"{path.name}: "
                f"policyengine_version={manifest.get('policyengine_version')!r}, "
                f"expected {target_version!r}"
            )

    if errors:
        print("\nValidation errors")
        print("-----------------")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)


def append_step_summary(
    sample_dir: Path,
    target_version: str,
    diffs: dict[str, str],
) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    lines = [
        "## Release Manifest Sync Smoke",
        "",
        f"Sample directory: `{sample_dir}`",
        f"Synthetic target version: `{target_version}`",
        "",
        "| Manifest | Country | Bundle ID | policyengine_version |",
        "| --- | --- | --- | --- |",
    ]
    for path in sorted(sample_dir.glob("*.json")):
        summary = manifest_summary(path)
        lines.append(
            "| {file} | {country_id} | `{bundle_id}` | `{policyengine_version}` |".format(
                **summary,
            )
        )

    lines.extend(["", "### Diffs", ""])
    for manifest_name, diff in diffs.items():
        lines.extend(
            [
                f"#### {manifest_name}",
                "",
                "```diff",
                diff.strip() or "No diff",
                "```",
                "",
            ]
        )

    Path(summary_path).write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy bundled release manifests to sample data and show how "
            "release-version syncing would update them."
        )
    )
    parser.add_argument(
        "--target-version",
        default=DEFAULT_TARGET_VERSION,
        help=("Synthetic policyengine.py version to apply to the sample manifests."),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sync_release_manifest_versions = load_sync_release_manifest_versions()

    with tempfile.TemporaryDirectory(prefix="policyengine-manifest-sync-") as temp:
        sample_dir = Path(temp) / "release_manifests"
        before = copy_sample_manifests(sample_dir)

        print("Release manifest sync smoke test")
        print("================================")
        print(f"Repository root: {REPO_ROOT}")
        print(f"Source manifest directory: {SOURCE_MANIFEST_DIR}")
        print(f"Sample manifest directory: {sample_dir}")
        print(f"Synthetic target version: {args.target_version}")
        print("Only files in the temporary sample directory are modified by this test.")

        print_manifest_summaries("Before sync", sample_dir)
        sync_release_manifest_versions(sample_dir, args.target_version)
        print_manifest_summaries("After sync", sample_dir)

        print("\nUnified diffs")
        print("-------------")
        diffs: dict[str, str] = {}
        changed_count = 0
        for sample_path in sorted(sample_dir.glob("*.json")):
            after_text = sample_path.read_text()
            diff = unified_diff(sample_path.name, before[sample_path.name], after_text)
            diffs[sample_path.name] = diff
            if diff:
                changed_count += 1
            print(f"\n### {sample_path.name}")
            print(diff or "No diff")

        if changed_count == 0:
            raise SystemExit(
                "Expected sample manifests to change, but no diffs were produced."
            )

        validate_sample_manifests(sample_dir, args.target_version)
        append_step_summary(sample_dir, args.target_version, diffs)

        print("\nValidation")
        print("----------")
        print(
            f"Updated {changed_count} sample manifest(s) to "
            f"policyengine.py {args.target_version}."
        )


if __name__ == "__main__":
    main()
