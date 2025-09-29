from enum import Enum
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, Field
import time

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
    entity: str | None = None
    variable_name: str
    year: int | None = None
    filter_variable_name: str | None = None
    filter_variable_value: str | None = None
    filter_variable_leq: float | None = None
    filter_variable_geq: float | None = None
    filter_variable_quantile_leq: float | None = None
    filter_variable_quantile_geq: float | None = None
    filter_variable_quantile_value: str | None = None
    aggregate_function: Literal[
        AggregateType.SUM, AggregateType.MEAN, AggregateType.MEDIAN, AggregateType.COUNT
    ]
    reportelement_id: str | None = None

    baseline_value: float | None = None
    comparison_value: float | None = None
    change: float | None = None
    relative_change: float | None = None

    @staticmethod
    def _infer_entity(variable_name: str, filter_variable_name: str | None, tables: dict) -> str:
        """Infer entity from the target variable (not the filter variable).

        The entity represents what level we're aggregating at, determined by the target variable.
        Filters can be cross-entity and will be mapped if needed.
        """
        # Find entity of target variable
        for entity, table in tables.items():
            if variable_name in table.columns:
                return entity

        raise ValueError(f"Variable {variable_name} not found in any entity table")

    @staticmethod
    def _get_entity_link_columns() -> dict:
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
    def _map_variable_across_entities(
        df: pd.DataFrame,
        variable_name: str,
        source_entity: str,
        target_entity: str,
        tables: dict
    ) -> pd.Series:
        """Map a variable from source entity to target entity level."""
        links = AggregateChange._get_entity_link_columns()

        # Group to person: copy group values to persons using link column
        if source_entity != "person" and target_entity == "person":
            link_col = links.get("person", {}).get(source_entity)
            if link_col is None:
                raise ValueError(f"No known link from person to {source_entity}")

            if link_col not in tables["person"].columns:
                raise ValueError(f"Link column {link_col} not found in person table")

            # Create mapping: group position (0-based index) -> value
            # Most PolicyEngine models have entities numbered 0, 1, 2, ...
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
            person_values = AggregateChange._map_variable_across_entities(
                df, variable_name, source_entity, "person", tables
            )
            # Create temp dataframe with person values
            temp_person_df = tables["person"].copy()
            temp_person_df[variable_name] = person_values

            return AggregateChange._map_variable_across_entities(
                temp_person_df, variable_name, "person", target_entity, tables
            )

        else:
            # Same entity - shouldn't happen but return as-is
            return df[variable_name]

    @staticmethod
    def _prepare_tables(simulation: "Simulation") -> dict:
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
            baseline_tables = AggregateChange._prepare_tables(baseline_sim)
            comparison_tables = AggregateChange._prepare_tables(comparison_sim)

            prep_time = time.time()
            print(f"[PERFORMANCE]   Table preparation took {prep_time - group_start:.3f} seconds")

            # Process each item in the group
            for idx, agg_change in enumerate(group):
                item_start = time.time()

                # Infer entity if not provided (use filter variable entity if available)
                if agg_change.entity is None:
                    agg_change.entity = AggregateChange._infer_entity(
                        agg_change.variable_name,
                        agg_change.filter_variable_name,
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
            mapped_filter = AggregateChange._map_variable_across_entities(
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

        if any([agg_change.filter_variable_quantile_leq,
                agg_change.filter_variable_quantile_geq, agg_change.filter_variable_quantile_value]):

            if agg_change.filter_variable_quantile_leq is not None:
                threshold = filter_series.quantile(agg_change.filter_variable_quantile_leq)
                mask &= filter_series <= threshold

            if agg_change.filter_variable_quantile_geq is not None:
                threshold = filter_series.quantile(agg_change.filter_variable_quantile_geq)
                mask &= filter_series >= threshold

            if agg_change.filter_variable_quantile_value is not None:
                if "top" in agg_change.filter_variable_quantile_value.lower():
                    pct = float(agg_change.filter_variable_quantile_value.lower().replace("top_", "").replace("%", "")) / 100
                    threshold = filter_series.quantile(1 - pct)
                    mask &= filter_series >= threshold
                elif "bottom" in agg_change.filter_variable_quantile_value.lower():
                    pct = float(agg_change.filter_variable_quantile_value.lower().replace("bottom_", "").replace("%", "")) / 100
                    threshold = filter_series.quantile(pct)
                    mask &= filter_series <= threshold

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
                mapped_series = AggregateChange._map_variable_across_entities(
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

        try:
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
        except (ZeroDivisionError, ValueError) as e:
            return 0.0

        return value

    @staticmethod
    def _get_filter_mask(
        agg_change: "AggregateChange", simulation: "Simulation"
    ) -> pd.Series | None:
        """Get filter mask based on baseline simulation values."""
        if agg_change.filter_variable_name is None:
            return None  # No filtering needed

        tables = simulation.result
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

        df = tables[agg_change.entity]

        if agg_change.filter_variable_name not in df.columns:
            raise ValueError(
                f"Filter variable {agg_change.filter_variable_name} not found in entity {agg_change.entity}"
            )

        # Create filter mask based on baseline values
        mask = pd.Series([True] * len(df), index=df.index)

        # Apply value/range filters
        if agg_change.filter_variable_value is not None:
            mask &= df[agg_change.filter_variable_name] == agg_change.filter_variable_value

        if agg_change.filter_variable_leq is not None:
            mask &= df[agg_change.filter_variable_name] <= agg_change.filter_variable_leq

        if agg_change.filter_variable_geq is not None:
            mask &= df[agg_change.filter_variable_name] >= agg_change.filter_variable_geq

        # Apply quantile filters if specified
        if any([agg_change.filter_variable_quantile_leq,
                agg_change.filter_variable_quantile_geq, agg_change.filter_variable_quantile_value]):

            if agg_change.filter_variable_quantile_leq is not None:
                # Filter to values <= specified quantile
                threshold = df[agg_change.filter_variable_name].quantile(agg_change.filter_variable_quantile_leq)
                mask &= df[agg_change.filter_variable_name] <= threshold

            if agg_change.filter_variable_quantile_geq is not None:
                # Filter to values >= specified quantile
                threshold = df[agg_change.filter_variable_name].quantile(agg_change.filter_variable_quantile_geq)
                mask &= df[agg_change.filter_variable_name] >= threshold

            if agg_change.filter_variable_quantile_value is not None:
                # Parse quantile value like "top_10%" or "bottom_20%"
                if "top" in agg_change.filter_variable_quantile_value.lower():
                    pct = float(agg_change.filter_variable_quantile_value.lower().replace("top_", "").replace("%", "")) / 100
                    threshold = df[agg_change.filter_variable_name].quantile(1 - pct)
                    mask &= df[agg_change.filter_variable_name] >= threshold
                elif "bottom" in agg_change.filter_variable_quantile_value.lower():
                    pct = float(agg_change.filter_variable_quantile_value.lower().replace("bottom_", "").replace("%", "")) / 100
                    threshold = df[agg_change.filter_variable_name].quantile(pct)
                    mask &= df[agg_change.filter_variable_name] <= threshold

        return mask

    @staticmethod
    def _compute_single_aggregate(
        agg_change: "AggregateChange",
        simulation: "Simulation",
        filter_mask: pd.Series | None = None
    ) -> float:
        """Compute aggregate value for a single simulation."""
        compute_start = time.time()
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

        # Apply the pre-computed filter mask if provided
        # This ensures we're using the same subset of entities for both baseline and comparison
        if filter_mask is not None:
            df = df[filter_mask]

        # Check if we have any data left after filtering
        if len(df) == 0:
            # Return 0 for empty datasets
            return 0.0

        # Compute aggregate
        try:
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
        except (ZeroDivisionError, ValueError) as e:
            # Handle cases where weights sum to zero or other computation errors
            # Return 0 for these edge cases
            return 0.0

        return value