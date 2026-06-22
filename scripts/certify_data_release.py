"""Certify a country data release into policyengine-bundle.json.

Fetches the data release manifest, validates it with the selected
data-producer strategy, writes the certified data release into the bundle JSON
source, regenerates packaged bundle artifacts, and writes a Towncrier changelog
fragment.

Usage::

    python scripts/certify_data_release.py --country uk --data-producer populace \\
        --manifest-uri "hf://dataset/policyengine/populace-uk-private@<tag>/releases/<tag>/release_manifest.json"

Private data (UK) requires ``HUGGING_FACE_TOKEN`` or ``HF_TOKEN`` in the
environment. After running: commit the changed bundle JSON / generated bundle
manifest / pyproject.toml / changelog fragment, re-lock if pins moved, and run
the test suite. Certification is only asserted once the suite passes on the
exact pinned pair.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_bundle_artifacts import generate  # noqa: E402

from policyengine.provenance.certification import (  # noqa: E402
    certify_data_release,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Certify a country data release.")
    parser.add_argument("--country", required=True, choices=["us", "uk"])
    parser.add_argument(
        "--data-producer",
        default=None,
        choices=["legacy", "populace"],
        help="Data-producer strategy. Defaults to populace for UK, legacy otherwise.",
    )
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
    parser.add_argument("--no-generate", action="store_true")
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
        data_producer=args.data_producer,
        manifest_uri=args.manifest_uri,
        model_version=args.model_version,
        token=token,
        bundle_path=REPO_ROOT / "policyengine-bundle.json",
        check_artifacts=not args.skip_artifact_check,
    )
    print(result.summary())

    if not args.no_generate:
        generate(check=False)

    if not args.no_changelog:
        changelog_dir = REPO_ROOT / "changelog.d"
        changelog_dir.mkdir(exist_ok=True)
        fragment = (
            changelog_dir
            / f"certify-{args.country}-{result.build_id or 'data'}.changed.md"
        )
        fragment.write_text(
            f"Certify the {args.country.upper()} {result.data_producer} "
            f"data release `{result.build_id}` ({result.default_dataset}, "
            f"{result.model_package} {result.model_version}) into the "
            "PolicyEngine bundle manifest.\n"
        )
        print(f"changelog: {fragment}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
