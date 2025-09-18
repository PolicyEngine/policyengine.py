from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class ReportElement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    type: Literal["chart", "markdown"]

    # Data source
    data_table: Optional[Literal["aggregates", "simulations", "parameters", "models", "datasets"]] = None  # Which table to pull from
    filter_conditions: Optional[dict] = None  # Key-value pairs for filtering rows

    # Chart configuration
    chart_type: Optional[Literal["bar", "line", "scatter", "area", "pie", "histogram"]] = None
    x_axis_variable: Optional[str] = None  # Column name from the table
    y_axis_variable: Optional[str] = None  # Column name from the table
    group_by: Optional[str] = None  # Column to group/split series by
    color_by: Optional[str] = None  # Column for color mapping
    size_by: Optional[str] = None  # Column for size mapping (bubble charts)

    # Chart styling
    stacking_mode: Optional[Literal["none", "stack", "group", "percent", "overlay"]] = None
    line_style: Optional[Literal["solid", "dash", "dot", "dashdot"]] = None
    line_width: Optional[int] = None
    marker_size: Optional[int] = None
    opacity: Optional[float] = Field(None, ge=0, le=1)
    color_scheme: Optional[str] = None  # Named color palette
    show_data_labels: Optional[bool] = False

    # Layout
    height: Optional[int] = None  # Pixels
    width: Optional[int] = None  # Pixels or percentage
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    x_axis_type: Optional[Literal["linear", "log", "date", "category"]] = None
    y_axis_type: Optional[Literal["linear", "log", "date"]] = None
    x_axis_range: Optional[list] = None  # [min, max]
    y_axis_range: Optional[list] = None  # [min, max]
    show_legend: Optional[bool] = True
    legend_position: Optional[Literal["top", "bottom", "left", "right", "top-left", "top-right"]] = None
    show_grid: Optional[bool] = True

    # Interactivity
    hover_template: Optional[str] = None  # Custom hover text template
    clickable: Optional[bool] = False
    linked_element_ids: Optional[list[str]] = None  # For cross-filtering

    # Markdown specific
    markdown_content: Optional[str] = None
    template_variables: Optional[dict] = None  # For dynamic markdown

    # Metadata
    report_id: Optional[str] = None
    user_id: Optional[str] = None
    position: Optional[int] = None
    visible: Optional[bool] = True
    custom_config: Optional[dict] = None  # Additional chart-specific config
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None