from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class ReportElement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    type: Literal["chart", "markdown"]

    # Data source
    data_table: Optional[Literal["aggregates"]] = (
        None  # Which table to pull from
    )

    # Chart configuration
    chart_type: Optional[
        Literal["bar", "line", "scatter", "area", "pie", "histogram"]
    ] = None
    x_axis_variable: Optional[str] = None  # Column name from the table
    y_axis_variable: Optional[str] = None  # Column name from the table
    group_by: Optional[str] = None  # Column to group/split series by
    color_by: Optional[str] = None  # Column for color mapping
    size_by: Optional[str] = None  # Column for size mapping (bubble charts)

    # Markdown specific
    markdown_content: Optional[str] = None

    # Metadata
    report_id: Optional[str] = None
    user_id: Optional[str] = None
    position: Optional[int] = None
    visible: Optional[bool] = True
    custom_config: Optional[dict] = None  # Additional chart-specific config
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
