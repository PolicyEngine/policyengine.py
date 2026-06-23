"""Export bundle metadata files for the GitHub release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_bundle_artifacts import BUNDLE_MANIFEST, REPO_ROOT


def _write_json(dist_dir: Path, name: str, payload: object) -> Path:
    path = dist_dir / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _write_text(dist_dir: Path, name: str, text: str) -> Path:
    path = dist_dir / name
    path.write_text(text)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=REPO_ROOT / "dist")
    args = parser.parse_args()

    bundle = json.loads(BUNDLE_MANIFEST.read_text())
    version = bundle["bundle_version"]
    args.dist_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = _write_json(
        args.dist_dir,
        f"policyengine-bundle-{version}.json",
        bundle,
    )

    constraint_packages = [
        name
        for name, component in bundle["packages"].items()
        if component.get("installable") is not False
    ]
    constraints = [
        bundle["packages"][package]["install_requirement"]
        for package in constraint_packages
    ]
    constraints_path = _write_text(
        args.dist_dir,
        f"policyengine-bundle-{version}.constraints.txt",
        "\n".join(constraints) + "\n",
    )

    citation_path = _write_text(
        args.dist_dir,
        f"policyengine-bundle-{version}.citation.txt",
        "\n".join(
            [
                f"PolicyEngine bundle {version}",
                f"PolicyEngine package version: {bundle['policyengine_version']}",
                "Components:",
                *(
                    f"- {component['name']} {component['version']}"
                    for _, component in sorted(bundle["packages"].items())
                ),
            ]
        )
        + "\n",
    )

    for path in (manifest_path, constraints_path, citation_path):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
