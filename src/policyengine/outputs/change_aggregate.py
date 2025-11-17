from enum import Enum
from typing import Any

from policyengine.core import Output, Simulation


class ChangeAggregateType(str, Enum):
    COUNT = "count"
    SUM = "sum"
    MEAN = "mean"


class ChangeAggregate(Output):
    baseline_simulation: Simulation
    reform_simulation: Simulation
    variable: str
    aggregate_type: ChangeAggregateType
    entity: str | None = None

    # Filter by absolute change
    change_geq: float | None = None  # Change >= value (e.g., gain >= 500)
    change_leq: float | None = None  # Change <= value (e.g., loss <= -500)
    change_eq: float | None = None  # Change == value

    # Filter by relative change (as decimal, e.g., 0.05 = 5%)
    relative_change_geq: float | None = None  # Relative change >= value
    relative_change_leq: float | None = None  # Relative change <= value
    relative_change_eq: float | None = None  # Relative change == value

    # Filter by another variable (e.g., only count people with age >= 30)
    filter_variable: str | None = None
    filter_variable_eq: Any | None = None
    filter_variable_leq: Any | None = None
    filter_variable_geq: Any | None = None
    filter_variable_describes_quantiles: bool = False

    # Convenient quantile specification (alternative to describes_quantiles)
    quantile: int | None = (
        None  # Number of quantiles (e.g., 10 for deciles, 5 for quintiles)
    )
    quantile_eq: int | None = None  # Exact quantile (e.g., 3 for 3rd decile)
    quantile_leq: int | None = (
        None  # Maximum quantile (e.g., 5 for bottom 5 deciles)
    )
    quantile_geq: int | None = (
        None  # Minimum quantile (e.g., 9 for top 2 deciles)
    )

    result: Any | None = None

    def run(self):
        # Convert quantile specification to describes_quantiles format
        if self.quantile is not None:
            self.filter_variable_describes_quantiles = True
            if self.quantile_eq is not None:
                # For a specific quantile, filter between (quantile-1)/n and quantile/n
                self.filter_variable_geq = (
                    self.quantile_eq - 1
                ) / self.quantile
                self.filter_variable_leq = self.quantile_eq / self.quantile
            elif self.quantile_leq is not None:
                self.filter_variable_leq = self.quantile_leq / self.quantile
            elif self.quantile_geq is not None:
                self.filter_variable_geq = (
                    self.quantile_geq - 1
                ) / self.quantile

        # Get variable object
        var_obj = next(
            v
            for v in self.baseline_simulation.tax_benefit_model_version.variables
            if v.name == self.variable
        )

        # Get the target entity data
        target_entity = self.entity or var_obj.entity
        baseline_data = getattr(
            self.baseline_simulation.output_dataset.data, target_entity
        )
        reform_data = getattr(
            self.reform_simulation.output_dataset.data, target_entity
        )

        # Map variable to target entity if needed
        if var_obj.entity != target_entity:
            baseline_mapped = (
                self.baseline_simulation.output_dataset.data.map_to_entity(
                    var_obj.entity, target_entity
                )
            )
            baseline_series = baseline_mapped[self.variable]

            reform_mapped = (
                self.reform_simulation.output_dataset.data.map_to_entity(
                    var_obj.entity, target_entity
                )
            )
            reform_series = reform_mapped[self.variable]
        else:
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
            filter_var_obj = next(
                v
                for v in self.baseline_simulation.tax_benefit_model_version.variables
                if v.name == self.filter_variable
            )

            if filter_var_obj.entity != target_entity:
                filter_mapped = (
                    self.baseline_simulation.output_dataset.data.map_to_entity(
                        filter_var_obj.entity, target_entity
                    )
                )
                filter_series = filter_mapped[self.filter_variable]
            else:
                filter_series = baseline_data[self.filter_variable]

            if self.filter_variable_describes_quantiles:
                if self.filter_variable_eq is not None:
                    threshold = filter_series.quantile(self.filter_variable_eq)
                    mask &= filter_series <= threshold
                if self.filter_variable_leq is not None:
                    threshold = filter_series.quantile(
                        self.filter_variable_leq
                    )
                    mask &= filter_series <= threshold
                if self.filter_variable_geq is not None:
                    threshold = filter_series.quantile(
                        self.filter_variable_geq
                    )
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
