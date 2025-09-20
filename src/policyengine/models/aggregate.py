from enum import Enum
from typing import TYPE_CHECKING, Literal

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel

if TYPE_CHECKING:
    from policyengine.models import Simulation


class AggregateType(str, Enum):
    SUM = "sum"
    MEAN = "mean"
    COUNT = "count"


class Aggregate(BaseModel):
    simulation: "Simulation"
    entity: str
    variable_name: str
    year: int | None = None
    filter_variable_name: str | None = None
    filter_variable_value: str | None = None
    filter_variable_leq: float | None = None
    filter_variable_geq: float | None = None
    aggregate_function: Literal[
        AggregateType.SUM, AggregateType.MEAN, AggregateType.COUNT
    ]

    value: float | None = None

    @staticmethod
    def run(aggregates: list["Aggregate"]) -> list["Aggregate"]:
        # Assumes that all aggregates are from the same simulation
        results = []

        tables = aggregates[0].simulation.result
        for table in tables:
            tables[table] = pd.DataFrame(tables[table])
            weight_col = f"{table}_weight"
            if weight_col in tables[table].columns:
                tables[table] = MicroDataFrame(
                    tables[table], weights=weight_col
                )

        for agg in aggregates:
            if agg.entity not in tables:
                raise ValueError(
                    f"Entity {agg.entity} not found in simulation results"
                )
            table = tables[agg.entity]

            if agg.variable_name not in table.columns:
                raise ValueError(
                    f"Variable {agg.variable_name} not found in entity {agg.entity}"
                )

            df = table

            if agg.year is None:
                agg.year = aggregates[0].simulation.dataset.year

            if agg.filter_variable_name is not None:
                if agg.filter_variable_name not in df.columns:
                    raise ValueError(
                        f"Filter variable {agg.filter_variable_name} not found in entity {agg.entity}"
                    )
                if agg.filter_variable_value is not None:
                    df = df[
                        df[agg.filter_variable_name]
                        == agg.filter_variable_value
                    ]
                if agg.filter_variable_leq is not None:
                    df = df[
                        df[agg.filter_variable_name] <= agg.filter_variable_leq
                    ]
                if agg.filter_variable_geq is not None:
                    df = df[
                        df[agg.filter_variable_name] >= agg.filter_variable_geq
                    ]

            if agg.aggregate_function == AggregateType.SUM:
                agg.value = float(df[agg.variable_name].sum())
            elif agg.aggregate_function == AggregateType.MEAN:
                agg.value = float(df[agg.variable_name].mean())
            elif agg.aggregate_function == AggregateType.COUNT:
                agg.value = float((df[agg.variable_name] > 0).sum())

            results.append(agg)

        return results
