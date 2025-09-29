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


class Aggregate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    simulation: "Simulation | None" = None
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

    value: float | None = None

    @staticmethod
    def run(aggregates: list["Aggregate"]) -> list["Aggregate"]:
        """Process aggregates, handling multiple simulations if necessary."""
        # Group aggregates by simulation
        simulation_groups = {}
        for agg in aggregates:
            sim_id = id(agg.simulation) if agg.simulation else None
            if sim_id not in simulation_groups:
                simulation_groups[sim_id] = []
            simulation_groups[sim_id].append(agg)

        # Process each simulation group separately
        all_results = []
        for sim_id, sim_aggregates in simulation_groups.items():
            if not sim_aggregates:
                continue

            # Get the simulation from the first aggregate in this group
            simulation = sim_aggregates[0].simulation
            if simulation is None:
                raise ValueError("Aggregate has no simulation attached")

            # Process this simulation's aggregates
            group_results = Aggregate._process_simulation_aggregates(
                sim_aggregates, simulation
            )
            all_results.extend(group_results)

        return all_results

    @staticmethod
    def _process_simulation_aggregates(
        aggregates: list["Aggregate"], simulation: "Simulation"
    ) -> list["Aggregate"]:
        """Process aggregates for a single simulation."""
        results = []

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
                agg.year = simulation.dataset.year

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
            elif agg.aggregate_function == AggregateType.MEDIAN:
                agg.value = float(df[agg.variable_name].median())
            elif agg.aggregate_function == AggregateType.COUNT:
                agg.value = float((df[agg.variable_name] > 0).sum())

            results.append(agg)

        return results
