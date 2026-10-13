"""Settings, public models and constants of the disclosure layer."""

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

REPORTED = "reported"
APPROXIMATE = "approximate"
WITHHELD = "withheld"
TIERS = (REPORTED, APPROXIMATE, WITHHELD)

# The middle band uses an en dash, as the published tables do.
BAND_UNDER_10 = "<10"
BAND_10_TO_29 = "10–29"
BAND_30_PLUS = "30+"
SUPPORT_BANDS = (BAND_UNDER_10, BAND_10_TO_29, BAND_30_PLUS)

# Reasons a published table may show. A withheld row always shows the same
# reason: a finer one would tell a reader which rows are secondary.
REASON_THIN_SUPPORT = "thin_support"
REASON_DISCLOSURE_CONTROL = "disclosure_control"
PUBLIC_REASONS = (REASON_THIN_SUPPORT, REASON_DISCLOSURE_CONTROL)

# Reasons kept in the private audit only.
PRIVATE_BELOW_FLOOR = "below_floor"
PRIVATE_LOW_N_EFF = "low_effective_sample"
PRIVATE_DOMINANT = "dominant_household"
PRIVATE_SHARE_SPLIT = "share_split"
PRIVATE_SECONDARY = "secondary"
PRIVATE_UNDEFINED = "undefined_denominator"

GAIN = "gain"
LOSS = "loss"
TOO_CLOSE_TO_CALL = "too_close_to_call"
NO_CHANGE = "no_change"
DIRECTIONS = (GAIN, LOSS, TOO_CLOSE_TO_CALL, NO_CHANGE)

AVERAGE_CHANGE = "average_change"
RELATIVE_CHANGE = "relative_change"
TOTAL_CHANGE = "total_change"
SHARE_GAINING = "share_gaining"
SHARE_LOSING = "share_losing"
SHARE_NO_CHANGE = "share_no_change"
CHANGE_OUTCOMES = (AVERAGE_CHANGE, RELATIVE_CHANGE, TOTAL_CHANGE)
SHARE_OUTCOMES = (SHARE_GAINING, SHARE_LOSING, SHARE_NO_CHANGE)
OUTCOMES = CHANGE_OUTCOMES + SHARE_OUTCOMES

# Outcomes that share a numerator share a tier. A reader can turn one into the
# other with public denominators, so they are published or withheld together.
FAMILY_CHANGE = "change"
FAMILY_GAINING = SHARE_GAINING
FAMILY_LOSING = SHARE_LOSING
FAMILIES = (FAMILY_CHANGE, FAMILY_GAINING, FAMILY_LOSING)
OUTCOME_FAMILY = {
    AVERAGE_CHANGE: FAMILY_CHANGE,
    RELATIVE_CHANGE: FAMILY_CHANGE,
    TOTAL_CHANGE: FAMILY_CHANGE,
    SHARE_GAINING: FAMILY_GAINING,
    SHARE_LOSING: FAMILY_LOSING,
}

ESTIMATOR_DIRECT = "direct"

PUBLIC_COLUMNS = (
    "level",
    "area_code",
    "reform",
    "year",
    "outcome",
    "value",
    "lo",
    "hi",
    "direction",
    "tier",
    "reason",
    "support_band",
    "noise",
    "estimator",
)
# Label columns a publisher may add beside the public columns.
OPTIONAL_LABEL_COLUMNS = ("area_name",)
# Columns of the private audit. None may appear in a published file.
AUDIT_COLUMNS = (
    "family",
    "exact_value",
    "exact_lo",
    "exact_hi",
    "standard_error",
    "rounding_base",
    "n_sources",
    "n_eff",
    "top_share",
    "rest_share",
    "private_reason",
)

DEFAULT_MIN_ROUNDING_BASE = {
    AVERAGE_CHANGE: 1.0,
    RELATIVE_CHANGE: 0.0001,
    TOTAL_CHANGE: 1000.0,
    SHARE_GAINING: 0.001,
    SHARE_LOSING: 0.001,
    SHARE_NO_CHANGE: 0.001,
}

RECOVERABLE_REMAINDER = "recoverable_remainder"
RECOVERABLE_PARENT = "recoverable_parent"
UNCHECKED_OVERLAP = "unchecked_overlap"
NOISE_REFERENCE_PUBLIC = "noise_reference_public"
ALREADY_PUBLIC = "already_public"
# Findings a caller may accept after review. The others always block.
ACKNOWLEDGEABLE_FINDINGS = (UNCHECKED_OVERLAP, NOISE_REFERENCE_PUBLIC)


def is_power_of_ten(value: float) -> bool:
    if not math.isfinite(value) or value <= 0:
        return False
    exponent = math.log10(value)
    return abs(exponent - round(exponent)) < 1e-9


