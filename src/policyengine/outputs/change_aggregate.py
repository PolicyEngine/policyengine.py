from enum import Enum
from typing import Any, Optional

from policyengine.core import Output, Simulation
from policyengine.outputs.aggregate import (
    get_aggregate_variable,
    get_output_entity_data,
    require_output_column,
)


class ChangeAggregateType(str, Enum):
    COUNT = "count"
    SUM = "sum"
    MEAN = "mean"


class ChangeAggregate(Output):
    baseline_simulation: Simulation
    reform_simulation: Simulation
    variable: str
    aggregate_type: ChangeAggregateType
    entity: Optional[str] = None

    # Filter by absolute change
    change_geq: Optional[float] = None  # Change >= value (e.g., gain >= 500)
    change_leq: Optional[float] = None  # Change <= value (e.g., loss <= -500)
    change_eq: Optional[float] = None  # Change == value

    # Filter by relative change (as decimal, e.g., 0.05 = 5%)
    relative_change_geq: Optional[float] = None  # Relative change >= value
    relative_change_leq: Optional[float] = None  # Relative change <= value
    relative_change_eq: Optional[float] = None  # Relative change == value

    # Filter by another variable (e.g., only count people with age >= 30)
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
            self.baseline_simulation, self.variable, "ChangeAggregate.variable"
        )

        # Get the target entity data
        target_entity = self.entity or var_obj.entity
        baseline_data = get_output_entity_data(
            self.baseline_simulation,
            target_entity,
            "ChangeAggregate.baseline_entity",
        )
        reform_data = get_output_entity_data(
            self.reform_simulation,
            target_entity,
            "ChangeAggregate.reform_entity",
        )

        # Map variable to target entity if needed
        if var_obj.entity != target_entity:
            baseline_source_data = get_output_entity_data(
                self.baseline_simulation,
                var_obj.entity,
                "ChangeAggregate.variable",
            )
            reform_source_data = get_output_entity_data(
                self.reform_simulation,
                var_obj.entity,
                "ChangeAggregate.variable",
            )
            require_output_column(
                baseline_source_data,
                self.variable,
                var_obj.entity,
                self.baseline_simulation,
                "ChangeAggregate.variable",
            )
            require_output_column(
                reform_source_data,
                self.variable,
                var_obj.entity,
                self.reform_simulation,
                "ChangeAggregate.variable",
            )
            baseline_mapped = (
                self.baseline_simulation.output_dataset.data.map_to_entity(
                    var_obj.entity, target_entity, columns=[self.variable]
                )
            )
            baseline_series = baseline_mapped[self.variable]

            reform_mapped = self.reform_simulation.output_dataset.data.map_to_entity(
                var_obj.entity, target_entity, columns=[self.variable]
            )
            reform_series = reform_mapped[self.variable]
        else:
            require_output_column(
                baseline_data,
                self.variable,
                target_entity,
                self.baseline_simulation,
                "ChangeAggregate.variable",
            )
            require_output_column(
                reform_data,
                self.variable,
                target_entity,
                self.reform_simulation,
                "ChangeAggregate.variable",
            )
            baseline_series = baseline_data[self.variable]
            reform_series = reform_data[self.variable]

        # Calculate change (reform - baseline)
        change_series = reform_series - baseline_series

        # Calculate relative change (handling division by zero)
        # Where baseline is 0, relative change is undefined; we'll mask these out if relative filters are used
        import numpy as np

        with np.errstate(divide="ignore", invalid="ignore"):
            relative_change_series = change_series / baseline_series
            relative_change_series = relative_change_series.replace(
                [np.inf, -np.inf], np.nan
            )

        # Start with all rows
        mask = baseline_series.notna()

        # Apply absolute change filters
        if self.change_eq is not None:
            mask &= change_series == self.change_eq
        if self.change_leq is not None:
            mask &= change_series <= self.change_leq
        if self.change_geq is not None:
            mask &= change_series >= self.change_geq

        # Apply relative change filters
        if self.relative_change_eq is not None:
            mask &= relative_change_series == self.relative_change_eq
        if self.relative_change_leq is not None:
            mask &= relative_change_series <= self.relative_change_leq
        if self.relative_change_geq is not None:
            mask &= relative_change_series >= self.relative_change_geq

        # Apply filter_variable filters
        if self.filter_variable is not None:
            filter_var_obj = get_aggregate_variable(
                self.baseline_simulation,
                self.filter_variable,
                "ChangeAggregate.filter_variable",
            )

            if filter_var_obj.entity != target_entity:
                filter_source_data = get_output_entity_data(
                    self.baseline_simulation,
                    filter_var_obj.entity,
                    "ChangeAggregate.filter_variable",
                )
                require_output_column(
                    filter_source_data,
                    self.filter_variable,
                    filter_var_obj.entity,
                    self.baseline_simulation,
                    "ChangeAggregate.filter_variable",
                )
                filter_mapped = (
                    self.baseline_simulation.output_dataset.data.map_to_entity(
                        filter_var_obj.entity,
                        target_entity,
                        columns=[self.filter_variable],
                    )
                )
                filter_series = filter_mapped[self.filter_variable]
            else:
                require_output_column(
                    baseline_data,
                    self.filter_variable,
                    target_entity,
                    self.baseline_simulation,
                    "ChangeAggregate.filter_variable",
                )
                filter_series = baseline_data[self.filter_variable]

            if self.filter_variable_describes_quantiles:
                if self.filter_variable_eq is not None:
                    threshold = filter_series.quantile(self.filter_variable_eq)
                    mask &= filter_series <= threshold
                if self.filter_variable_leq is not None:
                    threshold = filter_series.quantile(self.filter_variable_leq)
                    mask &= filter_series <= threshold
                if self.filter_variable_geq is not None:
                    threshold = filter_series.quantile(self.filter_variable_geq)
                    mask &= filter_series >= threshold
            else:
                if self.filter_variable_eq is not None:
                    mask &= filter_series == self.filter_variable_eq
                if self.filter_variable_leq is not None:
                    mask &= filter_series <= self.filter_variable_leq
                if self.filter_variable_geq is not None:
                    mask &= filter_series >= self.filter_variable_geq

        # Apply mask to get filtered data
        filtered_change = change_series[mask]

        # Aggregate
        if self.aggregate_type == ChangeAggregateType.COUNT:
            self.result = filtered_change.count()
        elif self.aggregate_type == ChangeAggregateType.SUM:
            self.result = filtered_change.sum()
        elif self.aggregate_type == ChangeAggregateType.MEAN:
            self.result = filtered_change.mean()
