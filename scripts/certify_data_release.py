"""Certify a country data release from its HF release manifest.

Replaces the policyengine-bundles import flow: fetches the data release
manifest, validates it, writes the vendored country manifest, exact-pins
the country model package in ``pyproject.toml``, regenerates the TRACE
TRO sidecar, and writes a Towncrier changelog fragment.

Usage::

    python scripts/certify_data_release.py --country us \\
        --manifest-uri "hf://dataset/policyengine/populace-us@<tag>/releases/<tag>/release_manifest.json"

Private data (UK) requires ``HUGGING_FACE_TOKEN`` or ``HF_TOKEN`` in the
environment. After running: commit the changed manifest / TRO /
pyproject.toml / changelog fragment, re-lock if pins moved, and run the
test suite — certification is only asserted once the suite passes on the
exact pinned pair.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from policyengine.provenance.certification import (  # noqa: E402
    certify_data_release,
)
from policyengine.provenance.pyproject_pins import (  # noqa: E402
    update_country_pins,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Certify a country data release.")
    parser.add_argument("--country", required=True, choices=["us", "uk"])
    parser.add_argument(
        "--manifest-uri",
        required=True,
        help="hf://dataset/<repo_id>@<revision>/<path-to-release_manifest.json>",
    )
    parser.add_argument(
        "--model-version",
        default=None,
        help="Model package version to certify for (default: installed).",
    )
    parser.add_argument("--no-pyproject", action="store_true")
    parser.add_argument("--no-tro", action="store_true")
    parser.add_argument("--no-changelog", action="store_true")
    parser.add_argument(
        "--skip-artifact-check",
        action="store_true",
        help="Skip the reachability HEAD on the certified dataset.",
    )
    args = parser.parse_args(argv)

    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")

    result = certify_data_release(
        country=args.country,
        manifest_uri=args.manifest_uri,
        model_version=args.model_version,
        token=token,
        check_artifacts=not args.skip_artifact_check,
    )
    print(result.summary())

    if not args.no_pyproject:
        from importlib.metadata import version as installed_version

        update_country_pins(
            pyproject_path=REPO_ROOT / "pyproject.toml",
            country=args.country,
            model_package=result.model_package,
            model_version=result.model_version,
            core_version=installed_version("policyengine_core"),
        )
        print(f"pinned {result.model_package}=={result.model_version}")

    if not args.no_tro:
        from policyengine.provenance.bundle import regenerate_trace_tro

        tro_path = regenerate_trace_tro(
            args.country, result.country_manifest_path.parent
        )
        print(f"trace tro: {tro_path}")

    if not args.no_changelog:
        changelog_dir = REPO_ROOT / "changelog.d"
        changelog_dir.mkdir(exist_ok=True)
        fragment = (
            changelog_dir
            / f"certify-{args.country}-{result.build_id or 'data'}.changed.md"
        )
        fragment.write_text(
            f"Certify the {args.country.upper()} data release "
            f"`{result.build_id}` ({result.default_dataset}, "
            f"{result.model_package} {result.model_version}) directly from "
            "its data release manifest.\n"
        )
        print(f"changelog: {fragment}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
