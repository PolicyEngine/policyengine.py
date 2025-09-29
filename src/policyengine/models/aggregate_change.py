from enum import Enum
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from policyengine.models import Simulation


class AggregateType(str, Enum):
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    COUNT = "count"


class AggregateChange(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    baseline_simulation: "Simulation | None" = None
    comparison_simulation: "Simulation | None" = None
    entity: str
    variable_name: str
    year: int | None = None
    filter_variable_name: str | None = None
    filter_variable_value: str | None = None
    filter_variable_leq: float | None = None
    filter_variable_geq: float | None = None
    aggregate_function: Literal[
        AggregateType.SUM, AggregateType.MEAN, AggregateType.MEDIAN, AggregateType.COUNT
    ]
    reportelement_id: str | None = None

    baseline_value: float | None = None
    comparison_value: float | None = None
    change: float | None = None
    relative_change: float | None = None

    @staticmethod
    def run(aggregate_changes: list["AggregateChange"]) -> list["AggregateChange"]:
        """Process aggregate changes, handling multiple simulation pairs."""
        results = []

        for agg_change in aggregate_changes:
            if agg_change.baseline_simulation is None:
                raise ValueError("AggregateChange has no baseline simulation attached")
            if agg_change.comparison_simulation is None:
                raise ValueError("AggregateChange has no comparison simulation attached")

            # Compute baseline value
            baseline_value = AggregateChange._compute_single_aggregate(
                agg_change, agg_change.baseline_simulation
            )

            # Compute comparison value
            comparison_value = AggregateChange._compute_single_aggregate(
                agg_change, agg_change.comparison_simulation
            )

            # Compute changes
            agg_change.baseline_value = baseline_value
            agg_change.comparison_value = comparison_value
            agg_change.change = comparison_value - baseline_value

            # Compute relative change (avoiding division by zero)
            if baseline_value != 0:
                agg_change.relative_change = (comparison_value - baseline_value) / abs(baseline_value)
            else:
                agg_change.relative_change = None if comparison_value == 0 else float('inf')

            results.append(agg_change)

        return results

    @staticmethod
    def _compute_single_aggregate(
        agg_change: "AggregateChange", simulation: "Simulation"
    ) -> float:
        """Compute aggregate value for a single simulation."""
        tables = simulation.result
        # Copy tables to ensure we don't modify original dataframes
        tables = {k: v.copy() for k, v in tables.items()}

        for table in tables:
            tables[table] = pd.DataFrame(tables[table])
            weight_col = f"{table}_weight"
            if weight_col in tables[table].columns:
                tables[table] = MicroDataFrame(
                    tables[table], weights=weight_col
                )

        if agg_change.entity not in tables:
            raise ValueError(
                f"Entity {agg_change.entity} not found in simulation results"
            )

        table = tables[agg_change.entity]

        if agg_change.variable_name not in table.columns:
            raise ValueError(
                f"Variable {agg_change.variable_name} not found in entity {agg_change.entity}"
            )

        df = table

        if agg_change.year is None:
            agg_change.year = simulation.dataset.year

        # Apply filters
        if agg_change.filter_variable_name is not None:
            if agg_change.filter_variable_name not in df.columns:
                raise ValueError(
                    f"Filter variable {agg_change.filter_variable_name} not found in entity {agg_change.entity}"
                )
            if agg_change.filter_variable_value is not None:
                df = df[
                    df[agg_change.filter_variable_name]
                    == agg_change.filter_variable_value
                ]
            if agg_change.filter_variable_leq is not None:
                df = df[
                    df[agg_change.filter_variable_name] <= agg_change.filter_variable_leq
                ]
            if agg_change.filter_variable_geq is not None:
                df = df[
                    df[agg_change.filter_variable_name] >= agg_change.filter_variable_geq
                ]

        # Compute aggregate
        if agg_change.aggregate_function == AggregateType.SUM:
            value = float(df[agg_change.variable_name].sum())
        elif agg_change.aggregate_function == AggregateType.MEAN:
            value = float(df[agg_change.variable_name].mean())
        elif agg_change.aggregate_function == AggregateType.MEDIAN:
            value = float(df[agg_change.variable_name].median())
        elif agg_change.aggregate_function == AggregateType.COUNT:
            value = float((df[agg_change.variable_name] > 0).sum())
        else:
            raise ValueError(f"Unknown aggregate function: {agg_change.aggregate_function}")

        return value