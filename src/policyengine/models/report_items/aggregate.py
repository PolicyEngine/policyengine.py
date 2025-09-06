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

    Use `Aggregate.run([...])` to compute a list of `Aggregate` records for
    provided items that reference a simulation and variable. Items should have
    `value=None` prior to running; this method returns copies with `value`
    computed. This enables batched computation for interactive use.
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
    value: float | None = None

    @classmethod
    def build(
        cls,
        simulation: "Simulation",
        variable: str,
        entity_level: str = "person",
        filter_variable: str | None = None,
        metric: AggregateMetric = AggregateMetric.SUM,
    ) -> list["Aggregate"]:
        """Build and run aggregate calculations for all unique filter values.

        If filter_variable is provided, creates one Aggregate per unique value.
        Otherwise creates a single Aggregate for the entire dataset.
        """
        items = []
        if filter_variable is not None:
            # Get unique values of the filter variable
            data: SingleYearDataset = simulation.result.data  # type: ignore[attr-defined]
            table: pd.DataFrame = data.tables[entity_level]
            if filter_variable in table.columns:
                unique_values = table[filter_variable].unique()
                for value in unique_values:
                    items.append(
                        cls(
                            simulation=simulation,
                            variable=variable,
                            entity_level=entity_level,
                            filter_variable=filter_variable,
                            filter_variable_value=value,
                            metric=metric,
                        )
                    )
        else:
            items.append(
                cls(
                    simulation=simulation,
                    variable=variable,
                    entity_level=entity_level,
                    metric=metric,
                )
            )

        # Run the computation
        return cls.run(items)

    @staticmethod
    def run(items: list["Aggregate"]) -> list["Aggregate"]:
        """Compute values for provided Aggregate items.

        - Assumes all items reference valid `simulation.result.data` with
          `tables[entity_level]` and optional `weight_value` column.
        - Returns new Aggregate instances with `time_period` and `value` set.
        - Keeps implementation simple while reusing tables per entity_level.
        """
        if not items:
            return []

        # Group items by entity_level to reuse the same table/mdf
        by_level: dict[str, list[Aggregate]] = {}
        for it in items:
            by_level.setdefault(it.entity_level, []).append(it)

        out: list[Aggregate] = []
        for entity_level, group in by_level.items():
            sim = group[0].simulation
            # Assume shape is correct: sim.result.data is SingleYearDataset
            data: SingleYearDataset = sim.result.data  # type: ignore[attr-defined]
            table: pd.DataFrame = data.tables[entity_level]
            time_period = getattr(sim.dataset.data, "year", None)
            use_weights = "weight_value" in table.columns

            for it in group:
                df = table
                # Apply value and range filters if provided
                if (
                    it.filter_variable is not None
                    and it.filter_variable in df.columns
                ):
                    mask = pd.Series(True, index=df.index)
                    if it.filter_variable_value is not None:
                        mask &= (
                            df[it.filter_variable] == it.filter_variable_value
                        )
                    if it.filter_variable_min_value is not None:
                        mask &= (
                            df[it.filter_variable]
                            >= it.filter_variable_min_value
                        )
                    if it.filter_variable_max_value is not None:
                        mask &= (
                            df[it.filter_variable]
                            < it.filter_variable_max_value
                        )
                    df = df.loc[mask]

                mdf = (
                    MicroDataFrame(df, weights="weight_value")
                    if use_weights and "weight_value" in df.columns
                    else MicroDataFrame(df)
                )
                s = mdf[it.variable]
                if it.metric == AggregateMetric.MEAN:
                    val = float(s.mean())
                elif it.metric == AggregateMetric.MEDIAN:
                    val = float(s.median())
                elif it.metric == AggregateMetric.SUM:
                    val = float(s.sum())
                else:
                    val = float("nan")

                payload = it.model_dump()
                payload.update({"time_period": time_period, "value": val})
                out.append(Aggregate(**payload))

        return out
