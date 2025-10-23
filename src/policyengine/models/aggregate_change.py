from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, SkipValidation

from .aggregate import AggregateType, DataEngine

if TYPE_CHECKING:
    from policyengine.models import Simulation


class AggregateChange(BaseModel):
    """Calculates the change in an aggregate between baseline and comparison simulations."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    baseline_simulation: SkipValidation["Simulation | None"] = None
    comparison_simulation: SkipValidation["Simulation | None"] = None
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

    baseline_value: float | None = None
    comparison_value: float | None = None
    change: float | None = None
    relative_change: float | None = None

    @staticmethod
    def run(aggregate_changes: list["AggregateChange"]) -> list["AggregateChange"]:
        """Process aggregate changes efficiently by batching those with same simulation pair."""
        # Group by simulation pair for batch processing
        by_sim_pair = {}
        for agg_change in aggregate_changes:
            if agg_change.baseline_simulation is None:
                raise ValueError("AggregateChange missing baseline_simulation")
            if agg_change.comparison_simulation is None:
                raise ValueError("AggregateChange missing comparison_simulation")

            key = (
                id(agg_change.baseline_simulation),
                id(agg_change.comparison_simulation)
            )
            if key not in by_sim_pair:
                by_sim_pair[key] = []
            by_sim_pair[key].append(agg_change)

        results = []
        for pair_aggregates in by_sim_pair.values():
            if not pair_aggregates:
                continue

            # Get simulation objects
            baseline_sim = pair_aggregates[0].baseline_simulation
            comparison_sim = pair_aggregates[0].comparison_simulation

            # Create data engines once per simulation pair (batch optimization)
            baseline_engine = DataEngine(baseline_sim.result)
            comparison_engine = DataEngine(comparison_sim.result)

            # Process each aggregate change
            for agg_change in pair_aggregates:
                if agg_change.year is None:
                    agg_change.year = baseline_sim.dataset.year

                # Infer entity if not specified
                if agg_change.entity is None:
                    agg_change.entity = baseline_engine.infer_entity(agg_change.variable_name)

                # Build filter specification
                filters = None
                if agg_change.filter_variable_name:
                    filters = {
                        'variable': agg_change.filter_variable_name,
                        'value': agg_change.filter_variable_value,
                        'leq': agg_change.filter_variable_leq,
                        'geq': agg_change.filter_variable_geq,
                        'quantile_leq': agg_change.filter_variable_quantile_leq,
                        'quantile_geq': agg_change.filter_variable_quantile_geq,
                    }

                # Get variable series with filters for both simulations
                baseline_series = baseline_engine.get_variable_series(
                    agg_change.variable_name,
                    agg_change.entity,
                    filters
                )
                comparison_series = comparison_engine.get_variable_series(
                    agg_change.variable_name,
                    agg_change.entity,
                    filters
                )

                # Compute aggregates
                agg_change.baseline_value = baseline_engine.aggregate(
                    baseline_series,
                    agg_change.aggregate_function
                )
                agg_change.comparison_value = comparison_engine.aggregate(
                    comparison_series,
                    agg_change.aggregate_function
                )

                # Calculate changes
                agg_change.change = agg_change.comparison_value - agg_change.baseline_value

                if agg_change.baseline_value != 0:
                    agg_change.relative_change = (
                        agg_change.change / abs(agg_change.baseline_value)
                    )
                else:
                    agg_change.relative_change = (
                        None if agg_change.comparison_value == 0 else float('inf')
                    )

                results.append(agg_change)

        return results
