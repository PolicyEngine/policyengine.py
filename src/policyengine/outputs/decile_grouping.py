"""Shared weighted grouping for decile-based outputs."""

from typing import Any, Optional

import numpy as np
import pandas as pd
from microdf import MicroSeries


def _validate_nonnegative_finite(values: np.ndarray, *, name: str) -> None:
    """Require finite, non-negative values used as survey weights."""
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must contain only finite values")
    if np.any(values < 0):
        raise ValueError(f"{name} must not contain negative values")


def _get_analysis_weight(
    baseline_data: Any,
    *,
    entity: str,
) -> np.ndarray:
    """Return validated entity survey weights."""
    weight_variable = f"{entity}_weight"
    if weight_variable not in baseline_data.columns:
        raise ValueError(
            f"Weighted quantile grouping requires '{weight_variable}' in "
            f"baseline output data for entity '{entity}'."
        )

    analysis_weight = np.asarray(
        baseline_data[weight_variable],
        dtype=float,
    )
    _validate_nonnegative_finite(
        analysis_weight,
        name=weight_variable,
    )
    return analysis_weight


def _get_decile_weights(
    baseline_data: Any,
    *,
    entity: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Return entity survey weights and effective population weights."""
    analysis_weight = _get_analysis_weight(
        baseline_data,
        entity=entity,
    )
    if entity != "household":
        return analysis_weight, analysis_weight.copy()

    multiplier_variable = "household_count_people"
    if multiplier_variable not in baseline_data.columns:
        raise ValueError(
            "Person-weighted household quantile grouping requires "
            "'household_count_people' in baseline output data."
        )

    people_count = np.asarray(
        baseline_data[multiplier_variable],
        dtype=float,
    )
    _validate_nonnegative_finite(
        people_count,
        name=multiplier_variable,
    )
    return analysis_weight, analysis_weight * people_count


def calculate_decile_groups(
    baseline_data: Any,
    ranking_values: Any,
    *,
    decile_variable: Optional[str],
    entity: str,
    quantiles: int,
) -> pd.Series:
    """Return precomputed groups or weighted ranks of ``ranking_values``.

    Household income groups follow the convention used by both country
    packages: survey weights are multiplied by household size so that each
    decile represents an approximately equal number of people. Other entities
    use their entity survey weights without an additional multiplier. Negative
    ranking values are assigned ``-1`` and therefore excluded from reported
    groups, matching the country-package income-decile convention.

    Precomputed groups are returned unchanged. Callers that use values outside
    ``1..quantiles`` (including the conventional ``-1`` sentinel) can therefore
    intentionally exclude rows from reported groups.
    """

    if quantiles < 1:
        raise ValueError("quantiles must be at least 1")
    if decile_variable:
        return pd.Series(
            np.asarray(baseline_data[decile_variable]),
            index=baseline_data.index,
        )

    _, effective_weight = _get_decile_weights(
        baseline_data,
        entity=entity,
    )
    if np.sum(effective_weight) == 0:
        raise ValueError("Effective grouping weights must have a positive total")

    ranking_array = np.asarray(ranking_values, dtype=float)
    if len(ranking_array) != len(baseline_data):
        raise ValueError("Ranking values must align with baseline output data")

    finite = np.isfinite(ranking_array)
    groups = pd.Series(
        pd.array([pd.NA] * len(ranking_array), dtype="Int64"),
        index=baseline_data.index,
    )
    if not np.any(finite):
        return groups

    finite_weights = effective_weight[finite]
    if np.sum(finite_weights) == 0:
        raise ValueError(
            "Finite ranking values must have a positive effective weight total"
        )
    weighted_values = MicroSeries(
        ranking_array[finite],
        index=baseline_data.index[finite],
        weights=finite_weights,
    )
    percentile_ranks = np.asarray(weighted_values.rank(pct=True))
    finite_groups = np.clip(
        np.ceil(percentile_ranks * quantiles),
        1,
        quantiles,
    ).astype(int)
    finite_groups[ranking_array[finite] < 0] = -1
    groups.loc[finite] = finite_groups
    return groups
