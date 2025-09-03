from __future__ import annotations

from typing import Any, List

import numpy as np
import pandas as pd
from microdf import MicroDataFrame

from policyengine.models.reports import (
    ChangeByBaselineGroup,
    VariableChangeGroupByQuantileGroup,
    VariableChangeGroupByVariableValue,
    ReportElement,
)
from policyengine.models.simulation import Simulation
from policyengine.models.single_year_dataset import SingleYearDataset


def _get_table(sim: Simulation, entity_level: str) -> pd.DataFrame | None:
    try:
        data = sim.result.data  # type: ignore[attr-defined]
    except Exception:
        return None
    if not isinstance(data, SingleYearDataset):
        return None
    return data.tables.get(entity_level)


def _align_baseline_reform(
    baseline: pd.DataFrame,
    reform: pd.DataFrame,
    entity_level: str,
) -> pd.DataFrame:
    key = f"{entity_level}_id"
    if key not in baseline.columns or key not in reform.columns:
        # Fall back to index alignment if no ID column exists
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


class ChangeByBaselineGroupReportElement(ReportElement):
    """Compute change in a variable within a group defined on baseline results."""

    baseline: Simulation
    reform: Simulation
    variable: str
    group_variable: str
    group_value: Any
    entity_level: str = "household"

    def run(self) -> list[ChangeByBaselineGroup]:
        base_tbl = _get_table(self.baseline, self.entity_level)
        ref_tbl = _get_table(self.reform, self.entity_level)
        if base_tbl is None or ref_tbl is None:
            return []
        if (
            self.variable not in base_tbl.columns
            or self.variable not in ref_tbl.columns
            or self.group_variable not in base_tbl.columns
        ):
            return []

        merged = _align_baseline_reform(base_tbl, ref_tbl, self.entity_level)
        # weights from baseline
        # Build MicroDataFrame with baseline weights if available
        weights_col = "weight_value_base" if "weight_value_base" in merged.columns else None
        merged["__delta__"] = merged[f"{self.variable}_ref"] - merged[f"{self.variable}_base"]
        if self.group_variable in merged.columns:
            sub = merged[merged[self.group_variable] == self.group_value]
        else:
            sub = merged
        mdf = MicroDataFrame(sub, weights=weights_col) if weights_col else MicroDataFrame(sub)
        total_change = float(mdf["__delta__"].sum())
        denom = float(mdf[f"{self.variable}_base"].sum())
        relative_change = float(total_change / denom) if denom != 0 else float("nan")
        # Sum of weights via summing a column of ones
        sub = sub.copy()
        sub["__ones__"] = 1.0
        mdf2 = MicroDataFrame(sub, weights=weights_col) if weights_col else MicroDataFrame(sub)
        weights_sum = float(mdf2["__ones__"].sum())
        avg_change = float(total_change / weights_sum) if weights_sum != 0 else float("nan")

        period = getattr(self.baseline.dataset.data, "year", None)
        rec = ChangeByBaselineGroup(
            baseline_simulation=self.baseline,
            reform_simulation=self.reform,
            variable=self.variable,
            group_variable=self.group_variable,
            group_value=self.group_value,
            entity_level=self.entity_level,
            time_period=period,
            total_change=total_change,
            relative_change=relative_change,
            average_change_per_entity=avg_change,
        )
        return [rec]


