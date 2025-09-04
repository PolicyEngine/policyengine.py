from __future__ import annotations

from enum import Enum

from policyengine.models.report_item import ReportElementDataItem


class AggregateMetric(str, Enum):
    MEAN = "mean"
    MEDIAN = "median"
    SUM = "sum"


class Aggregate(ReportElementDataItem):
    """Reusable aggregate record for a simulation and variable."""

    simulation: "Simulation"
    time_period: int | str | None = None
    variable: str
    entity_level: str = "person"
    filter_variable: str | None = None
    filter_variable_value: object | None = None
    filter_variable_min_value: float | None = None
    filter_variable_max_value: float | None = None
    metric: AggregateMetric
    value: float
