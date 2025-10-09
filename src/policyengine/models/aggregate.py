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


class AggregateUtils:
    """Shared utilities for aggregate calculations."""

    @staticmethod
    def prepare_tables(simulation: "Simulation") -> dict:
        """Prepare dataframes from simulation result once."""
        tables = simulation.result
        tables = {k: v.copy() for k, v in tables.items()}

        for table in tables:
            tables[table] = pd.DataFrame(tables[table])
            weight_col = f"{table}_weight"
            if weight_col in tables[table].columns:
                tables[table] = MicroDataFrame(
                    tables[table], weights=weight_col
                )

        return tables

    @staticmethod
    def infer_entity(variable_name: str, tables: dict) -> str:
        """Infer entity from variable name by checking which table contains it."""
        for entity, table in tables.items():
            if variable_name in table.columns:
                return entity
        raise ValueError(f"Variable {variable_name} not found in any entity table")

    @staticmethod
    def get_entity_link_columns() -> dict:
        """Return mapping of entity relationships for common PolicyEngine models."""
        return {
            # person -> group entity links (copy values down)
            "person": {
                "benunit": "person_benunit_id",
                "household": "person_household_id",
                "family": "person_family_id",
                "tax_unit": "person_tax_unit_id",
                "spm_unit": "person_spm_unit_id",
            },
        }

    @staticmethod
    def map_variable_across_entities(
        df: pd.DataFrame,
        variable_name: str,
        source_entity: str,
        target_entity: str,
        tables: dict
    ) -> pd.Series:
        """Map a variable from source entity to target entity level."""
        links = AggregateUtils.get_entity_link_columns()

        # Group to person: copy group values to persons using link column
        if source_entity != "person" and target_entity == "person":
            link_col = links.get("person", {}).get(source_entity)
            if link_col is None:
                raise ValueError(f"No known link from person to {source_entity}")

            if link_col not in tables["person"].columns:
                raise ValueError(f"Link column {link_col} not found in person table")

            # Create mapping: group position (0-based index) -> value
            group_values = df[variable_name].values

            # Map to person level using the link column
            person_table = tables["person"]
            person_group_ids = person_table[link_col].values

            # Map each person to their group's value
            result = pd.Series([group_values[int(gid)] if int(gid) < len(group_values) else 0
                               for gid in person_group_ids], index=person_table.index)
            return result

        # Person to group: sum persons' values to group level
        elif source_entity == "person" and target_entity != "person":
            link_col = links.get("person", {}).get(target_entity)
            if link_col is None:
                raise ValueError(f"No known link from person to {target_entity}")

            if link_col not in df.columns:
                raise ValueError(f"Link column {link_col} not found in person table")

            # Sum by group - need to align with group table length
            grouped = df.groupby(link_col)[variable_name].sum()

            # Create a series aligned with the group table
            group_table = tables[target_entity]
            result = pd.Series([grouped.get(i, 0) for i in range(len(group_table))],
                              index=group_table.index)
            return result

        # Group to group: try via person as intermediary
        elif source_entity != "person" and target_entity != "person":
            # Map source -> person -> target
            person_values = AggregateUtils.map_variable_across_entities(
                df, variable_name, source_entity, "person", tables
            )
            # Create temp dataframe with person values
            temp_person_df = tables["person"].copy()
            temp_person_df[variable_name] = person_values

            return AggregateUtils.map_variable_across_entities(
                temp_person_df, variable_name, "person", target_entity, tables
            )

        else:
            # Same entity - shouldn't happen but return as-is
            return df[variable_name]

    @staticmethod
    def compute_aggregate(
        variable_series: pd.Series | MicroDataFrame,
        aggregate_function: str
    ) -> float:
        """Compute aggregate value from a series."""
        if len(variable_series) == 0:
            return 0.0

        # Check if this is a weight column being summed from a MicroDataFrame
        # If so, use unweighted sum to avoid weight^2
        is_weight_column = (
            isinstance(variable_series, pd.Series) and
            hasattr(variable_series, 'name') and
            variable_series.name and
            'weight' in str(variable_series.name).lower()
        )

        if aggregate_function == AggregateType.SUM:
            if is_weight_column:
                # Use unweighted sum for weight columns
                return float(pd.Series(variable_series.values).sum())
            return float(variable_series.sum())
        elif aggregate_function == AggregateType.MEAN:
            return float(variable_series.mean())
        elif aggregate_function == AggregateType.MEDIAN:
            return float(variable_series.median())
        elif aggregate_function == AggregateType.COUNT:
            # For COUNT, return the actual number of entries (not weighted)
            # Use len() to count all entries regardless of value
            return float(len(variable_series))
        else:
            raise ValueError(f"Unknown aggregate function: {aggregate_function}")


