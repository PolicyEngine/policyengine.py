from pydantic import BaseModel
from sqlmodel import SQLModel, Field

from policyengine.models import Simulation
from enum import Enum
from typing import Literal
from policyengine.database.link import TableLink
from uuid import uuid4


class AggregateType(str, Enum):
    SUM = "sum"
    MEAN = "mean"
    COUNT = "count"


class Aggregate(BaseModel):
    simulation: Simulation
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

            if agg.year is not None and "year" in df.columns:
                df = df[df["year"] == agg.year]
            elif agg.year is None:
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
                agg.value = float(len(df))

            results.append(agg)

        return results


class AggregateTable(SQLModel, table=True):
    __tablename__ = "aggregates"

    id: str = Field(default_factory=lambda: uuid4(), primary_key=True)
    simulation_id: str = Field(
        foreign_key="simulations.id", ondelete="CASCADE"
    )
    entity: str
    variable_name: str
    year: int | None = None
    filter_variable_name: str | None = None
    filter_variable_value: str | None = None
    filter_variable_leq: float | None = None
    filter_variable_geq: float | None = None
    aggregate_function: str
    value: float | None = None


aggregate_table_link = TableLink(
    model_cls=Aggregate,
    table_cls=AggregateTable,
    model_to_table_custom_transforms=dict(
        simulation_id=lambda a: a.simulation.id,
    ),
)
