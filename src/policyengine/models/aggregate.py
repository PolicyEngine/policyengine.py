from enum import Enum
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

import pandas as pd
from microdf import MicroDataFrame
from pydantic import BaseModel, ConfigDict, Field, SkipValidation

if TYPE_CHECKING:
    from policyengine.models import Simulation


class AggregateType(str, Enum):
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    COUNT = "count"


class DataEngine:
    """Clean data processing engine for aggregations."""

    def __init__(self, tables: dict):
        """Initialize with simulation result tables."""
        self.tables = self._prepare_tables(tables)

    @staticmethod
    def _prepare_tables(tables: dict) -> dict[str, pd.DataFrame]:
        """Convert tables to DataFrames with MicroDataFrame for weighted columns."""
        prepared = {}
        for name, table in tables.items():
            df = pd.DataFrame(table.copy() if hasattr(table, 'copy') else table)
            weight_col = f"{name}_weight"
            if weight_col in df.columns:
                df = MicroDataFrame(df, weights=weight_col)
            prepared[name] = df
        return prepared

    def infer_entity(self, variable: str) -> str:
        """Infer which entity contains a variable."""
        for entity, table in self.tables.items():
            if variable in table.columns:
                return entity
        raise ValueError(f"Variable {variable} not found in any entity")

    def get_variable_series(
        self,
        variable: str,
        target_entity: str,
        filters: dict[str, Any] | None = None
    ) -> pd.Series:
        """
        Get variable series at target entity level, with optional filtering.

        Handles cross-entity mapping automatically.
        """
        # Find source entity
        source_entity = self.infer_entity(variable)

        # Apply filters first (on target entity)
        if filters:
            mask = self._build_filter_mask(filters, target_entity)
            target_table = self.tables[target_entity][mask]
        else:
            target_table = self.tables[target_entity]

        # Get variable (map if needed)
        if source_entity == target_entity:
            return target_table[variable]
        else:
            # Map across entities
            source_series = self.tables[source_entity][variable]
            mapped_series = self._map_variable(source_series, source_entity, target_entity)
            # Apply filter mask to mapped series
            if filters:
                return mapped_series[mask]
            return mapped_series

    def _build_filter_mask(self, filters: dict[str, Any], target_entity: str) -> pd.Series:
        """Build boolean mask from filter specification."""
        target_table = self.tables[target_entity]
        mask = pd.Series([True] * len(target_table), index=target_table.index)

        filter_variable = filters.get('variable')
        if not filter_variable:
            return mask

        # Get filter series (map if cross-entity)
        filter_entity = self.infer_entity(filter_variable)
        if filter_entity == target_entity:
            filter_series = target_table[filter_variable]
        else:
            filter_series = self._map_variable(
                self.tables[filter_entity][filter_variable],
                filter_entity,
                target_entity
            )

        # Apply value filters
        if 'value' in filters and filters['value'] is not None:
            mask &= filter_series == filters['value']

        if 'leq' in filters and filters['leq'] is not None:
            mask &= filter_series <= filters['leq']

        if 'geq' in filters and filters['geq'] is not None:
            mask &= filter_series >= filters['geq']

        # Apply quantile filters
        if 'quantile_leq' in filters and filters['quantile_leq'] is not None:
            threshold = filter_series.quantile(filters['quantile_leq'])
            mask &= filter_series <= threshold

        if 'quantile_geq' in filters and filters['quantile_geq'] is not None:
            threshold = filter_series.quantile(filters['quantile_geq'])
            mask &= filter_series >= threshold

        return mask

    def _map_variable(
        self,
        series: pd.Series,
        source_entity: str,
        target_entity: str
    ) -> pd.Series:
        """Map a variable from source to target entity."""
        if source_entity == target_entity:
            return series

        # Default entity links (can be overridden)
        person_links = {
            "benunit": "person_benunit_id",
            "household": "person_household_id",
            "family": "person_family_id",
            "tax_unit": "person_tax_unit_id",
            "spm_unit": "person_spm_unit_id",
        }

        # Group to person: copy values down
        if source_entity != "person" and target_entity == "person":
            link_col = person_links.get(source_entity)
            if not link_col:
                raise ValueError(f"No link from person to {source_entity}")

            person_table = self.tables["person"]
            if link_col not in person_table.columns:
                raise ValueError(f"Link column {link_col} not in person table")

            group_values = series.values
            person_group_ids = person_table[link_col].values
            return pd.Series(
                [group_values[int(gid)] if int(gid) < len(group_values) else 0
                 for gid in person_group_ids],
                index=person_table.index
            )

        # Person to group: aggregate up
        elif source_entity == "person" and target_entity != "person":
            link_col = person_links.get(target_entity)
            if not link_col:
                raise ValueError(f"No link from person to {target_entity}")

            person_table = self.tables["person"]
            if link_col not in person_table.columns:
                raise ValueError(f"Link column {link_col} not in person table")

            grouped = pd.DataFrame({
                link_col: person_table[link_col],
                'value': series
            }).groupby(link_col)['value'].sum()

            target_table = self.tables[target_entity]
            return pd.Series(
                [grouped.get(i, 0) for i in range(len(target_table))],
                index=target_table.index
            )

        # Group to group: via person
        else:
            person_series = self._map_variable(series, source_entity, "person")
            return self._map_variable(person_series, "person", target_entity)

    @staticmethod
    def aggregate(series: pd.Series, function: AggregateType) -> float:
        """Apply aggregation function to series."""
        if len(series) == 0:
            return 0.0

        # Avoid double-weighting weight columns
        is_weight = (
            hasattr(series, 'name') and
            series.name and
            'weight' in str(series.name).lower()
        )

        if function == AggregateType.SUM:
            if is_weight:
                return float(pd.Series(series.values).sum())
            return float(series.sum())
        elif function == AggregateType.MEAN:
            return float(series.mean())
        elif function == AggregateType.MEDIAN:
            return float(series.median())
        elif function == AggregateType.COUNT:
            return float(len(series))
        else:
            raise ValueError(f"Unknown aggregate function: {function}")


