from pydantic import BaseModel, Field
from policyengine.core import *
from enum import Enum
from typing import Any


class AggregateType(str, Enum):
    SUM = "sum"
    MEAN = "mean"
    COUNT = "count"


class Aggregate(BaseModel):
    simulation: Simulation
    variable: str
    aggregate_type: AggregateType
    entity: str | None = None

    filter_variable: str | None = None
    filter_variable_eq: Any | None = None
    filter_variable_leq: Any | None = None
    filter_variable_geq: Any | None = None
    filter_variable_describes_quantiles: bool = False

    result: Any | None = None

    def run(self):
        # Get variable object
        var_obj = next(
            v
            for v in self.simulation.tax_benefit_model_version.variables
            if v.name == self.variable
        )

        # Get the target entity data
        target_entity = self.entity or var_obj.entity
        data = getattr(self.simulation.output_dataset.data, target_entity)

        # Map variable to target entity if needed
        if var_obj.entity != target_entity:
            mapped = self.simulation.output_dataset.data.map_to_entity(
                var_obj.entity, target_entity
            )
            series = mapped[self.variable]
        else:
            series = data[self.variable]

        # Apply filters
        if self.filter_variable is not None:
            filter_var_obj = next(
                v
                for v in self.simulation.tax_benefit_model_version.variables
                if v.name == self.filter_variable
            )

            if filter_var_obj.entity != target_entity:
                filter_mapped = (
                    self.simulation.output_dataset.data.map_to_entity(
                        filter_var_obj.entity, target_entity
                    )
                )
                filter_series = filter_mapped[self.filter_variable]
            else:
                filter_series = data[self.filter_variable]

            if self.filter_variable_describes_quantiles:
                if self.filter_variable_eq is not None:
                    threshold = filter_series.quantile(self.filter_variable_eq)
                    series = series[filter_series <= threshold]
                if self.filter_variable_leq is not None:
                    threshold = filter_series.quantile(
                        self.filter_variable_leq
                    )
                    series = series[filter_series <= threshold]
                if self.filter_variable_geq is not None:
                    threshold = filter_series.quantile(
                        self.filter_variable_geq
                    )
                    series = series[filter_series >= threshold]
            else:
                if self.filter_variable_eq is not None:
                    series = series[filter_series == self.filter_variable_eq]
                if self.filter_variable_leq is not None:
                    series = series[filter_series <= self.filter_variable_leq]
                if self.filter_variable_geq is not None:
                    series = series[filter_series >= self.filter_variable_geq]

        # Aggregate
        if self.aggregate_type == AggregateType.SUM:
            self.result = series.sum()
        elif self.aggregate_type == AggregateType.MEAN:
            self.result = series.mean()
        elif self.aggregate_type == AggregateType.COUNT:
            self.result = series.count()
