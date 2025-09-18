from sqlmodel import SQLModel, Field, JSON, Column
from policyengine.models.report_element import ReportElement
from typing import Optional, Literal
from datetime import datetime
from .link import TableLink
import uuid


class ReportElementTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "report_elements"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    label: str = Field(nullable=False)
    type: Literal["chart", "markdown"] = Field(nullable=False)

    # Data source
    data_table: Optional[Literal["aggregates", "simulations", "parameters", "models", "datasets"]] = Field(default=None)
    filter_conditions: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Chart configuration
    chart_type: Optional[Literal["bar", "line", "scatter", "area", "pie"]] = Field(default=None)
    x_axis_variable: Optional[str] = Field(default=None)
    y_axis_variable: Optional[str] = Field(default=None)
    group_by: Optional[str] = Field(default=None)
    color_by: Optional[str] = Field(default=None)
    size_by: Optional[str] = Field(default=None)

    # Chart styling
    stacking_mode: Optional[Literal["none", "stack", "group", "percent", "overlay"]] = Field(default=None)
    line_style: Optional[Literal["solid", "dash", "dot", "dashdot"]] = Field(default=None)
    line_width: Optional[int] = Field(default=None)
    marker_size: Optional[int] = Field(default=None)
    opacity: Optional[float] = Field(default=None)
    color_scheme: Optional[str] = Field(default=None)
    show_data_labels: Optional[bool] = Field(default=False)

    # Layout
    height: Optional[int] = Field(default=None)
    width: Optional[int] = Field(default=None)
    x_axis_label: Optional[str] = Field(default=None)
    y_axis_label: Optional[str] = Field(default=None)
    x_axis_type: Optional[Literal["linear", "log", "date", "category"]] = Field(default=None)
    y_axis_type: Optional[Literal["linear", "log", "date"]] = Field(default=None)
    x_axis_range: Optional[list] = Field(default=None, sa_column=Column(JSON))
    y_axis_range: Optional[list] = Field(default=None, sa_column=Column(JSON))
    show_legend: Optional[bool] = Field(default=True)
    legend_position: Optional[Literal["top", "bottom", "left", "right", "top-left", "top-right"]] = Field(default=None)
    show_grid: Optional[bool] = Field(default=True)

    # Interactivity
    hover_template: Optional[str] = Field(default=None)
    clickable: Optional[bool] = Field(default=False)
    linked_element_ids: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))

    # Markdown specific
    markdown_content: Optional[str] = Field(default=None)
    template_variables: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Metadata
    report_id: Optional[str] = Field(default=None, foreign_key="reports.id")
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    position: Optional[int] = Field(default=None)
    visible: Optional[bool] = Field(default=True)
    custom_config: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


report_element_table_link = TableLink(
    model_cls=ReportElement,
    table_cls=ReportElementTable,
)