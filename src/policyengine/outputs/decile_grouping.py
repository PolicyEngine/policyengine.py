"""Shared weighted grouping for decile-based outputs."""

from typing import Any, Optional

import numpy as np
import pandas as pd
from microdf import MicroSeries


def calculate_decile_groups(
    baseline_data: Any,
    ranking_values: Any,
    *,
    decile_variable: Optional[str],
    entity: str,
    quantiles: int,
) -> Any:
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

    if decile_variable:
        return baseline_data[decile_variable]
    if quantiles < 1:
        raise ValueError("quantiles must be at least 1")

    weight_variable = f"{entity}_weight"
    if weight_variable not in baseline_data.columns:
        raise ValueError(
            f"Weighted quantile grouping requires '{weight_variable}' in "
            f"baseline output data for entity '{entity}'."
        )
    weights = np.asarray(baseline_data[weight_variable], dtype=float)

    if entity == "household":
        multiplier_variable = "household_count_people"
        if multiplier_variable not in baseline_data.columns:
            raise ValueError(
                "Person-weighted household quantile grouping requires "
                "'household_count_people' in baseline output data."
            )
        weights = weights * np.asarray(
            baseline_data[multiplier_variable],
            dtype=float,
        )

    ranking_array = np.asarray(ranking_values)
    weighted_values = MicroSeries(
        ranking_array,
        index=baseline_data.index,
        weights=weights,
    )
    percentile_ranks = np.asarray(weighted_values.rank(pct=True))
    groups = np.clip(
        np.ceil(percentile_ranks * quantiles),
        1,
        quantiles,
    ).astype(int)
    groups[ranking_array < 0] = -1
    return pd.Series(groups, index=baseline_data.index)
