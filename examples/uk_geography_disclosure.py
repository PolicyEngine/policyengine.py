"""Example: Publish area results under disclosure control.

This script demonstrates:
1. Building estimates for two geography levels from per-household arrays
2. Checking a release for numbers a reader could recover by subtraction
3. Resolving a finding by withholding the suggested cell
4. Writing the public table and validating its format

The data is synthetic, so the script needs no dataset.

Run: python examples/uk_geography_disclosure.py
"""

import tempfile
from pathlib import Path

import numpy as np

from policyengine.disclosure import (
    AreaWeights,
    Release,
    estimate_change,
    validate_public,
)


def main() -> Path:
    rng = np.random.default_rng(0)
    # Two regions of three seats, 400 households a seat. In seat S1 the
    # reform reaches only a handful of households.
    seats = np.repeat(["S1", "S2", "S3", "S4", "S5", "S6"], 400)
    regions = np.repeat(["North", "South"], 1_200)
    reach = np.where(seats == "S1", 0.01, np.where(seats == "S2", 0.08, 0.35))
    affected = rng.random(len(seats)) < reach
    weights = rng.uniform(150.0, 450.0, len(seats))
    baseline = rng.lognormal(10.4, 0.5, len(seats))
    reformed = baseline + np.where(affected, rng.uniform(100.0, 900.0, len(seats)), 0)
    source_ids = np.arange(len(seats))

    release = Release()
    for level, codes in (("region", regions), ("constituency", seats)):
        release.add(
            estimate_change(
                level=level,
                reform="example",
                year=2026,
                areas=AreaWeights.from_labels(codes, weights),
                source_ids=source_ids,
                baseline=baseline,
                reformed=reformed,
            )
        )
    release.add_nesting("constituency", "region")

    # S1 is withheld. Its region is public, so subtraction would recover it
    # unless a second seat is withheld too.
    for finding in release.check():
        print(f"{finding.code}: {finding.message} Suggested: {finding.suggested}")
        release.withhold(
            level="constituency",
            area_code=finding.suggested,
            reform="example",
            year=2026,
            outcome="average_change" if finding.family == "change" else finding.family,
        )
    assert release.check() == []

    public = release.to_public()
    frame = public.to_frame()
    print(
        frame[frame["outcome"] == "average_change"][
            ["level", "area_code", "value", "lo", "hi", "tier", "support_band"]
        ].to_string(index=False)
    )

    output = Path(tempfile.mkdtemp(prefix="disclosure-example-"))
    public.to_csv(output / "example.csv")
    assert validate_public(output) == []
    print(f"Wrote and validated {output / 'example.csv'}")
    return output


if __name__ == "__main__":
    main()