class Aggregate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    simulation: "Simulation | None" = None
    entity: str | None = None
    variable_name: str
    year: int | None = None
    filter_variable_name: str | None = None
    filter_variable_value: str | None = None
    filter_variable_leq: float | None = None
    filter_variable_geq: float | None = None
    filter_variable_quantile_leq: float | None = None
    filter_variable_quantile_geq: float | None = None
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

        # Use centralized table preparation
        tables = AggregateUtils.prepare_tables(simulation)

        for agg in aggregates:
            # Infer entity if not provided
            if agg.entity is None:
                agg.entity = AggregateUtils.infer_entity(agg.variable_name, tables)

            if agg.entity not in tables:
                raise ValueError(
                    f"Entity {agg.entity} not found in simulation results"
                )

            if agg.year is None:
                agg.year = simulation.dataset.year

            # Get the target table
            target_table = tables[agg.entity]

            # Handle cross-entity filters
            mask = None
            if agg.filter_variable_name is not None:
                # Find which entity contains the filter variable
                filter_entity = None
                for entity, table in tables.items():
                    if agg.filter_variable_name in table.columns:
                        filter_entity = entity
                        break

                if filter_entity is None:
                    raise ValueError(
                        f"Filter variable {agg.filter_variable_name} not found in any entity"
                    )

                # Get the filter series (mapped if needed)
                if filter_entity == agg.entity:
                    filter_series = tables[agg.entity][agg.filter_variable_name]
                else:
                    # Different entity - map filter variable to target entity
                    filter_df = tables[filter_entity]
                    filter_series = AggregateUtils.map_variable_across_entities(
                        filter_df,
                        agg.filter_variable_name,
                        filter_entity,
                        agg.entity,
                        tables
                    )

                # Build mask
                mask = pd.Series([True] * len(target_table), index=target_table.index)

                # Apply value/range filters
                if agg.filter_variable_value is not None:
                    mask &= filter_series == agg.filter_variable_value
                if agg.filter_variable_leq is not None:
                    mask &= filter_series <= agg.filter_variable_leq
                if agg.filter_variable_geq is not None:
                    mask &= filter_series >= agg.filter_variable_geq

                # Apply quantile filters
                if agg.filter_variable_quantile_leq is not None:
                    threshold = filter_series.quantile(agg.filter_variable_quantile_leq)
                    mask &= filter_series <= threshold
                if agg.filter_variable_quantile_geq is not None:
                    threshold = filter_series.quantile(agg.filter_variable_quantile_geq)
                    mask &= filter_series >= threshold

            # Find which entity contains the variable
            variable_entity = None
            for entity, table in tables.items():
                if agg.variable_name in table.columns:
                    variable_entity = entity
                    break

            if variable_entity is None:
                raise ValueError(
                    f"Variable {agg.variable_name} not found in any entity"
                )

            # Get variable data (mapped if needed)
            if variable_entity == agg.entity:
                # Same entity - extract from target table
                if mask is not None:
                    # Filter the entire table to preserve MicroDataFrame weights
                    filtered_table = target_table[mask]
                    variable_series = filtered_table[agg.variable_name]
                else:
                    variable_series = target_table[agg.variable_name]
            else:
                # Map variable to target entity
                source_table = tables[variable_entity]
                variable_series = AggregateUtils.map_variable_across_entities(
                    source_table,
                    agg.variable_name,
                    variable_entity,
                    agg.entity,
                    tables
                )
                # Apply mask after mapping
                if mask is not None:
                    variable_series = variable_series[mask]

            # Compute aggregate using centralized function
            agg.value = AggregateUtils.compute_aggregate(
                variable_series,
                agg.aggregate_function
            )

            results.append(agg)

        return results
