"""CLI wrapper around :func:`policyengine.provenance.refresh_release_bundle`.

Usage::

    python scripts/refresh_release_bundle.py --country us \\
        --model-version 1.653.3 --data-version 1.83.4

Fetches PyPI wheel metadata and streams the HF dataset to compute its
sha256, then writes updated ``data/release_manifests/{country}.json``,
bumps the matching pin in ``pyproject.toml`` (unless
``--no-pyproject``), and regenerates the bundle's TRACE TRO sidecar
(unless ``--no-tro``).

Private HF datasets require ``HUGGING_FACE_TOKEN`` in the env.

After running:

- commit the changed manifest / TRO / pyproject.toml,
- manually rerun
  ``PE_UPDATE_SNAPSHOTS=1 pytest tests/test_household_calculator_snapshot.py``
  to rebaseline expected household outputs — those numbers will
  almost certainly drift when the data version bumps, and the drift
  deserves human review before being committed.
"""

from __future__ import annotations

import argparse
import sys

from policyengine.provenance.bundle import (
    refresh_release_bundle,
    regenerate_trace_tro,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", required=True, choices=("us", "uk"))
    parser.add_argument(
        "--model-version",
        help="New policyengine-{country} version (e.g. 1.653.3)",
    )
    parser.add_argument(
        "--data-version",
        help="New policyengine-{country}-data version (e.g. 1.83.4)",
    )
    parser.add_argument(
        "--no-pyproject",
        action="store_true",
        help="Do not bump the country extra in pyproject.toml",
    )
    parser.add_argument(
        "--no-tro",
        action="store_true",
        help="Skip TRACE TRO regeneration",
    )
    args = parser.parse_args(argv)

    if args.model_version is None and args.data_version is None:
        parser.error("Pass at least --model-version or --data-version")

    result = refresh_release_bundle(
        country=args.country,
        model_version=args.model_version,
        data_version=args.data_version,
        update_pyproject=not args.no_pyproject,
    )
    print(result.summary())

    if not args.no_tro:
        tro_path = regenerate_trace_tro(args.country)
        print(f"  TRO regenerated: {tro_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
