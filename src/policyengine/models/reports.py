"""Report models for PolicyEngine.

Defines `ReportElement` base, `Report`, and tabular result models used by report elements.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
from pydantic import BaseModel

from .enums import OperationStatus
from enum import Enum
from enum import Enum


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
        raise NotImplementedError("ReportElement is a base-only marker.")


class Report(BaseModel):
    """A report generated from a simulation."""

    name: str
    description: str | None = None
    elements: list[ReportElement] = []
    country: str | None = None


"""Data items live under `policyengine.models.report_items`.

This module only contains `Report` and `ReportElement` base classes.
"""
