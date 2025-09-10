from __future__ import annotations

from typing import Any, List

import numpy as np
import pandas as pd

try:
    from microdf import MicroDataFrame

    MICRODF_AVAILABLE = True
except ImportError:
    MICRODF_AVAILABLE = False
    MicroDataFrame = None
from policyengine.models.simulation import (
    Simulation,
)  # ensure forward ref resolution

from .base import ReportElementDataItem


def _get_table(sim: "Simulation", entity_level: str) -> pd.DataFrame:
    # Assume well-formed result
    return sim.result.data.tables[entity_level]  # type: ignore[attr-defined]


def _align_baseline_reform(
    baseline: pd.DataFrame,
    reform: pd.DataFrame,
    entity_level: str,
) -> pd.DataFrame:
    key = f"{entity_level}_id"
    if key not in baseline.columns or key not in reform.columns:
        baseline = baseline.copy()
        reform = reform.copy()
        baseline["__idx"] = range(len(baseline))
        reform["__idx"] = range(len(reform))
        key = "__idx"
    merged = baseline.merge(
        reform,
        on=key,
        how="inner",
        suffixes=("_base", "_ref"),
        copy=False,
    )
    return merged


class ChangeByBaselineGroup(ReportElementDataItem):
    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    country: str
    variable: str
    group_variable: str
    group_value: int | str
    entity_level: str = "household"
    time_period: int | str | None = None

    total_change: float | None = None
    relative_change: float | None = None
    average_change_per_entity: float | None = None

    @staticmethod
    def run(
        items: list["ChangeByBaselineGroup"],
    ) -> list["ChangeByBaselineGroup"]:
        """Batch-compute change metrics for provided items.

        Assumes items share the same baseline/reform simulations for efficiency.
        """
        if not items:
            return []

        # Group by (entity_level) to reuse aligned tables
        grouped: dict[str, list[ChangeByBaselineGroup]] = {}
        for it in items:
            grouped.setdefault(it.entity_level, []).append(it)

        out: list[ChangeByBaselineGroup] = []
        for entity_level, bucket in grouped.items():
            base_sim = bucket[0].baseline_simulation
            ref_sim = bucket[0].reform_simulation
            base_tbl = _get_table(base_sim, entity_level)
            ref_tbl = _get_table(ref_sim, entity_level)
            merged = _align_baseline_reform(base_tbl, ref_tbl, entity_level)

            weights_col = (
                "weight_value_base"
                if "weight_value_base" in merged.columns
                else None
            )

            # Precompute ones for weighted counts
            merged = merged.copy()
            merged["__ones__"] = 1.0

            for it in bucket:
                var = it.variable
                grp_var = it.group_variable
                merged["__delta__"] = (
                    merged[f"{var}_ref"] - merged[f"{var}_base"]
                )
                # Resolve group column name (merge may suffix)
                if grp_var in merged.columns:
                    grp_col = grp_var
                elif f"{grp_var}_base" in merged.columns:
                    grp_col = f"{grp_var}_base"
                elif f"{grp_var}_ref" in merged.columns:
                    grp_col = f"{grp_var}_ref"
                else:
                    grp_col = None
                sub = (
                    merged[merged[grp_col] == it.group_value]  # type: ignore[index]
                    if grp_col is not None
                    else merged
                )
                if not MICRODF_AVAILABLE:
                    raise ImportError(
                        "microdf is not installed. "
                        "Install it with: pip install 'policyengine[core]'"
                    )
                mdf = (
                    MicroDataFrame(sub, weights=weights_col)
                    if weights_col
                    else MicroDataFrame(sub)
                )
                total_change = float(mdf["__delta__"].sum())
                denom = float(mdf[f"{var}_base"].sum())
                relative_change = (
                    float(total_change / denom) if denom != 0 else float("nan")
                )

                mdf2 = (
                    MicroDataFrame(sub, weights=weights_col)
                    if weights_col
                    else MicroDataFrame(sub)
                )
                weights_sum = float(mdf2["__ones__"].sum())
                avg_change = (
                    float(total_change / weights_sum)
                    if weights_sum
                    else float("nan")
                )

                period = getattr(base_sim.dataset.data, "year", None)
                payload = it.model_dump()
                payload.update(
                    {
                        "time_period": period,
                        "total_change": total_change,
                        "relative_change": relative_change,
                        "average_change_per_entity": avg_change,
                    }
                )
                out.append(ChangeByBaselineGroup(**payload))

        return out


