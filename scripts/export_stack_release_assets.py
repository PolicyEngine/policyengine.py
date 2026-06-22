"""Export bundle metadata files for the GitHub release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_stack_artifacts import REPO_ROOT, STACK_MANIFEST


def _write_json_aliases(
    dist_dir: Path, names: list[str], payload: object
) -> list[Path]:
    paths = [dist_dir / name for name in names]
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    for path in paths:
        path.write_text(text)
    return paths


def _write_text_aliases(dist_dir: Path, names: list[str], text: str) -> list[Path]:
    paths = [dist_dir / name for name in names]
    for path in paths:
        path.write_text(text)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=REPO_ROOT / "dist")
    args = parser.parse_args()

    stack = json.loads(STACK_MANIFEST.read_text())
    version = stack.get("bundle_version") or stack["stack_version"]
    args.dist_dir.mkdir(parents=True, exist_ok=True)

    manifest_paths = _write_json_aliases(
        args.dist_dir,
        [
            f"policyengine-bundle-{version}.json",
            f"policyengine-stack-{version}.json",
        ],
        stack,
    )

    full_packages = ["policyengine", *stack["extras"]["full"]]
    constraints = [
        stack["packages"][package]["install_requirement"] for package in full_packages
    ]
    constraints_paths = _write_text_aliases(
        args.dist_dir,
        [
            f"policyengine-bundle-{version}.constraints.txt",
            f"policyengine-stack-{version}.constraints.txt",
        ],
        "\n".join(constraints) + "\n",
    )

    citation_paths = _write_text_aliases(
        args.dist_dir,
        [
            f"policyengine-bundle-{version}.citation.txt",
            f"policyengine-stack-{version}.citation.txt",
        ],
        "\n".join(
            [
                f"PolicyEngine bundle {version}",
                f"PolicyEngine package version: {stack['policyengine_version']}",
                "Components:",
                *(
                    f"- {component['name']} {component['version']}"
                    for _, component in sorted(stack["packages"].items())
                ),
            ]
        )
        + "\n",
    )

    for path in [*manifest_paths, *constraints_paths, *citation_paths]:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
