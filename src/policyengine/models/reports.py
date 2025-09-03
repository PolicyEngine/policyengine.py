"""Report models for PolicyEngine.

Defines `ReportElement` base, `Report`, and tabular result models used by report elements.
"""

from __future__ import annotations

from typing import List, Optional, Any

import pandas as pd
from pydantic import BaseModel

from .enums import OperationStatus
from enum import Enum
from .report_item import ReportElementDataItem
from .aggregate import Aggregate, AggregateMetric


class ReportElement(BaseModel):
    """An element of a report composed in the web app.

    Subclasses represent concrete charts/tables. They implement `run()` and
    return a list of data records (BaseModels). Callers can convert that list
    to a DataFrame using the record class' helper.
    """

    name: str | None = None
    description: str | None = None
    report: Optional["Report"] = None
    status: OperationStatus = OperationStatus.PENDING
    country: str | None = None

    def run(self) -> list[BaseModel]:
        raise NotImplementedError(
            "ReportElement run method must be implemented by subclasses."
        )


class Report(BaseModel):
    """A report generated from a simulation."""

    name: str
    description: str | None = None
    elements: list[ReportElement] = []
    country: str | None = None


class ChangeByBaselineGroup(ReportElementDataItem):
    """Change in a variable using grouping defined by a baseline simulation.

    Captures total, relative, and per-household change within a specific group
    (e.g., baseline income decile).
    """

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    variable: str
    group_variable: str  # e.g., household_net_income_decile
    group_value: int | str
    entity_level: str = "household"
    time_period: int | str | None = None

    total_change: float
    relative_change: float
    average_change_per_entity: float

class VariableChangeGroupByQuantileGroup(ReportElementDataItem):
    """Winners/losers share by quantile grouping based on baseline.

    Computes percent and count of entities in a change bucket per quantile group.
    """

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    variable: str
    group_variable: str
    quantile_group: int
    quantile_group_count: int = 10
    change_lower_bound: float
    change_upper_bound: float
    change_bound_is_relative: bool = False
    fixed_entity_count_per_quantile_group: str = "household"
    percent_of_group_in_change_group: float
    entities_in_group_in_change_group: float

class VariableChangeGroupByVariableValue(ReportElementDataItem):
    """Change-group shares by exact group variable value (not quantiles)."""

    baseline_simulation: "Simulation"
    reform_simulation: "Simulation"
    variable: str
    group_variable: str
    group_variable_value: Any
    fixed_entity_count_per_quantile_group: str = "household"
    percent_of_group_in_change_group: float
    entities_in_group_in_change_group: float

    pass
