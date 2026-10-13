"""Private estimates for one geography level, reform and year.

Everything here is private: exact values, counts and shares. Only a
:class:`~.release.Release` turns estimates into rows that may be published.
"""

import math
import warnings
from typing import Optional, Union

import numpy as np
import pandas as pd

from .areas import AreaWeights
from .noise import canonical_source_ids, noise_factors, resolve_noise_key
from .schema import (
    APPROXIMATE,
    AVERAGE_CHANGE,
    CHANGE_OUTCOMES,
    FAMILIES,
    FAMILY_CHANGE,
    FAMILY_GAINING,
    FAMILY_LOSING,
    GAIN,
    LOSS,
    NO_CHANGE,
    PRIVATE_SHARE_SPLIT,
    PRIVATE_UNDEFINED,
    REASON_THIN_SUPPORT,
    RELATIVE_CHANGE,
    REPORTED,
    SHARE_GAINING,
    SHARE_LOSING,
    SHARE_NO_CHANGE,
    TOO_CLOSE_TO_CALL,
    TOTAL_CHANGE,
    WITHHELD,
    DisclosureSettings,
)
from .support import (
    Support,
    binding_support,
    cell_tier,
    family_supports,
    primary_tier,
    support,
    support_band,
)

_REPLICATE_CHUNK = 100
_TIER_ORDER = {REPORTED: 0, APPROXIMATE: 1, WITHHELD: 2}


class AreaEstimates:
    """Estimates and support for the areas of one level. Private.

    The object holds exact values, household counts and, with noise on, the
    noise factor of every household that gains or loses. Within one dataset
    those factors do the same job as the key, so treat the object as you treat
    the key: keep it in memory, and let a release write the audit.
    """

    def __init__(
        self,
        *,
        level: str,
        reform: str,
        year: int,
        areas: AreaWeights,
        source_index: np.ndarray,
        settings: DisclosureSettings,
        noise: bool,
        contributions: dict[str, np.ndarray],
        table: pd.DataFrame,
    ) -> None:
        self.level = level
        self.reform = reform
        self.year = year
        self.areas = areas
        self.settings = settings
        self.noise = noise
        self._source_index = source_index
        self._contributions = contributions
        self._table = table

    def __repr__(self) -> str:
        # The table holds exact values and counts, so it stays out of reprs.
        return (
            f"AreaEstimates(level={self.level!r}, reform={self.reform!r}, "
            f"year={self.year!r}, areas={self.areas.n_areas}, private)"
        )

    def __getstate__(self) -> dict:
        raise TypeError(
            "AreaEstimates holds exact values and noise factors, so it cannot "
            "be pickled or copied. Use Release.write_audit for a private record."
        )

    def family_tiers(self, family: str) -> dict[str, str]:
        """The primary tier of each area's cell in one family."""
        outcome = AVERAGE_CHANGE if family == FAMILY_CHANGE else family
        rows = self._table[self._table["outcome"] == outcome]
        return dict(zip(rows["area_code"], rows["family_tier"]))

    def family_sources(self, family: str) -> dict[str, int]:
        outcome = AVERAGE_CHANGE if family == FAMILY_CHANGE else family
        rows = self._table[self._table["outcome"] == outcome]
        return dict(zip(rows["area_code"], rows["n_sources"]))


