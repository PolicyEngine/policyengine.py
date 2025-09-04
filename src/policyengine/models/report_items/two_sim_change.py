from __future__ import annotations

from typing import Any, List

import numpy as np
import pandas as pd
from microdf import MicroDataFrame
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
    variable: str
    group_variable: str
    group_value: int | str
    entity_level: str = "household"
    time_period: int | str | None = None

    total_change: float
    relative_change: float
    average_change_per_entity: float

    @staticmethod
    def build(
        baseline_simulation: "Simulation",
        reform_simulation: "Simulation",
        *,
        variable: str,
        group_variable: str,
        group_value: Any,
        entity_level: str = "household",
    ) -> list["ChangeByBaselineGroup"]:
        base_tbl = _get_table(baseline_simulation, entity_level)
        ref_tbl = _get_table(reform_simulation, entity_level)
        merged = _align_baseline_reform(base_tbl, ref_tbl, entity_level)

        weights_col = (
            "weight_value_base"
            if "weight_value_base" in merged.columns
            else None
        )
        merged["__delta__"] = (
            merged[f"{variable}_ref"] - merged[f"{variable}_base"]
        )
        sub = (
            merged[merged[group_variable] == group_value]
            if group_variable in merged.columns
            else merged
        )
        mdf = (
            MicroDataFrame(sub, weights=weights_col)
            if weights_col
            else MicroDataFrame(sub)
        )
        total_change = float(mdf["__delta__"].sum())
        denom = float(mdf[f"{variable}_base"].sum())
        relative_change = (
            float(total_change / denom) if denom != 0 else float("nan")
        )

        sub = sub.copy()
        sub["__ones__"] = 1.0
        mdf2 = (
            MicroDataFrame(sub, weights=weights_col)
            if weights_col
            else MicroDataFrame(sub)
        )
        weights_sum = float(mdf2["__ones__"].sum())
        avg_change = (
            float(total_change / weights_sum) if weights_sum else float("nan")
        )

        period = getattr(baseline_simulation.dataset.data, "year", None)
        return [
            ChangeByBaselineGroup(
                baseline_simulation=baseline_simulation,
                reform_simulation=reform_simulation,
                variable=variable,
                group_variable=group_variable,
                group_value=group_value,
                entity_level=entity_level,
                time_period=period,
                total_change=total_change,
                relative_change=relative_change,
                average_change_per_entity=avg_change,
            )
        ]


class VariableChangeGroupByQuantileGroup(ReportElementDataItem):
    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    variable: str
    group_variable: str
    quantile_group: int
    quantile_group_count: int = 10
    change_lower_bound: float
    change_upper_bound: float
    change_bound_is_relative: bool = False
    fixed_entity_count_per_quantile_group: str = "household"
    percent_of_group_in_change_group: float
    entities_in_group_in_change_group: float

    @staticmethod
    def build(
        baseline_simulation: "Simulation",
        reform_simulation: "Simulation",
        *,
        variable: str,
        group_variable: str,
        quantile_group_count: int = 10,
        change_lower_bound: float = -np.inf,
        change_upper_bound: float = 0.0,
        change_bound_is_relative: bool = False,
        entity_level: str = "household",
    ) -> list["VariableChangeGroupByQuantileGroup"]:
        base_tbl = _get_table(baseline_simulation, entity_level)
        ref_tbl = _get_table(reform_simulation, entity_level)
        merged = _align_baseline_reform(base_tbl, ref_tbl, entity_level)
        merged["__delta__"] = (
            merged[f"{variable}_ref"] - merged[f"{variable}_base"]
        )
        if change_bound_is_relative:
            base = merged[f"{variable}_base"].replace({0.0: np.nan}).abs()
            merged["__delta__"] = merged["__delta__"] / base

        results: list[VariableChangeGroupByQuantileGroup] = []
        weights_col = (
            "weight_value_base"
            if "weight_value_base" in merged.columns
            else None
        )
        for g, grp in merged.groupby(group_variable):
            grp = grp.copy()
            grp["__in_bucket__"] = (
                (grp["__delta__"] >= change_lower_bound)
                & (grp["__delta__"] < change_upper_bound)
            ).astype(int)
            mdf = (
                MicroDataFrame(grp, weights=weights_col)
                if weights_col
                else MicroDataFrame(grp)
            )
            percent = float(mdf["__in_bucket__"].mean())
            entities = float(mdf["__in_bucket__"].sum())
            results.append(
                VariableChangeGroupByQuantileGroup(
                    baseline_simulation=baseline_simulation,
                    reform_simulation=reform_simulation,
                    variable=variable,
                    group_variable=group_variable,
                    quantile_group=int(g)
                    if isinstance(g, (int, np.integer))
                    else g,
                    quantile_group_count=quantile_group_count,
                    change_lower_bound=float(change_lower_bound),
                    change_upper_bound=float(change_upper_bound),
                    change_bound_is_relative=change_bound_is_relative,
                    fixed_entity_count_per_quantile_group=entity_level,
                    percent_of_group_in_change_group=percent,
                    entities_in_group_in_change_group=entities,
                )
            )
        return results


class VariableChangeGroupByVariableValue(ReportElementDataItem):
    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    variable: str
    group_variable: str
    group_variable_value: Any
    fixed_entity_count_per_quantile_group: str = "household"
    percent_of_group_in_change_group: float
    entities_in_group_in_change_group: float

    @staticmethod
    def build(
        baseline_simulation: "Simulation",
        reform_simulation: "Simulation",
        *,
        variable: str,
        group_variable: str,
        change_lower_bound: float = -np.inf,
        change_upper_bound: float = 0.0,
        change_bound_is_relative: bool = False,
        entity_level: str = "household",
    ) -> list["VariableChangeGroupByVariableValue"]:
        base_tbl = _get_table(baseline_simulation, entity_level)
        ref_tbl = _get_table(reform_simulation, entity_level)
        merged = _align_baseline_reform(base_tbl, ref_tbl, entity_level)
        merged["__delta__"] = (
            merged[f"{variable}_ref"] - merged[f"{variable}_base"]
        )
        if change_bound_is_relative:
            base = merged[f"{variable}_base"].replace({0.0: np.nan}).abs()
            merged["__delta__"] = merged["__delta__"] / base

        results: list[VariableChangeGroupByVariableValue] = []
        weights_col = (
            "weight_value_base"
            if "weight_value_base" in merged.columns
            else None
        )
        for val, grp in merged.groupby(group_variable):
            grp = grp.copy()
            grp["__in_bucket__"] = (
                (grp["__delta__"] >= change_lower_bound)
                & (grp["__delta__"] < change_upper_bound)
            ).astype(int)
            mdf = (
                MicroDataFrame(grp, weights=weights_col)
                if weights_col
                else MicroDataFrame(grp)
            )
            percent = float(mdf["__in_bucket__"].mean())
            entities = float(mdf["__in_bucket__"].sum())
            results.append(
                VariableChangeGroupByVariableValue(
                    baseline_simulation=baseline_simulation,
                    reform_simulation=reform_simulation,
                    variable=variable,
                    group_variable=group_variable,
                    group_variable_value=val,
                    fixed_entity_count_per_quantile_group=entity_level,
                    percent_of_group_in_change_group=percent,
                    entities_in_group_in_change_group=entities,
                )
            )
        return results
