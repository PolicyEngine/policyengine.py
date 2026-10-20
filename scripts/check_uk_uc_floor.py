"""Check a UK dataset against the Universal Credit coverage floor.

Usage::

    python scripts/check_uk_uc_floor.py --dataset <bundle dataset name or .h5 path> \\
        [--year 2025] [--output receipt.json]

A bundle dataset name (for example ``enhanced_frs_2024_25``) is materialized
from the certified bundle; private UK data needs ``HUGGING_FACE_TOKEN``. Exits
non-zero when either measure is outside the tolerance. The receipt holds
weighted national totals only, so it can be attached to a certification PR.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from policyengine.provenance.uk_uc_floor import check_uc_floor  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dataset",
        required=True,
        help="A bundle dataset name or a local UK dataset .h5 path.",
    )
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--output", type=Path, help="Write the JSON receipt here.")
    args = parser.parse_args(argv)

    if Path(args.dataset).expanduser().is_file():
        dataset_path = str(Path(args.dataset).expanduser())
        dataset = Path(dataset_path).name
    else:
        from policyengine.provenance.dataset_materialization import (
            materialize_dataset,
        )

        source = materialize_dataset("uk", args.dataset)
        dataset_path, dataset = source.path, source.source_uri

    receipt = check_uc_floor(dataset_path, args.year, dataset=dataset)
    text = receipt.model_dump_json(indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)
    return 0 if receipt.passed else 1


if __name__ == "__main__":
    sys.exit(main())
