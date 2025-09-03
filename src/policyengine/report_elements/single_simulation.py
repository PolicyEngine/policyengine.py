from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

from microdf import MicroDataFrame

from policyengine.models.aggregate import Aggregate, AggregateMetric
from policyengine.models.reports import ReportElement
from policyengine.models.simulation import Simulation
from policyengine.models.single_year_dataset import SingleYearDataset


class AggregateReportElement(ReportElement):
    """Compute aggregates for a variable, optionally grouped by a filter variable.

    Returns a list of `Aggregate` records. Call `Aggregate.to_dataframe(records)` to
    obtain a DataFrame for charting.
    """

    simulation: Simulation
    variable: str
    metric: AggregateMetric = AggregateMetric.MEAN
    entity_level: str = "person"
    filter_variable: str | None = None

    def run(self) -> list[Aggregate]:
        sim = self.simulation
        if not isinstance(sim.result, (dict, SingleYearDataset)) and (
            getattr(sim, "result", None) is None
        ):
            return []

        data: SingleYearDataset | None = None
        if isinstance(sim.result, dict):  # not expected but defensive
            return []
        else:
            # Simulation.result is a Dataset with .data being SingleYearDataset
            try:
                data = sim.result.data  # type: ignore[attr-defined]
            except Exception:
                # If result is None or not shaped as expected
                return []
        if not isinstance(data, SingleYearDataset):
            return []

        # Pick target table
        table = data.tables.get(self.entity_level)
        if table is None:
            # fallback: find first table containing variable
            for tbl in data.tables.values():
                if self.variable in tbl.columns:
                    table = tbl
                    break
        if table is None or self.variable not in table.columns:
            return []

        # Use MicroDataFrame for weighted operations
        use_weights = "weight_value" in table.columns

        def compute_metric_from_df(df: pd.DataFrame) -> float:
            mdf = MicroDataFrame(df, weights="weight_value") if use_weights else MicroDataFrame(df)
            s = mdf[self.variable]
            if self.metric == AggregateMetric.MEAN:
                return float(s.mean())
            if self.metric == AggregateMetric.MEDIAN:
                return float(s.median())
            if self.metric == AggregateMetric.SUM:
                return float(s.sum())
            return float("nan")

        results: list[Aggregate] = []
        time_period = getattr(sim.dataset.data, "year", None)
        if self.filter_variable and self.filter_variable in table.columns:
            for val, grp in table.groupby(self.filter_variable):
                value = compute_metric_from_df(grp)
                results.append(
                    Aggregate(
                        simulation=sim,
                        time_period=time_period,
                        variable=self.variable,
                        entity_level=self.entity_level,
                        filter_variable=self.filter_variable,
                        filter_variable_value=val,
                        metric=self.metric,
                        value=value,
                    )
                )
        else:
            value = compute_metric_from_df(table)
            results.append(
                Aggregate(
                    simulation=sim,
                    time_period=time_period,
                    variable=self.variable,
                    entity_level=self.entity_level,
                    filter_variable=None,
                    filter_variable_value=None,
                    metric=self.metric,
                    value=value,
                )
            )

        return results
