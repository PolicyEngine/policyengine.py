from .base import ReportElementDataItem
from .aggregate import Aggregate, AggregateMetric
from .two_sim_change import (
    ChangeByBaselineGroup,
    VariableChangeGroupByQuantileGroup,
    VariableChangeGroupByVariableValue,
)

__all__ = [
    "ReportElementDataItem",
    "Aggregate",
    "AggregateMetric",
    "ChangeByBaselineGroup",
    "VariableChangeGroupByQuantileGroup",
    "VariableChangeGroupByVariableValue",
]

# Ensure Pydantic forward references are resolved when this package is imported
try:
    Aggregate.model_rebuild()
    ChangeByBaselineGroup.model_rebuild()
    VariableChangeGroupByQuantileGroup.model_rebuild()
    VariableChangeGroupByVariableValue.model_rebuild()
except Exception:
    pass