class VariableChangeGroupByQuantileGroup(ReportElementDataItem):
    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    country: str
    variable: str
    group_variable: str
    quantile_group: int
    quantile_group_count: int = 10
    change_lower_bound: float
    change_upper_bound: float
    change_bound_is_relative: bool = False
    fixed_entity_count_per_quantile_group: str = "household"
    percent_of_group_in_change_group: float | None = None
    entities_in_group_in_change_group: float | None = None

    @staticmethod
    def run(
        items: list["VariableChangeGroupByQuantileGroup"],
    ) -> list["VariableChangeGroupByQuantileGroup"]:
        """Batch-compute change-bucket shares by group.

        Items should reference the same baseline/reform simulations for best performance.
        """
        if not items:
            return []

        # Group by entity_level
        grouped: dict[str, list[VariableChangeGroupByQuantileGroup]] = {}
        for it in items:
            grouped.setdefault(
                it.fixed_entity_count_per_quantile_group, []
            ).append(it)

        out: list[VariableChangeGroupByQuantileGroup] = []
        for entity_level, bucket in grouped.items():
            base_sim = bucket[0].baseline_simulation
            ref_sim = bucket[0].reform_simulation
            base_tbl = _get_table(base_sim, entity_level)
            ref_tbl = _get_table(ref_sim, entity_level)
            merged = _align_baseline_reform(base_tbl, ref_tbl, entity_level)

            weights_col = (
                "weight_value_base"
                if "weight_value_base" in merged.columns
                else None
            )
            merged = merged.copy()

            for it in bucket:
                var = it.variable
                grp_var = it.group_variable
                merged["__delta__"] = (
                    merged[f"{var}_ref"] - merged[f"{var}_base"]
                )
                if it.change_bound_is_relative:
                    base = merged[f"{var}_base"].replace({0.0: np.nan}).abs()
                    merged["__delta__"] = merged["__delta__"] / base

                # Resolve group column name and subset to selected group
                if grp_var in merged.columns:
                    grp_col = grp_var
                elif f"{grp_var}_base" in merged.columns:
                    grp_col = f"{grp_var}_base"
                elif f"{grp_var}_ref" in merged.columns:
                    grp_col = f"{grp_var}_ref"
                else:
                    grp_col = None
                target = it.quantile_group
                grp = (
                    merged[merged[grp_col] == target].copy()  # type: ignore[index]
                    if grp_col is not None
                    else merged.copy()
                )
                grp["__in_bucket__"] = (
                    (grp["__delta__"] >= it.change_lower_bound)
                    & (grp["__delta__"] < it.change_upper_bound)
                ).astype(int)
                if not MICRODF_AVAILABLE:
                    raise ImportError(
                        "microdf is not installed. "
                        "Install it with: pip install 'policyengine[core]'"
                    )
                mdf = (
                    MicroDataFrame(grp, weights=weights_col)
                    if weights_col
                    else MicroDataFrame(grp)
                )
                percent = float(mdf["__in_bucket__"].mean())
                entities = float(mdf["__in_bucket__"].sum())
                payload = it.model_dump()
                payload.update(
                    {
                        "percent_of_group_in_change_group": percent,
                        "entities_in_group_in_change_group": entities,
                    }
                )
                out.append(VariableChangeGroupByQuantileGroup(**payload))

        return out


class VariableChangeGroupByVariableValue(ReportElementDataItem):
    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    country: str
    variable: str
    group_variable: str
    group_variable_value: Any
    change_lower_bound: float
    change_upper_bound: float
    change_bound_is_relative: bool = False
    fixed_entity_count_per_quantile_group: str = "household"
    percent_of_group_in_change_group: float | None = None
    entities_in_group_in_change_group: float | None = None

    @staticmethod
    def run(
        items: list["VariableChangeGroupByVariableValue"],
    ) -> list["VariableChangeGroupByVariableValue"]:
        """Batch-compute change-bucket shares by variable values.

        Assumes shared baseline/reform simulations for best performance.
        """
        if not items:
            return []

        # Group by entity_level
        grouped: dict[str, list[VariableChangeGroupByVariableValue]] = {}
        for it in items:
            grouped.setdefault(
                it.fixed_entity_count_per_quantile_group, []
            ).append(it)

        out: list[VariableChangeGroupByVariableValue] = []
        for entity_level, bucket in grouped.items():
            base_sim = bucket[0].baseline_simulation
            ref_sim = bucket[0].reform_simulation
            base_tbl = _get_table(base_sim, entity_level)
            ref_tbl = _get_table(ref_sim, entity_level)
            merged = _align_baseline_reform(base_tbl, ref_tbl, entity_level)
            weights_col = (
                "weight_value_base"
                if "weight_value_base" in merged.columns
                else None
            )
            merged = merged.copy()

            for it in bucket:
                var = it.variable
                grp_var = it.group_variable
                merged["__delta__"] = (
                    merged[f"{var}_ref"] - merged[f"{var}_base"]
                )
                if it.change_bound_is_relative:
                    base = merged[f"{var}_base"].replace({0.0: np.nan}).abs()
                    merged["__delta__"] = merged["__delta__"] / base

                # Resolve group column name and subset
                if grp_var in merged.columns:
                    grp_col = grp_var
                elif f"{grp_var}_base" in merged.columns:
                    grp_col = f"{grp_var}_base"
                elif f"{grp_var}_ref" in merged.columns:
                    grp_col = f"{grp_var}_ref"
                else:
                    grp_col = None

                grp = (
                    merged[merged[grp_col] == it.group_variable_value].copy()  # type: ignore[index]
                    if grp_col is not None
                    else merged.copy()
                )
                grp["__in_bucket__"] = (
                    (grp["__delta__"] >= it.change_lower_bound)
                    & (grp["__delta__"] < it.change_upper_bound)
                ).astype(int)
                if not MICRODF_AVAILABLE:
                    raise ImportError(
                        "microdf is not installed. "
                        "Install it with: pip install 'policyengine[core]'"
                    )
                mdf = (
                    MicroDataFrame(grp, weights=weights_col)
                    if weights_col
                    else MicroDataFrame(grp)
                )
                percent = float(mdf["__in_bucket__"].mean())
                entities = float(mdf["__in_bucket__"].sum())
                payload = it.model_dump()
                payload.update(
                    {
                        "percent_of_group_in_change_group": percent,
                        "entities_in_group_in_change_group": entities,
                    }
                )
                out.append(VariableChangeGroupByVariableValue(**payload))

        return out
