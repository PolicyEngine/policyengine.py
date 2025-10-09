from enum import Enum
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, Field
import time

from .aggregate import AggregateUtils, AggregateType

if TYPE_CHECKING:
    from policyengine.models import Simulation


class AggregateChange(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    baseline_simulation: "Simulation | None" = None
    comparison_simulation: "Simulation | None" = None
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

    baseline_value: float | None = None
    comparison_value: float | None = None
    change: float | None = None
    relative_change: float | None = None


    @staticmethod
    def run(aggregate_changes: list["AggregateChange"]) -> list["AggregateChange"]:
        """Process aggregate changes, batching those with the same simulation pair."""
        start_time = time.time()
        print(f"[PERFORMANCE] AggregateChange.run starting with {len(aggregate_changes)} items")

        # Group aggregate changes by simulation pair for batch processing
        from collections import defaultdict
        grouped = defaultdict(list)
        for agg_change in aggregate_changes:
            if agg_change.baseline_simulation is None:
                raise ValueError("AggregateChange has no baseline simulation attached")
            if agg_change.comparison_simulation is None:
                raise ValueError("AggregateChange has no comparison simulation attached")

            key = (agg_change.baseline_simulation.id, agg_change.comparison_simulation.id)
            grouped[key].append(agg_change)

        print(f"[PERFORMANCE] Grouped {len(aggregate_changes)} items into {len(grouped)} simulation pairs")

        results = []

        for (baseline_id, comparison_id), group in grouped.items():
            group_start = time.time()
            print(f"[PERFORMANCE] Processing batch of {len(group)} items for sim pair {baseline_id[:8]}...{comparison_id[:8]}")

            # Get simulation objects once for the group
            baseline_sim = group[0].baseline_simulation
            comparison_sim = group[0].comparison_simulation

            # Pre-compute simulation dataframes once per batch
            baseline_tables = AggregateUtils.prepare_tables(baseline_sim)
            comparison_tables = AggregateUtils.prepare_tables(comparison_sim)

            prep_time = time.time()
            print(f"[PERFORMANCE]   Table preparation took {prep_time - group_start:.3f} seconds")

            # Process each item in the group
            for idx, agg_change in enumerate(group):
                item_start = time.time()

                # Infer entity if not provided
                if agg_change.entity is None:
                    agg_change.entity = AggregateUtils.infer_entity(
                        agg_change.variable_name,
                        baseline_tables
                    )

                # Compute filter mask on baseline
                filter_mask = AggregateChange._get_filter_mask_from_tables(
                    agg_change, baseline_tables
                )

                # Compute baseline value
                baseline_value = AggregateChange._compute_single_aggregate_from_tables(
                    agg_change, baseline_tables, filter_mask
                )

                # Compute comparison value using same filter
                comparison_value = AggregateChange._compute_single_aggregate_from_tables(
                    agg_change, comparison_tables, filter_mask
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

            group_time = time.time()
            print(f"[PERFORMANCE]   Batch processing took {group_time - group_start:.3f} seconds ({(group_time - group_start) / len(group):.3f}s per item)")

        total_time = time.time()
        print(f"[PERFORMANCE] AggregateChange.run completed in {total_time - start_time:.2f} seconds")
        return results

    @staticmethod
    def _get_filter_mask_from_tables(
        agg_change: "AggregateChange", tables: dict
    ) -> pd.Series | None:
        """Get filter mask from pre-prepared tables, handling cross-entity filters."""
        if agg_change.filter_variable_name is None:
            return None

        if agg_change.entity not in tables:
            raise ValueError(
                f"Entity {agg_change.entity} not found in simulation results"
            )

        # Find which entity contains the filter variable
        filter_entity = None
        for entity, table in tables.items():
            if agg_change.filter_variable_name in table.columns:
                filter_entity = entity
                break

        if filter_entity is None:
            raise ValueError(
                f"Filter variable {agg_change.filter_variable_name} not found in any entity"
            )

        # Get the dataframe for filtering
        if filter_entity == agg_change.entity:
            # Same entity - use directly
            df = tables[agg_change.entity]
            filter_series = df[agg_change.filter_variable_name]
        else:
            # Different entity - need to map filter variable to target entity
            filter_df = tables[filter_entity]
            mapped_filter = AggregateUtils.map_variable_across_entities(
                filter_df,
                agg_change.filter_variable_name,
                filter_entity,
                agg_change.entity,
                tables
            )
            df = tables[agg_change.entity]
            filter_series = mapped_filter

        mask = pd.Series([True] * len(df), index=df.index)

        if agg_change.filter_variable_value is not None:
            mask &= filter_series == agg_change.filter_variable_value

        if agg_change.filter_variable_leq is not None:
            mask &= filter_series <= agg_change.filter_variable_leq

        if agg_change.filter_variable_geq is not None:
            mask &= filter_series >= agg_change.filter_variable_geq

        if agg_change.filter_variable_quantile_leq is not None or agg_change.filter_variable_quantile_geq is not None:
            if agg_change.filter_variable_quantile_leq is not None:
                threshold = filter_series.quantile(agg_change.filter_variable_quantile_leq)
                mask &= filter_series <= threshold

            if agg_change.filter_variable_quantile_geq is not None:
                threshold = filter_series.quantile(agg_change.filter_variable_quantile_geq)
                mask &= filter_series >= threshold

        return mask

    @staticmethod
    def _compute_single_aggregate_from_tables(
        agg_change: "AggregateChange",
        tables: dict,
        filter_mask: pd.Series | None = None
    ) -> float:
        """Compute aggregate value from pre-prepared tables."""
        if agg_change.entity not in tables:
            raise ValueError(
                f"Entity {agg_change.entity} not found in simulation results"
            )

        # Check if variable is in the target entity
        target_entity = agg_change.entity
        variable_entity = None

        # Find which entity contains the variable
        for entity, table in tables.items():
            if agg_change.variable_name in table.columns:
                variable_entity = entity
                break

        if variable_entity is None:
            raise ValueError(
                f"Variable {agg_change.variable_name} not found in any entity"
            )

        # If variable is in a different entity than the filter, we need to map
        if variable_entity != target_entity:
            # Get the variable data from its native entity
            source_table = tables[variable_entity]

            # Map it to the target entity level
            try:
                mapped_series = AggregateUtils.map_variable_across_entities(
                    source_table,
                    agg_change.variable_name,
                    variable_entity,
                    target_entity,
                    tables
                )
                # Create a temporary dataframe with the mapped variable
                table = tables[target_entity].copy()
                table[agg_change.variable_name] = mapped_series
            except ValueError as e:
                # If mapping fails, raise informative error
                raise ValueError(
                    f"Variable {agg_change.variable_name} is in {variable_entity} entity, "
                    f"but filters are at {target_entity} level. Cannot map between these entities: {str(e)}"
                )
        else:
            table = tables[agg_change.entity]

        df = table

        if filter_mask is not None:
            df = df[filter_mask]

        if len(df) == 0:
            return 0.0

        # Use centralized compute function
        return AggregateUtils.compute_aggregate(
            df[agg_change.variable_name],
            agg_change.aggregate_function
        )

