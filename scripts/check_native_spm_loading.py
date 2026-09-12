"""Run the producer's four-wheel native-input qualification without publication.

Run only after installing the four candidate wheels in an isolated environment.
The wrapper must import from its installed wheel, never a checkout PYTHONPATH.
The explicit development bootstrap does not certify data or published packages.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_derived_weights(path: Path) -> dict[str, int]:
    """Check household weight projection with one additional read-only load."""
    import numpy as np

    from policyengine.tax_benefit_models.us.datasets import PolicyEngineUSDataset

    dataset = PolicyEngineUSDataset(
        name="native_spm_weight_qualification",
        description="Read-only mapping check; not population model acceptance",
        filepath=str(path),
        year=2024,
    )
    import pandas as pd

    # This is an ID/array qualification, never a population poverty statistic.
    person = pd.DataFrame(dataset.data.person)
    household = pd.DataFrame(dataset.data.household)
    lookup = household.set_index("household_id")["household_weight"]
    counts = {}
    for entity, frame in dataset.data.entity_data.items():
        frame = pd.DataFrame(frame)
        counts[entity] = len(frame)
        if entity == "household":
            continue
        if entity == "person":
            expected = person["person_household_id"].map(lookup)
        else:
            link = f"person_{entity}_id"
            relationships = person[[link, "person_household_id"]].drop_duplicates()
            assert not relationships[link].duplicated().any()
            group_households = relationships.set_index(link)["person_household_id"]
            expected = frame[f"{entity}_id"].map(group_households).map(lookup)
        if not np.array_equal(
            frame[f"{entity}_weight"].to_numpy(), expected.to_numpy()
        ):
            raise ValueError(
                f"Wrapper {entity} weights do not match household projection"
            )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-h5", required=True, type=Path)
    parser.add_argument("--producer-src", required=True, type=Path)
    parser.add_argument("--development-manifest", required=True, type=Path)
    parser.add_argument("--wheel", required=True, action="append", type=Path)
    parser.add_argument("--check-derived-weights", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        parser.error("Output must be a new diagnostic file")

    # Import the producer read-only. This path contains Microcosm only, so
    # installed-wrapper source ownership remains independently verifiable.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.producer_src.resolve(strict=True)))
    helper = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "spm_development.py"
    )
    spec = importlib.util.spec_from_file_location("spm_qualification_bootstrap", helper)
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    bootstrap.activate_spm_development_manifest(args.development_manifest)

    from microcosm.data.source_enrichment import run_native_loader_compatibility

    before = sha256_file(args.candidate_h5)
    try:
        receipt = run_native_loader_compatibility(
            args.candidate_h5,
            require_wheels=True,
            compatibility_wheels=tuple(args.wheel),
        )
        weight_check = (
            check_derived_weights(args.candidate_h5)
            if args.check_derived_weights
            else None
        )
    finally:
        after = sha256_file(args.candidate_h5)
        if after != before:
            raise RuntimeError("Native candidate H5 changed during qualification")
    report = {
        "scope": "read_only_native_input_qualification",
        "data_certification": "not_certified",
        "external_package_publication": "not_attested",
        "canonical_spm_model_acceptance": "not_attested",
        "candidate_sha256_before": before,
        "candidate_sha256_after": after,
        "development_manifest": {
            "path": str(args.development_manifest.resolve()),
            "sha256": sha256_file(args.development_manifest),
        },
        "probe_sha256": sha256_file(Path(__file__)),
        "derived_weight_check": weight_check,
        "producer_compatibility": receipt,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
