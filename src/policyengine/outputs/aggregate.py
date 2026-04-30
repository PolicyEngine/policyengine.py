from difflib import get_close_matches
from enum import Enum
from typing import Any, Optional

from policyengine.core import Output, Simulation


class AggregateType(str, Enum):
    SUM = "sum"
    MEAN = "mean"
    COUNT = "count"


def get_aggregate_variable(simulation: Simulation, variable: str, context: str):
    """Return a model variable with an aggregation-specific error message."""
    model_version = simulation.tax_benefit_model_version
    try:
        return model_version.get_variable(variable)
    except ValueError as exc:
        candidates = sorted(model_version.variables_by_name)
        suggestions = get_close_matches(variable, candidates, n=3, cutoff=0.65)
        suggestion_text = (
            f" Did you mean: {', '.join(repr(name) for name in suggestions)}?"
            if suggestions
            else ""
        )
        raise ValueError(
            f"{context} references missing variable '{variable}' in "
            f"{model_version.model.id} version {model_version.version}."
            f"{suggestion_text}"
        ) from exc


def get_output_entity_data(simulation: Simulation, entity: str, context: str):
    """Return output data for an entity with a clear error if it is unavailable."""
    if simulation.output_dataset is None or simulation.output_dataset.data is None:
        raise ValueError(
            f"{context} requires simulation '{simulation.id}' to have an "
            "output dataset before aggregation."
        )

    try:
        return getattr(simulation.output_dataset.data, entity)
    except AttributeError as exc:
        raise ValueError(
            f"{context} references entity '{entity}', but simulation "
            f"'{simulation.id}' has no output data for that entity."
        ) from exc


def require_output_column(
    data,
    variable: str,
    entity: str,
    simulation: Simulation,
    context: str,
) -> None:
    """Raise a descriptive error when a known variable was not materialized."""
    if variable in data.columns:
        return

    model_version = simulation.tax_benefit_model_version
    raise ValueError(
        f"{context} variable '{variable}' exists in {model_version.model.id} "
        f"version {model_version.version}, but is not present in simulation "
        f"'{simulation.id}' output data for entity '{entity}'. Add '{variable}' "
        f"to {model_version.__class__.__name__}.entity_variables or pass it via "
        "Simulation.extra_variables before running the simulation."
    )


class Aggregate(Output):
    simulation: Simulation
    variable: str
    aggregate_type: AggregateType
    entity: Optional[str] = None

    filter_variable: Optional[str] = None
    filter_variable_eq: Optional[Any] = None
    filter_variable_leq: Optional[Any] = None
    filter_variable_geq: Optional[Any] = None
    filter_variable_describes_quantiles: bool = False

    # Convenient quantile specification (alternative to describes_quantiles)
    quantile: Optional[int] = (
        None  # Number of quantiles (e.g., 10 for deciles, 5 for quintiles)
    )
    quantile_eq: Optional[int] = None  # Exact quantile (e.g., 3 for 3rd decile)
    quantile_leq: Optional[int] = (
        None  # Maximum quantile (e.g., 5 for bottom 5 deciles)
    )
    quantile_geq: Optional[int] = None  # Minimum quantile (e.g., 9 for top 2 deciles)

    result: Optional[Any] = None

    def run(self):
        # Convert quantile specification to describes_quantiles format
        if self.quantile is not None:
            self.filter_variable_describes_quantiles = True
            if self.quantile_eq is not None:
                # For a specific quantile, filter between (quantile-1)/n and quantile/n
                self.filter_variable_geq = (self.quantile_eq - 1) / self.quantile
                self.filter_variable_leq = self.quantile_eq / self.quantile
            elif self.quantile_leq is not None:
                self.filter_variable_leq = self.quantile_leq / self.quantile
            elif self.quantile_geq is not None:
                self.filter_variable_geq = (self.quantile_geq - 1) / self.quantile

        var_obj = get_aggregate_variable(
            self.simulation, self.variable, "Aggregate.variable"
        )

        # Get the target entity data
        target_entity = self.entity or var_obj.entity
        data = get_output_entity_data(
            self.simulation, target_entity, "Aggregate.entity"
        )

        # Map variable to target entity if needed
        if var_obj.entity != target_entity:
            source_data = get_output_entity_data(
                self.simulation, var_obj.entity, "Aggregate.variable"
            )
            require_output_column(
                source_data,
                self.variable,
                var_obj.entity,
                self.simulation,
                "Aggregate.variable",
            )
            mapped = self.simulation.output_dataset.data.map_to_entity(
                var_obj.entity, target_entity, columns=[self.variable]
            )
            series = mapped[self.variable]
        else:
            require_output_column(
                data,
                self.variable,
                target_entity,
                self.simulation,
                "Aggregate.variable",
            )
            series = data[self.variable]

        # Apply filters
        if self.filter_variable is not None:
            filter_var_obj = get_aggregate_variable(
                self.simulation, self.filter_variable, "Aggregate.filter_variable"
            )

            if filter_var_obj.entity != target_entity:
                filter_source_data = get_output_entity_data(
                    self.simulation,
                    filter_var_obj.entity,
                    "Aggregate.filter_variable",
                )
                require_output_column(
                    filter_source_data,
                    self.filter_variable,
                    filter_var_obj.entity,
                    self.simulation,
                    "Aggregate.filter_variable",
                )
                filter_mapped = self.simulation.output_dataset.data.map_to_entity(
                    filter_var_obj.entity,
                    target_entity,
                    columns=[self.filter_variable],
                )
                filter_series = filter_mapped[self.filter_variable]
            else:
                require_output_column(
                    data,
                    self.filter_variable,
                    target_entity,
                    self.simulation,
                    "Aggregate.filter_variable",
                )
                filter_series = data[self.filter_variable]

            if self.filter_variable_describes_quantiles:
                if self.filter_variable_eq is not None:
                    threshold = filter_series.quantile(self.filter_variable_eq)
                    series = series[filter_series <= threshold]
                if self.filter_variable_leq is not None:
                    threshold = filter_series.quantile(self.filter_variable_leq)
                    series = series[filter_series <= threshold]
                if self.filter_variable_geq is not None:
                    threshold = filter_series.quantile(self.filter_variable_geq)
                    series = series[filter_series >= threshold]
            else:
                if self.filter_variable_eq is not None:
                    series = series[filter_series == self.filter_variable_eq]
                if self.filter_variable_leq is not None:
                    series = series[filter_series <= self.filter_variable_leq]
                if self.filter_variable_geq is not None:
                    series = series[filter_series >= self.filter_variable_geq]

        # Aggregate - MicroSeries will automatically apply weights
        if self.aggregate_type == AggregateType.SUM:
            self.result = series.sum()
        elif self.aggregate_type == AggregateType.MEAN:
            self.result = series.mean()
        elif self.aggregate_type == AggregateType.COUNT:
            self.result = series.count()
