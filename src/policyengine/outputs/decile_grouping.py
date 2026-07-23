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
    use their entity survey weights without an additional multiplier.
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

    weighted_values = MicroSeries(
        np.asarray(ranking_values),
        index=baseline_data.index,
        weights=weights,
    )
    percentile_ranks = np.asarray(weighted_values.rank(pct=True))
    groups = np.minimum(
        np.ceil(percentile_ranks * quantiles),
        quantiles,
    ).astype(int)
    return pd.Series(groups, index=baseline_data.index)
