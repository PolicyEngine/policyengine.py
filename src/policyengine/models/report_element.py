import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReportElement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    type: Literal["chart", "markdown"]

    # Data source
    data_table: Literal["aggregates"] | None = None  # Which table to pull from

    # Chart configuration
    chart_type: (
        Literal["bar", "line", "scatter", "area", "pie", "histogram"] | None
    ) = None
    x_axis_variable: str | None = None  # Column name from the table
    y_axis_variable: str | None = None  # Column name from the table
    group_by: str | None = None  # Column to group/split series by
    color_by: str | None = None  # Column for color mapping
    size_by: str | None = None  # Column for size mapping (bubble charts)

    # Markdown specific
    markdown_content: str | None = None

    # Metadata
    report_id: str | None = None
    user_id: str | None = None
    position: int | None = None
    visible: bool | None = True
    custom_config: dict | None = None  # Additional chart-specific config
    created_at: datetime | None = None
    updated_at: datetime | None = None
