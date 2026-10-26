"""Certify a country data release into the PolicyEngine bundle manifest.

Fetches the data release manifest, validates it with the selected
data-producer strategy, writes the certified data release into the canonical
bundle manifest, regenerates derived bundle metadata, and writes a Towncrier
changelog fragment.

Usage::

    python scripts/bundle.py certify-data --country uk --data-producer populace \\
        --manifest-uri "hf://dataset/policyengine/populace-uk-private@<cut-tag>/releases/<release-id>/release_manifest.json"

Pin the cut tag, never a branch: each cut rewrites ``releases/<release-id>/``.
Add ``--regional-manifest-uri`` to route local regions to a regional release
(see docs/engineering/skills/data-certification.md).

Private data (UK) requires ``HUGGING_FACE_TOKEN`` or ``HF_TOKEN`` in the
environment. After running: commit the changed bundle manifest, pyproject.toml,
changelog fragment, and any regenerated TRO sidecars, re-lock if pins moved,
and run the test suite. Certification is only asserted once the suite passes on
the exact pinned pair.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_bundle_artifacts import generate  # noqa: E402

from policyengine.provenance.certification import (  # noqa: E402
    REGIONAL_RELEASE_KINDS,
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
        "--regional-manifest-uri",
        default=None,
        help=(
            "Regional release_manifest.json URI whose dataset serves the local "
            "region types (US states and districts, UK constituencies and local "
            "authorities). Required on re-certification while the bundle routes "
            "regions, unless --drop-regional-release is given."
        ),
    )
    parser.add_argument(
        "--regional-release-kind",
        default="local_area",
        choices=REGIONAL_RELEASE_KINDS,
        help=(
            "local_area: a non-default local-area release. "
            "area_coded_national (UK only): another certified national release "
            "whose households carry area codes, such as the enhanced FRS; its "
            "national dataset and area weight matrices serve constituency and "
            "local-authority regions."
        ),
    )
    parser.add_argument(
        "--drop-regional-release",
        action="store_true",
        help=(
            "Remove the bundle's current regional routing on re-certification. "
            "Cannot be combined with --regional-manifest-uri."
        ),
    )
    parser.add_argument(
        "--regional-artifact-prefix",
        default="states/",
        help="Legacy per-state artifact path prefix to import. Defaults to states/.",
    )
    parser.add_argument(
        "--regional-path-template",
        default="states/{state_code}.h5",
        help="Legacy per-state dataset path template to certify.",
    )
    parser.add_argument(
        "--model-version",
        default=None,
        help="Model package version to certify for (default: installed).",
    )
    parser.add_argument(
        "--core-version",
        default=None,
        help=(
            "policyengine-core version to check against the release's core "
            "claims and pin in the bundle."
        ),
    )
    parser.add_argument(
        "--qualified-pair-id",
        default=None,
        help=(
            "Admit the exact model, core and data release on automated "
            "qualification of this pair (requires --core-version)."
        ),
    )
    parser.add_argument(
        "--accept-regional-model-mismatch",
        metavar="REASON",
        help=(
            "UK only: route regions to a regional release that does not cover "
            "the pinned model, recording this reviewed reason in the bundle "
            "instead of refusing. Requires --regional-input-surface-evidence; "
            "dropped columns (defined by the regional build model, not by the "
            "pinned model) refuse. The core must still be covered."
        ),
    )
    parser.add_argument("--no-generate", action="store_true")
    parser.add_argument(
        "--regional-input-surface-evidence",
        type=Path,
        help=(
            "Audit JSON from scripts/audit_regional_input_surface.py, bound to "
            "the regional bytes, its build model and the exact target model."
        ),
    )
    parser.add_argument("--no-changelog", action="store_true")
    parser.add_argument(
        "--skip-artifact-check",
        action="store_true",
        help=(
            "Skip reachability HEAD checks for the certified dataset and any "
            "vendored/regional artifacts."
        ),
    )
    args = parser.parse_args(argv)

    token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")

    result = certify_data_release(
        country=args.country,
        data_producer=args.data_producer,
        manifest_uri=args.manifest_uri,
        model_version=args.model_version,
        token=token,
        bundle_path=REPO_ROOT
        / "src"
        / "policyengine"
        / "data"
        / "bundle"
        / "manifest.json",
        check_artifacts=not args.skip_artifact_check,
        regional_manifest_uri=args.regional_manifest_uri,
        regional_artifact_prefix=args.regional_artifact_prefix,
        regional_path_template=args.regional_path_template,
        regional_release_kind=args.regional_release_kind,
        drop_regional_release=args.drop_regional_release,
        core_version=args.core_version,
        qualified_pair_id=args.qualified_pair_id,
        regional_model_mismatch_reason=args.accept_regional_model_mismatch,
        regional_input_surface_evidence=(
            json.loads(args.regional_input_surface_evidence.read_text())
            if args.regional_input_surface_evidence is not None
            else None
        ),
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