class WinnersLosersByQuantileReportElement(ReportElement):
    """Percent and count in change buckets by quantile groups (baseline)."""

    baseline: Simulation
    reform: Simulation
    variable: str
    group_variable: str  # a precomputed quantile label variable, e.g. *_decile
    quantile_group_count: int = 10
    change_lower_bound: float = -np.inf
    change_upper_bound: float = 0.0
    change_bound_is_relative: bool = False
    entity_level: str = "household"

    def run(self) -> list[VariableChangeGroupByQuantileGroup]:
        base_tbl = _get_table(self.baseline, self.entity_level)
        ref_tbl = _get_table(self.reform, self.entity_level)
        if base_tbl is None or ref_tbl is None:
            return []
        if (
            self.variable not in base_tbl.columns
            or self.variable not in ref_tbl.columns
            or self.group_variable not in base_tbl.columns
        ):
            return []

        merged = _align_baseline_reform(base_tbl, ref_tbl, self.entity_level)
        merged["__delta__"] = merged[f"{self.variable}_ref"] - merged[f"{self.variable}_base"]
        if self.change_bound_is_relative:
            base = merged[f"{self.variable}_base"].replace({0.0: np.nan}).abs()
            merged["__delta__"] = merged["__delta__"] / base

        results: list[VariableChangeGroupByQuantileGroup] = []
        period = getattr(self.baseline.dataset.data, "year", None)
        weights_col = "weight_value_base" if "weight_value_base" in merged.columns else None
        for g, grp in merged.groupby(self.group_variable):
            grp = grp.copy()
            grp["__in_bucket__"] = (
                (grp["__delta__"] >= self.change_lower_bound)
                & (grp["__delta__"] < self.change_upper_bound)
            ).astype(int)
            mdf = MicroDataFrame(grp, weights=weights_col) if weights_col else MicroDataFrame(grp)
            percent = float(mdf["__in_bucket__"].mean())
            entities = float(mdf["__in_bucket__"].sum())

            results.append(
                VariableChangeGroupByQuantileGroup(
                    baseline_simulation=self.baseline,
                    reform_simulation=self.reform,
                    variable=self.variable,
                    group_variable=self.group_variable,
                    quantile_group=int(g) if isinstance(g, (int, np.integer)) else g,
                    quantile_group_count=self.quantile_group_count,
                    change_lower_bound=float(self.change_lower_bound),
                    change_upper_bound=float(self.change_upper_bound),
                    change_bound_is_relative=self.change_bound_is_relative,
                    fixed_entity_count_per_quantile_group=self.entity_level,
                    percent_of_group_in_change_group=percent,
                    entities_in_group_in_change_group=entities,
                )
            )

        return results


class VariableChangeByValueReportElement(ReportElement):
    """Change group shares by exact group variable value."""

    baseline: Simulation
    reform: Simulation
    variable: str
    group_variable: str
    change_lower_bound: float = -np.inf
    change_upper_bound: float = 0.0
    change_bound_is_relative: bool = False
    entity_level: str = "household"

    def run(self) -> list[VariableChangeGroupByVariableValue]:
        base_tbl = _get_table(self.baseline, self.entity_level)
        ref_tbl = _get_table(self.reform, self.entity_level)
        if base_tbl is None or ref_tbl is None:
            return []
        if (
            self.variable not in base_tbl.columns
            or self.variable not in ref_tbl.columns
            or self.group_variable not in base_tbl.columns
        ):
            return []

        merged = _align_baseline_reform(base_tbl, ref_tbl, self.entity_level)
        merged["__delta__"] = merged[f"{self.variable}_ref"] - merged[f"{self.variable}_base"]
        if self.change_bound_is_relative:
            base = merged[f"{self.variable}_base"].replace({0.0: np.nan}).abs()
            merged["__delta__"] = merged["__delta__"] / base

        results: list[VariableChangeGroupByVariableValue] = []
        weights_col = "weight_value_base" if "weight_value_base" in merged.columns else None
        for val, grp in merged.groupby(self.group_variable):
            grp = grp.copy()
            grp["__in_bucket__"] = (
                (grp["__delta__"] >= self.change_lower_bound)
                & (grp["__delta__"] < self.change_upper_bound)
            ).astype(int)
            mdf = MicroDataFrame(grp, weights=weights_col) if weights_col else MicroDataFrame(grp)
            percent = float(mdf["__in_bucket__"].mean())
            entities = float(mdf["__in_bucket__"].sum())

            results.append(
                VariableChangeGroupByVariableValue(
                    baseline_simulation=self.baseline,
                    reform_simulation=self.reform,
                    variable=self.variable,
                    group_variable=self.group_variable,
                    group_variable_value=val,
                    fixed_entity_count_per_quantile_group=self.entity_level,
                    percent_of_group_in_change_group=percent,
                    entities_in_group_in_change_group=entities,
                )
            )

        return results