class Aggregate(BaseModel):
    """Aggregate calculation."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    simulation: SkipValidation["Simulation | None"] = None
    entity: str | None = None
    variable_name: str
    year: int | None = None
    filter_variable_name: str | None = None
    filter_variable_value: Any | None = None
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
        """Process aggregates efficiently by batching those with same simulation."""
        # Group by simulation for batch processing
        by_simulation = {}
        for agg in aggregates:
            sim_id = id(agg.simulation) if agg.simulation else None
            if sim_id not in by_simulation:
                by_simulation[sim_id] = []
            by_simulation[sim_id].append(agg)

        results = []
        for sim_aggregates in by_simulation.values():
            if not sim_aggregates:
                continue

            simulation = sim_aggregates[0].simulation
            if simulation is None:
                raise ValueError("Aggregate has no simulation")

            # Create data engine once per simulation (batch optimization)
            engine = DataEngine(simulation.result)

            # Process each aggregate
            for agg in sim_aggregates:
                if agg.year is None:
                    agg.year = simulation.dataset.year

                # Infer entity if not specified
                if agg.entity is None:
                    agg.entity = engine.infer_entity(agg.variable_name)

                # Build filter specification
                filters = None
                if agg.filter_variable_name:
                    filters = {
                        'variable': agg.filter_variable_name,
                        'value': agg.filter_variable_value,
                        'leq': agg.filter_variable_leq,
                        'geq': agg.filter_variable_geq,
                        'quantile_leq': agg.filter_variable_quantile_leq,
                        'quantile_geq': agg.filter_variable_quantile_geq,
                    }

                # Get variable series with filters
                series = engine.get_variable_series(
                    agg.variable_name,
                    agg.entity,
                    filters
                )

                # Compute aggregate
                agg.value = engine.aggregate(series, agg.aggregate_function)
                results.append(agg)

        return results
