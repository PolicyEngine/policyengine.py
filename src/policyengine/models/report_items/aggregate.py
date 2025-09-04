from __future__ import annotations

from enum import Enum
import pandas as pd
from microdf import MicroDataFrame
from policyengine.models.simulation import (
    Simulation,
)  # ensure forward ref resolution

from policyengine.models.single_year_dataset import SingleYearDataset
from .base import ReportElementDataItem


class AggregateMetric(str, Enum):
    MEAN = "mean"
    MEDIAN = "median"
    SUM = "sum"


class Aggregate(ReportElementDataItem):
    """Reusable aggregate record for a simulation and variable.

    Use `Aggregate.build(...)` to compute a list of `Aggregate` records from a
    simulation, optionally grouped by a filter variable.
    """

    simulation: "Simulation"
    time_period: int | str | None = None
    variable: str
    entity_level: str = "person"
    filter_variable: str | None = None
    filter_variable_value: object | None = None
    filter_variable_min_value: float | None = None
    filter_variable_max_value: float | None = None
    metric: AggregateMetric
    value: float

    @staticmethod
    def build(
        simulation: "Simulation",
        *,
        variable: str,
        metric: AggregateMetric = AggregateMetric.MEAN,
        entity_level: str = "person",
        filter_variable: str | None = None,
    ) -> list["Aggregate"]:
        """Compute aggregates for `variable` on `simulation`.

        Assumes the simulation result is a `SingleYearDataset` with appropriate
        tables and optional `weight_value` column for weighting.
        """
        # Assume shape is correct: sim.result.data is SingleYearDataset
        data: SingleYearDataset = simulation.result.data  # type: ignore[attr-defined]
        table: pd.DataFrame = data.tables[entity_level]

        use_weights = "weight_value" in table.columns

        def compute_metric_from_df(df: pd.DataFrame) -> float:
            mdf = (
                MicroDataFrame(df, weights="weight_value")
                if use_weights
                else MicroDataFrame(df)
            )
            s = mdf[variable]
            if metric == AggregateMetric.MEAN:
                return float(s.mean())
            if metric == AggregateMetric.MEDIAN:
                return float(s.median())
            if metric == AggregateMetric.SUM:
                return float(s.sum())
            return float("nan")

        results: list[Aggregate] = []
        time_period = getattr(simulation.dataset.data, "year", None)
        if filter_variable and filter_variable in table.columns:
            for val, grp in table.groupby(filter_variable):
                value = compute_metric_from_df(grp)
                results.append(
                    Aggregate(
                        simulation=simulation,
                        time_period=time_period,
                        variable=variable,
                        entity_level=entity_level,
                        filter_variable=filter_variable,
                        filter_variable_value=val,
                        metric=metric,
                        value=value,
                    )
                )
        else:
            value = compute_metric_from_df(table)
            results.append(
                Aggregate(
                    simulation=simulation,
                    time_period=time_period,
                    variable=variable,
                    entity_level=entity_level,
                    filter_variable=None,
                    filter_variable_value=None,
                    metric=metric,
                    value=value,
                )
            )

        return results
