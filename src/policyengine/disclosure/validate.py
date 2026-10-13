"""Format checks on a published table.

``validate_public`` needs no key and no microdata, so it can run on every
pull request. It checks necessary conditions only: the shape of the file, not
the support behind it. It cannot tell whether a number rested on enough
households. Only the release that made the file can.
"""

import math
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from .schema import (
    APPROXIMATE,
    AUDIT_COLUMNS,
    BAND_UNDER_10,
    CHANGE_OUTCOMES,
    DEFAULT_MIN_ROUNDING_BASE,
    DIRECTIONS,
    ESTIMATOR_DIRECT,
    OPTIONAL_LABEL_COLUMNS,
    OUTCOMES,
    PUBLIC_COLUMNS,
    REASON_DISCLOSURE_CONTROL,
    REASON_THIN_SUPPORT,
    SHARE_GAINING,
    SHARE_LOSING,
    SHARE_NO_CHANGE,
    SHARE_OUTCOMES,
    SUPPORT_BANDS,
    TIERS,
    WITHHELD,
    PublicTable,
)

_KEY = ["level", "area_code", "reform", "year", "outcome"]
_VALUES = ["value", "lo", "hi"]
# An interval this many rounding steps wide means the row was not rounded.
_MAX_INTERVAL_STEPS = 100.0


def _shared_base(numbers: Iterable[float]) -> Optional[float]:
    """The largest power of ten that divides every number, if any."""
    values = [number for number in numbers if number != 0]
    if not values:
        return None
    for exponent in range(15, -13, -1):
        base = 10.0**exponent
        steps = [v / base for v in values]
        # A base larger than a number does not divide it.
        if all(round(s) != 0 and abs(s - round(s)) < 1e-6 for s in steps):
            return base
    return 0.0


def _check_frame(
    frame: pd.DataFrame, minimum_base: Mapping[str, float], label: str
) -> list[str]:
    problems: list[str] = []
    columns = set(frame.columns)
    leaked = sorted(columns & set(AUDIT_COLUMNS))
    if leaked:
        problems.append(f"{label}: private audit columns present: {leaked}")
    missing = [column for column in PUBLIC_COLUMNS if column not in columns]
    if missing:
        problems.append(f"{label}: missing columns: {missing}")
    extra = sorted(columns - set(PUBLIC_COLUMNS) - set(OPTIONAL_LABEL_COLUMNS))
    if extra:
        problems.append(f"{label}: columns that are not allowed: {extra}")
    if missing:
        return problems

    if frame.duplicated(subset=_KEY).any():
        problems.append(f"{label}: duplicate rows for one area, reform and outcome")

    shares: dict[tuple, dict[str, float]] = {}
    for number, row in enumerate(frame.to_dict("records"), start=2):
        where = f"{label}: row {number}"
        tier, outcome = row["tier"], row["outcome"]
        if tier not in TIERS:
            problems.append(f"{where}: unknown tier")
            continue
        if outcome not in OUTCOMES:
            problems.append(f"{where}: unknown outcome")
            continue
        if row["noise"] not in ("True", "False"):
            problems.append(f"{where}: noise must be True or False")
        if row["estimator"] != ESTIMATOR_DIRECT:
            problems.append(f"{where}: unknown estimator")
        if not row["year"].lstrip("-").isdigit():
            problems.append(f"{where}: year is not a whole number")

        if tier == WITHHELD:
            filled = [c for c in (*_VALUES, "direction", "support_band") if row[c]]
            if filled:
                problems.append(f"{where}: a withheld row has entries in {filled}")
            if row["reason"] != REASON_DISCLOSURE_CONTROL:
                problems.append(f"{where}: a withheld row has the wrong reason")
            continue

        expected = REASON_THIN_SUPPORT if tier == APPROXIMATE else ""
        if row["reason"] != expected:
            problems.append(f"{where}: the reason does not match the tier")
        if row["support_band"] not in SUPPORT_BANDS:
            problems.append(f"{where}: unknown support band")
        direction = row["direction"]
        if outcome in CHANGE_OUTCOMES and direction not in DIRECTIONS:
            problems.append(f"{where}: unknown direction")
        if outcome in SHARE_OUTCOMES and direction:
            problems.append(f"{where}: a share has no direction")
        try:
            value, lo, hi = (float(row[column]) for column in _VALUES)
        except ValueError:
            problems.append(f"{where}: value, lo and hi must be numbers")
            continue
        if not all(math.isfinite(number) for number in (value, lo, hi)):
            problems.append(f"{where}: value, lo and hi must be finite")
            continue
        if not lo <= value <= hi:
            problems.append(f"{where}: the value is outside its interval")
        if row["support_band"] == BAND_UNDER_10 and value != 0:
            problems.append(f"{where}: a non-zero value has a support band under 10")
        if outcome in SHARE_OUTCOMES:
            if lo < 0 or hi > 1:
                problems.append(f"{where}: a share is outside 0 to 1")
            key = tuple(row[column] for column in _KEY[:-1])
            shares.setdefault(key, {})[outcome] = value

        base = _shared_base((value, lo, hi))
        if base is not None:
            if base < minimum_base[outcome] * (1 - 1e-9):
                problems.append(f"{where}: finer than the minimum rounding")
            elif outcome != SHARE_NO_CHANGE and hi - lo > _MAX_INTERVAL_STEPS * base:
                # No change is derived from the two rounded shares, so its
                # value can be finer than its own interval.
                problems.append(f"{where}: not rounded to its interval")

    for key, parts in shares.items():
        if len(parts) == 3:
            total = parts[SHARE_GAINING] + parts[SHARE_LOSING] + parts[SHARE_NO_CHANGE]
            if abs(total - 1.0) > 1e-9:
                problems.append(f"{label}: the shares of {key} do not add to one")
        elif SHARE_NO_CHANGE in parts:
            problems.append(f"{label}: {key} shows no change without both shares")
    return problems


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def validate_public(
    table: Union[str, Path, pd.DataFrame, PublicTable],
    *,
    reviewed: Iterable[str] = (),
    min_rounding_base: Optional[Mapping[str, float]] = None,
) -> list[str]:
    """Return the problems found in a published table, file or directory.

    An empty list means the format checks pass. In a directory every file must
    be a table from this package, or be named in ``reviewed`` after a person
    checked it.
    """
    minimum_base = {**DEFAULT_MIN_ROUNDING_BASE, **(min_rounding_base or {})}
    if isinstance(table, PublicTable):
        table = table.to_frame()
    if isinstance(table, pd.DataFrame):
        frame = table.astype(object).where(table.notna(), "").astype(str)
        return _check_frame(frame, minimum_base, "table")

    path = Path(table)
    if not path.exists():
        return [f"{path}: no such file or directory"]
    if path.is_file():
        return _check_frame(_read(path), minimum_base, path.name)

    allowed = set(reviewed)
    problems: list[str] = []
    for entry in sorted(path.rglob("*")):
        if entry.is_dir():
            continue
        name = entry.relative_to(path).as_posix()
        if name in allowed or entry.name in allowed:
            continue
        if entry.suffix.lower() != ".csv":
            problems.append(f"{name}: not a disclosure table and not reviewed")
            continue
        frame = _read(entry)
        if not set(PUBLIC_COLUMNS) <= set(frame.columns):
            problems.append(f"{name}: not a disclosure table and not reviewed")
            continue
        problems.extend(_check_frame(frame, minimum_base, name))
    return problems
