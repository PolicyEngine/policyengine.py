"""Disclosure control and uncertainty for area-level outputs.

Survey microdata under a licence binds every published number. This package
turns per-record results into area tables that carry the licence's rules: a
floor on the number of distinct survey households behind a number, a dominance
rule or keyed noise, bootstrap intervals, precision-adaptive rounding, and a
check on what a reader can recover by subtraction.

The package is self-contained. It works on arrays and imports nothing from
the rest of the library, so it can be lifted into its own distribution.

.. code-block:: python

    from policyengine.disclosure import AreaWeights, Release, estimate_change

    seats = estimate_change(
        level="constituency",
        reform="budget",
        year=2026,
        areas=AreaWeights.from_labels(seat_codes, household_weights),
        source_ids=source_household_ids,
        baseline=baseline_net_income,
        reformed=reformed_net_income,
    )
    release = Release()
    release.add(seats)
    findings = release.check()
    public = release.to_public()  # raises while a blocking finding remains
"""

from .areas import UNASSIGNED as UNASSIGNED
from .areas import AreaWeights as AreaWeights
from .estimate import AreaEstimates as AreaEstimates
from .estimate import estimate_change as estimate_change
from .noise import NOISE_KEY_ENV as NOISE_KEY_ENV
from .noise import DisclosureKeyError as DisclosureKeyError
from .noise import noise_factors as noise_factors
from .noise import resolve_noise_key as resolve_noise_key
from .release import DisclosureError as DisclosureError
from .release import Release as Release
from .schema import DisclosureSettings as DisclosureSettings
from .schema import Finding as Finding
from .schema import PriorPublic as PriorPublic
from .schema import PublicRow as PublicRow
from .schema import PublicTable as PublicTable
from .validate import validate_public as validate_public

__all__ = [
    "NOISE_KEY_ENV",
    "UNASSIGNED",
    "AreaEstimates",
    "AreaWeights",
    "DisclosureError",
    "DisclosureKeyError",
    "DisclosureSettings",
    "Finding",
    "PriorPublic",
    "PublicRow",
    "PublicTable",
    "Release",
    "estimate_change",
    "noise_factors",
    "resolve_noise_key",
    "validate_public",
]