def _per_record(values: object, n_records: int, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.shape != (n_records,):
        raise ValueError(f"{name} must have one entry per record.")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must be finite.")
    return array


def _rounding_base(standard_error: float, minimum: float) -> float:
    """The order of magnitude of the standard error, never below the minimum."""
    if not math.isfinite(standard_error) or standard_error <= 0:
        return minimum
    return max(10.0 ** math.floor(math.log10(standard_error)), minimum)


def _round(value: float, base: float, mode: str = "nearest") -> float:
    quotient = value / base
    if mode == "down":
        steps = math.floor(quotient + 1e-9)
    elif mode == "up":
        steps = math.ceil(quotient - 1e-9)
    else:
        steps = round(quotient)
    digits = max(0, -int(round(math.log10(base))))
    return round(steps * base, digits) + 0.0


def _replicates(
    areas: AreaWeights,
    contributions: dict[str, np.ndarray],
    baseline: np.ndarray,
    source_index: np.ndarray,
    n_sources: int,
    settings: DisclosureSettings,
) -> dict[str, np.ndarray]:
    """Poisson bootstrap over source households: areas x replicates per outcome.

    A replicate reweights every record of a source household by one draw. A
    ratio resamples its numerator and denominator with the same draws.
    """
    rng = np.random.default_rng(settings.bootstrap_seed)
    ones = np.ones(areas.n_records)
    out: dict[str, list[np.ndarray]] = {
        outcome: []
        for outcome in (*CHANGE_OUTCOMES, SHARE_GAINING, SHARE_LOSING, SHARE_NO_CHANGE)
    }
    done = 0
    while done < settings.n_replicates:
        size = min(_REPLICATE_CHUNK, settings.n_replicates - done)
        done += size
        # Replicate-major draws, so the result does not depend on the chunk.
        draws = rng.poisson(1.0, size=(size, n_sources)).astype(np.uint8)
        multipliers = draws[:, source_index]
        change = areas.totals(contributions[FAMILY_CHANGE], multipliers)
        households = areas.totals(ones, multipliers)
        income = areas.totals(baseline, multipliers)
        gaining = areas.totals(contributions[FAMILY_GAINING], multipliers)
        losing = areas.totals(contributions[FAMILY_LOSING], multipliers)
        with np.errstate(divide="ignore", invalid="ignore"):
            share_gaining = np.clip(gaining / households, 0.0, 1.0)
            share_losing = np.clip(losing / households, 0.0, 1.0 - share_gaining)
            out[AVERAGE_CHANGE].append(change / households)
            out[RELATIVE_CHANGE].append(np.where(income > 0, change / income, np.nan))
        out[TOTAL_CHANGE].append(change)
        out[SHARE_GAINING].append(share_gaining)
        out[SHARE_LOSING].append(share_losing)
        out[SHARE_NO_CHANGE].append(1.0 - share_gaining - share_losing)
    return {outcome: np.concatenate(chunks, axis=1) for outcome, chunks in out.items()}


def _interval(
    draws: np.ndarray, exact: np.ndarray, alpha: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Percentile bounds and standard error of each area's replicates.

    A skewed set of replicates can leave the estimate outside its percentile
    bounds, so the bounds are widened to include it.
    """
    lower = np.nanpercentile(draws, 100.0 * alpha, axis=1)
    upper = np.nanpercentile(draws, 100.0 * (1.0 - alpha), axis=1)
    return (
        np.fmin(lower, exact),
        np.fmax(upper, exact),
        np.nanstd(draws, axis=1, ddof=1),
    )


def _direction(value: float, lo: float, hi: float) -> str:
    if lo > 0:
        return GAIN
    if hi < 0:
        return LOSS
    if value == 0 and lo == 0 and hi == 0:
        return NO_CHANGE
    return TOO_CLOSE_TO_CALL


def estimate_change(
    *,
    level: str,
    reform: str,
    year: int,
    areas: AreaWeights,
    source_ids: object,
    baseline: object,
    reformed: object,
    settings: Optional[DisclosureSettings] = None,
    noise_key: Optional[Union[str, bytes]] = None,
) -> AreaEstimates:
    """Estimate the change between two runs for every area of one level.

    ``baseline`` and ``reformed`` hold one value per record, for example
    household net income. ``source_ids`` names the survey household each
    record was copied or cloned from.
    """
    settings = (settings or DisclosureSettings()).revalidated()
    # Resolve the key first, so a missing key fails before any computation.
    key = resolve_noise_key(noise_key) if settings.noise else None
    n_records = areas.n_records
    baseline_array = _per_record(baseline, n_records, "baseline")
    reformed_array = _per_record(reformed, n_records, "reformed")
    canonical = canonical_source_ids(source_ids)
    if len(canonical) != n_records:
        raise ValueError("source_ids must have one entry per record.")
    source_index, sources = pd.factorize(canonical)
    n_sources = len(sources)

    change = reformed_array - baseline_array
    change = np.where(np.abs(change) > settings.change_tolerance, change, 0.0)
    # Noise goes on the change only, never on a denominator.
    factor = (
        noise_factors(canonical, key, distance=settings.noise_distance)
        if key is not None
        else np.ones(n_records)
    )
    contributions = {
        FAMILY_CHANGE: factor * change,
        FAMILY_GAINING: factor * (change > 0),
        FAMILY_LOSING: factor * (change < 0),
    }
    no_change = (change == 0).astype(float)

    households = areas.totals(np.ones(n_records))
    income = areas.totals(baseline_array)
    total = areas.totals(contributions[FAMILY_CHANGE])
    with np.errstate(divide="ignore", invalid="ignore"):
        share_gaining = np.clip(
            areas.totals(contributions[FAMILY_GAINING]) / households, 0.0, 1.0
        )
        share_losing = np.clip(
            areas.totals(contributions[FAMILY_LOSING]) / households,
            0.0,
            1.0 - share_gaining,
        )
        exact = {
            AVERAGE_CHANGE: total / households,
            RELATIVE_CHANGE: np.where(income > 0, total / income, np.nan),
            TOTAL_CHANGE: total,
            SHARE_GAINING: share_gaining,
            SHARE_LOSING: share_losing,
            SHARE_NO_CHANGE: 1.0 - share_gaining - share_losing,
        }

    replicates = _replicates(
        areas, contributions, baseline_array, source_index, n_sources, settings
    )
    alpha = (1.0 - settings.interval) / 2.0
    bounds: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        for outcome, draws in replicates.items():
            bounds[outcome] = _interval(draws, exact[outcome], alpha)

    one_area = areas.one_area_per_record
    rules = {"one_area_per_record": one_area, "noise": settings.noise}
    rows: list[dict] = []
    for position, code in enumerate(areas.area_codes):
        records, weights = areas.area_records(code)
        sources_here = source_index[records]
        supports: dict[str, tuple[Support, ...]] = {}
        tiers: dict[str, str] = {}
        reasons: dict[str, Optional[str]] = {}
        for family in FAMILIES:
            supports[family] = family_supports(
                weights, contributions[family][records], sources_here, family
            )
            tiers[family], reasons[family] = cell_tier(
                supports[family], settings, **rules
            )

        # Gaining, losing and no change add to one. Two published shares give
        # the third, so the third cell must also pass.
        unchanged = support(weights, no_change[records], sources_here)
        third_tier, _ = primary_tier(unchanged, settings, **rules)
        both = tiers[FAMILY_GAINING] != WITHHELD and tiers[FAMILY_LOSING] != WITHHELD
        if both and third_tier == WITHHELD:
            weaker = min(
                (FAMILY_LOSING, FAMILY_GAINING),
                key=lambda family: binding_support(supports[family]).n_sources,
            )
            tiers[weaker], reasons[weaker] = WITHHELD, PRIVATE_SHARE_SPLIT
            both = False
        if both:
            third = max(
                (tiers[FAMILY_GAINING], tiers[FAMILY_LOSING], third_tier),
                key=_TIER_ORDER.__getitem__,
            )
            third_reason = None if third == REPORTED else REASON_THIN_SUPPORT
        else:
            third, third_reason = WITHHELD, PRIVATE_SHARE_SPLIT

        rounded: dict[str, tuple[float, float, float, float]] = {}
        for outcome in (*CHANGE_OUTCOMES, SHARE_GAINING, SHARE_LOSING):
            value = float(exact[outcome][position])
            if not math.isfinite(value):
                continue
            lo, hi, error = (float(part[position]) for part in bounds[outcome])
            base = _rounding_base(error, settings.min_rounding_base[outcome])
            rounded[outcome] = (
                _round(value, base),
                _round(lo, base, "down"),
                _round(hi, base, "up"),
                base,
            )
        for outcome in (SHARE_GAINING, SHARE_LOSING):
            value, lo, hi, base = rounded[outcome]
            rounded[outcome] = (value, max(lo, 0.0), min(hi, 1.0), base)
        # No change is the remainder of the two rounded shares, so the three
        # published shares add to one. Its value keeps their finer base: a
        # reader can derive it at that precision anyway. Its interval is
        # rounded on its own standard error.
        base = min(rounded[SHARE_GAINING][3], rounded[SHARE_LOSING][3])
        value = _round(1.0 - rounded[SHARE_GAINING][0] - rounded[SHARE_LOSING][0], base)
        value = min(max(value, 0.0), 1.0)
        lo, hi, error = (float(part[position]) for part in bounds[SHARE_NO_CHANGE])
        own = max(
            _rounding_base(error, settings.min_rounding_base[SHARE_NO_CHANGE]), base
        )
        rounded[SHARE_NO_CHANGE] = (
            value,
            max(min(_round(lo, own, "down"), value), 0.0),
            min(max(_round(hi, own, "up"), value), 1.0),
            base,
        )

        for outcome in (*CHANGE_OUTCOMES, *(SHARE_GAINING, SHARE_LOSING)):
            family = FAMILY_CHANGE if outcome in CHANGE_OUTCOMES else outcome
            rows.append(
                _row(
                    level,
                    code,
                    reform,
                    year,
                    outcome,
                    family,
                    position,
                    exact,
                    bounds,
                    rounded.get(outcome),
                    tiers[family],
                    reasons[family],
                    binding_support(supports[family]),
                    # A cell with no contributor rests on the households that
                    # did not change, as a zero share rests on its other side.
                    binding_support((*supports[family], unchanged)),
                    one_area,
                )
            )
        third_cell = binding_support(
            (*supports[FAMILY_GAINING], *supports[FAMILY_LOSING], unchanged)
        )
        rows.append(
            _row(
                level,
                code,
                reform,
                year,
                SHARE_NO_CHANGE,
                SHARE_NO_CHANGE,
                position,
                exact,
                bounds,
                rounded[SHARE_NO_CHANGE],
                third,
                third_reason,
                third_cell,
                third_cell,
                one_area,
            )
        )

    return AreaEstimates(
        level=level,
        reform=reform,
        year=int(year),
        areas=areas,
        source_index=source_index,
        settings=settings,
        noise=settings.noise,
        contributions=contributions,
        table=pd.DataFrame(rows),
    )


def _row(
    level: str,
    code: str,
    reform: str,
    year: int,
    outcome: str,
    family: str,
    position: int,
    exact: dict[str, np.ndarray],
    bounds: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    rounded: Optional[tuple[float, float, float, float]],
    family_tier: str,
    family_reason: Optional[str],
    cell: Support,
    band_cell: Support,
    one_area_per_record: bool,
) -> dict:
    """One private row: exact and rounded values with the cell's support."""
    tier, reason = family_tier, family_reason
    value = lo = hi = base = None
    direction = None
    if rounded is None:
        # No defined value, for example a relative change on zero income.
        tier, reason = WITHHELD, PRIVATE_UNDEFINED
    else:
        value, lo, hi, base = rounded
        if outcome in CHANGE_OUTCOMES:
            direction = _direction(value, lo, hi)
    exact_lo, exact_hi, error = (float(part[position]) for part in bounds[outcome])
    return {
        "level": level,
        "area_code": code,
        "reform": reform,
        "year": int(year),
        "outcome": outcome,
        "family": family,
        "exact_value": float(exact[outcome][position]),
        "exact_lo": exact_lo,
        "exact_hi": exact_hi,
        "standard_error": error,
        "rounding_base": base,
        "value": value,
        "lo": lo,
        "hi": hi,
        "direction": direction,
        "tier": tier,
        "family_tier": family_tier,
        "private_reason": reason,
        "n_sources": cell.n_sources,
        "n_eff": cell.n_eff,
        "top_share": cell.top_share,
        "rest_share": cell.rest_share,
        "support_band": support_band(
            cell if cell.n_sources else band_cell,
            one_area_per_record=one_area_per_record,
        ),
    }
