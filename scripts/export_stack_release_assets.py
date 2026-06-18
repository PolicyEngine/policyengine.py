"""Export stack metadata files for the GitHub release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_stack_artifacts import REPO_ROOT, STACK_MANIFEST


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=REPO_ROOT / "dist")
    args = parser.parse_args()

    stack = json.loads(STACK_MANIFEST.read_text())
    version = stack["stack_version"]
    args.dist_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = args.dist_dir / f"policyengine-stack-{version}.json"
    manifest_path.write_text(json.dumps(stack, indent=2, sort_keys=True) + "\n")

    constraints_path = args.dist_dir / f"policyengine-stack-{version}.constraints.txt"
    full_packages = ["policyengine", *stack["extras"]["full"]]
    constraints = [
        stack["packages"][package]["install_requirement"] for package in full_packages
    ]
    constraints_path.write_text("\n".join(constraints) + "\n")

    citation_path = args.dist_dir / f"policyengine-stack-{version}.citation.txt"
    citation_path.write_text(
        "\n".join(
            [
                f"PolicyEngine stack {version}",
                f"PolicyEngine package version: {stack['policyengine_version']}",
                "Components:",
                *(
                    f"- {component['name']} {component['version']}"
                    for _, component in sorted(stack["packages"].items())
                ),
            ]
        )
        + "\n"
    )

    print(manifest_path)
    print(constraints_path)
    print(citation_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
