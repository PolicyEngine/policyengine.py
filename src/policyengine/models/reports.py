"""Report models for PolicyEngine.

Includes `ReportElementDataItem`, `ReportElement`, and `Report` models.
"""

from typing import Optional, List

import pandas as pd
from pydantic import BaseModel

from .enums import OperationStatus
from microdf import MicroDataFrame
from enum import Enum


class ReportElement(BaseModel):
    """An element of a report.

    May include tables, charts, and other visualizations.
    """

    name: str | None = None
    description: str | None = None
    report: Optional["Report"] = None
    status: OperationStatus = OperationStatus.PENDING
    country: str | None = None

    def run(self) -> pd.DataFrame:
        raise NotImplementedError(
            "ReportElement run method must be implemented in "
            "country-specific subclass."
        )


class Report(BaseModel):
    """A report generated from a simulation."""

    name: str
    description: str | None = None
    elements: list[ReportElement] = []
    country: str | None = None


class AggregateType(str, Enum):
    MEAN = "mean"
    MEDIAN = "median"
    SUM = "sum"


class Aggregate(BaseModel):
    simulation: "Simulation"
    type: AggregateType
    variable: str
    value: str


class AggregateChangeReportElement(ReportElement):
    simulations: List["Simulation"] = []
    variables: List[str] = ["gov_balance"]
    aggregate_type: AggregateType = AggregateType.MEAN

    def run(self) -> pd.DataFrame:
        results = []
        for sim in self.simulations:
            for variable in self.variables:
                for table in sim.result.data.tables.values():
                    table = MicroDataFrame(table, weights="weight_value")
                    if variable in table.columns:
                        results.append(
                            dict(
                                simulation=sim,
                                variable=variable,
                                value={
                                    "mean": table[variable].mean(),
                                    "median": table[variable].median(),
                                    "sum": table[variable].sum(),
                                }[self.aggregate_type],
                            )
                        )
        return pd.DataFrame(results)
