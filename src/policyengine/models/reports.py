"""Report models for PolicyEngine.

Includes `ReportElementDataItem`, `ReportElement`, and `Report` models.
"""

from typing import Optional

import pandas as pd
from pydantic import BaseModel

from .enums import OperationStatus


class ReportElementDataItem(BaseModel):
    report_element: "ReportElement"


class ReportElement(BaseModel):
    """An element of a report.

    May include tables, charts, and other visualizations.
    """

    name: str | None = None
    description: str | None = None
    data_items: list[ReportElementDataItem] = []
    report: Optional["Report"] = None
    status: OperationStatus = OperationStatus.PENDING
    country: str | None = None
    data_item_type: str | None = None

    @property
    def data(self) -> pd.DataFrame:
        # Get pydantic fields from reportelementdataitem-inheriting classes
        data: list[dict[str, object]] = []
        for item in self.data_items:
            non_inherited_fields = (
                type(item).model_fields.keys()
                - ReportElementDataItem.model_fields.keys()
            )
            data.append(
                {key: getattr(item, key) for key in non_inherited_fields}
            )
        return pd.DataFrame(data)

    def run(self):
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
