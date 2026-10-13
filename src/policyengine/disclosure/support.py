"""Support behind a number: how many source households it rests on.

One function serves a cell, the two sides of a share, and a remainder that a
reader could recover by subtraction. Clones and copies of one survey household
count once: weights and contributions are summed by source first.
"""

import math
from typing import NamedTuple, Optional

import numpy as np

from .schema import (
    APPROXIMATE,
    BAND_10_TO_29,
    BAND_30_PLUS,
    BAND_UNDER_10,
    FAMILY_CHANGE,
    PRIVATE_BELOW_FLOOR,
    PRIVATE_DOMINANT,
    PRIVATE_LOW_N_EFF,
    REASON_THIN_SUPPORT,
    REPORTED,
    WITHHELD,
    DisclosureSettings,
)


class Support(NamedTuple):
    n_sources: int
    n_eff: float
    top_share: float
    rest_share: float = math.inf


NO_SUPPORT = Support(0, 0.0, 0.0)


def support(
    weights: np.ndarray, contributions: np.ndarray, source_index: np.ndarray
) -> Support:
    """Support of one cell, from aligned per-record arrays.

    A record contributes when it has weight and a non-zero contribution.
    """
    contributing = (weights > 0) & (contributions != 0)
    if not contributing.any():
        return NO_SUPPORT
    _, by_source = np.unique(source_index[contributing], return_inverse=True)
    weighted = weights[contributing] * contributions[contributing]
    source_weight = np.bincount(by_source, weights=weights[contributing])
    magnitude = np.bincount(by_source, weights=np.abs(weighted))
    n_eff = float(source_weight.sum() ** 2 / (source_weight**2).sum())
    top_share = float(magnitude.max() / magnitude.sum())
    signed = np.bincount(by_source, weights=weighted)
    return Support(len(source_weight), n_eff, top_share, _rest_share(signed))


def _rest_share(signed: np.ndarray) -> float:
    """The rest of a total next to its largest household: the p% measure.

    ``top_share`` works on magnitudes, so it misses a total whose other parts
    cancel: the total is then one household's contribution. This measure
    works on the signed total. It takes what is left without the largest
    household, and what is left without the two largest, as a share of the
    largest household's part. A small value means the number gives that part
    away, to any reader or to the second-largest household.
    """
    order = np.argsort(-np.abs(signed))
    largest = abs(float(signed[order[0]]))
    if largest == 0:
        return math.inf
    total = float(signed.sum())
    without_one = abs(total - float(signed[order[0]]))
    without_two = abs(total - float(signed[order[:2]].sum()))
    return min(without_one, without_two) / largest


def family_supports(
    weights: np.ndarray,
    contributions: np.ndarray,
    source_index: np.ndarray,
    family: str,
) -> tuple[Support, ...]:
    """The supports a family's cell must pass: one for a change, two for a share."""
    cell = support(weights, contributions, source_index)
    if family == FAMILY_CHANGE:
        return (cell,)
    complement = (contributions == 0).astype(float)
    return (cell, support(weights, complement, source_index))


def primary_tier(
    cell: Support,
    settings: DisclosureSettings,
    *,
    one_area_per_record: bool,
    noise: bool,
) -> tuple[str, Optional[str]]:
    """Tier and private reason of one side. The count rule comes first."""
    if cell.n_sources == 0:
        return REPORTED, None
    if cell.n_sources < settings.min_sources:
        return WITHHELD, PRIVATE_BELOW_FLOOR
    if not one_area_per_record and cell.n_eff < settings.min_n_eff:
        return WITHHELD, PRIVATE_LOW_N_EFF
    dominated = (
        cell.top_share > settings.max_top_share
        or cell.rest_share < settings.min_rest_share
    )
    if not noise and dominated:
        return WITHHELD, PRIVATE_DOMINANT
    if cell.n_eff < settings.approximate_below_n_eff:
        return APPROXIMATE, REASON_THIN_SUPPORT
    return REPORTED, None


def binding_support(supports: tuple[Support, ...]) -> Support:
    """The weakest non-empty side, which sets the band and the audit columns."""
    present = [cell for cell in supports if cell.n_sources > 0]
    if not present:
        return NO_SUPPORT
    return min(present, key=lambda cell: (cell.n_sources, cell.n_eff))


def cell_tier(
    supports: tuple[Support, ...],
    settings: DisclosureSettings,
    *,
    one_area_per_record: bool,
    noise: bool,
) -> tuple[str, Optional[str]]:
    """Tier of a cell from all its sides: the worst side decides."""
    tier: str = REPORTED
    reason: Optional[str] = None
    for cell in supports:
        side_tier, side_reason = primary_tier(
            cell, settings, one_area_per_record=one_area_per_record, noise=noise
        )
        if side_tier == WITHHELD:
            return side_tier, side_reason
        if side_tier == APPROXIMATE:
            tier, reason = side_tier, side_reason
    return tier, reason


def support_band(cell: Support, *, one_area_per_record: bool) -> str:
    """The published band. It never shows an exact count."""
    basis = cell.n_sources if one_area_per_record else cell.n_eff
    if basis < 10:
        return BAND_UNDER_10
    if basis < 30:
        return BAND_10_TO_29
    return BAND_30_PLUS
