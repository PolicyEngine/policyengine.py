from __future__ import annotations

from enum import Enum
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
                if it.filter_variable is not None:
                    # Check if filter variable is in current entity's columns
                    if it.filter_variable in df.columns:
                        mask = pd.Series(True, index=df.index)
                        if it.filter_variable_value is not None:
                            mask &= (
                                df[it.filter_variable]
                                == it.filter_variable_value
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
                    else:
                        # Filter variable is on a different entity level
                        # Try to find it in other entity tables and map via foreign keys
                        found = False
                        for other_entity, other_table in data.tables.items():
                            if (
                                other_entity != entity_level
                                and it.filter_variable in other_table.columns
                            ):
                                # Found the filter variable in another entity
                                # Check if we have a foreign key relationship
                                fk_col = f"{entity_level}_{other_entity}_id"
                                if fk_col in df.columns:
                                    # Map filter from other entity to current entity
                                    other_df = other_table.set_index(
                                        f"{other_entity}_id"
                                    )
                                    mapped_filter = other_df.loc[
                                        df[fk_col], it.filter_variable
                                    ].values

                                    mask = pd.Series(True, index=df.index)
                                    if it.filter_variable_value is not None:
                                        mask &= (
                                            mapped_filter
                                            == it.filter_variable_value
                                        )
                                    if (
                                        it.filter_variable_min_value
                                        is not None
                                    ):
                                        mask &= (
                                            mapped_filter
                                            >= it.filter_variable_min_value
                                        )
                                    if (
                                        it.filter_variable_max_value
                                        is not None
                                    ):
                                        mask &= (
                                            mapped_filter
                                            < it.filter_variable_max_value
                                        )
                                    df = df.loc[mask]
                                    found = True
                                    break

                        if not found:
                            # Could not find filter variable or foreign key relationship
                            # Skip filtering or raise warning
                            pass

                if not MICRODF_AVAILABLE:
                    raise ImportError(
                        "microdf is not installed. "
                        "Install it with: pip install 'policyengine[core]'"
                    )
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