class DisclosureSettings(BaseModel):
    """Publication rules. The floors can be raised, never lowered."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_sources: int = Field(default=10, ge=10)
    max_top_share: float = Field(default=0.5, gt=0.0, le=0.5)
    # The p% rule: what is left of a number without its largest household, or
    # its two largest, must be at least this share of the largest one's part.
    min_rest_share: float = Field(default=0.1, ge=0.1, le=1.0)
    min_n_eff: float = Field(default=10.0, ge=10.0)
    approximate_below_n_eff: float = Field(default=30.0, ge=0.0)
    # A household contributes, gains or loses when its change is larger than
    # this, in the outcome's unit (pounds a year). Smaller changes count as no
    # change and are left out of every sum. The bound keeps floating-point
    # residue from counting as a contributor.
    change_tolerance: float = Field(default=1.0, ge=1.0)
    noise: bool = False
    # Distance of a noise factor from 1: uniform on this range, either side.
    noise_distance: tuple[float, float] = (0.08, 0.12)
    n_replicates: int = Field(default=1000, ge=200)
    interval: float = Field(default=0.90, gt=0.5, lt=1.0)
    bootstrap_seed: int = 0
    min_rounding_base: dict[str, float] = Field(
        default_factory=lambda: dict(DEFAULT_MIN_ROUNDING_BASE)
    )

    def revalidated(self) -> "DisclosureSettings":
        """These settings, validated again.

        ``model_copy(update=...)`` and ``model_construct`` skip validation, so
        the layer validates the settings it is given before it uses them.
        """
        return type(self).model_validate(self.model_dump())

    @field_validator("noise_distance")
    @classmethod
    def _noise_distance_keeps_clear_of_one(
        cls, value: tuple[float, float]
    ) -> tuple[float, float]:
        low, high = value
        if not 0.0 < low < high < 1.0:
            raise ValueError("noise_distance must satisfy 0 < low < high < 1")
        return value

    @field_validator("min_rounding_base")
    @classmethod
    def _rounding_bases_are_complete_powers_of_ten(
        cls, value: dict[str, float]
    ) -> dict[str, float]:
        unknown = sorted(set(value) - set(OUTCOMES))
        if unknown:
            raise ValueError(f"unknown outcomes in min_rounding_base: {unknown}")
        merged = {**DEFAULT_MIN_ROUNDING_BASE, **value}
        for outcome, base in merged.items():
            if not is_power_of_ten(base):
                raise ValueError(
                    f"min_rounding_base[{outcome!r}] must be a power of ten"
                )
        return merged


class PublicRow(BaseModel):
    """One published row: an outcome for an area, a reform and a year."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: str
    area_code: str
    reform: str
    year: int
    outcome: str
    value: Optional[float] = None
    lo: Optional[float] = None
    hi: Optional[float] = None
    direction: Optional[str] = None
    tier: str
    reason: Optional[str] = None
    support_band: Optional[str] = None
    noise: bool = False
    estimator: str = ESTIMATOR_DIRECT


class PublicTable(BaseModel):
    """The rows a release may publish."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rows: list[PublicRow]

    def to_frame(self) -> pd.DataFrame:
        records = [row.model_dump() for row in self.rows]
        return pd.DataFrame(records, columns=list(PUBLIC_COLUMNS))

    def to_csv(self, path: Union[str, Path]) -> Path:
        path = Path(path)
        self.to_frame().to_csv(path, index=False)
        return path


class Finding(BaseModel):
    """A result of the release check. It carries labels, never values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    blocking: bool
    relation: str
    message: str
    level: Optional[str] = None
    reform: Optional[str] = None
    year: Optional[int] = None
    family: Optional[str] = None
    group: Optional[str] = None
    group_level: Optional[str] = None
    members: list[str] = Field(default_factory=list)
    suggested: Optional[str] = None


class PriorPublic(BaseModel):
    """Cells an earlier publication already made public."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    noise: bool = False
    cells: list[tuple[str, str, str, int, str]]

    @classmethod
    def from_frame(
        cls, name: str, frame: pd.DataFrame, *, noise: bool = False
    ) -> "PriorPublic":
        """Read cells from columns level, area_code, reform, year, outcome."""
        columns: Sequence[str] = ("level", "area_code", "reform", "year", "outcome")
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ValueError(f"prior publication {name!r} lacks columns {missing}")
        cells = [
            (str(level), str(area), str(reform), int(year), str(outcome))
            for level, area, reform, year, outcome in frame[list(columns)].itertuples(
                index=False, name=None
            )
        ]
        return cls(name=name, noise=noise, cells=cells)
