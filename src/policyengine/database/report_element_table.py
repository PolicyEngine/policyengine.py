from sqlmodel import SQLModel, Field, JSON, Column
from policyengine.models.report_element import ReportElement
from typing import Optional
from datetime import datetime
from .link import TableLink
import uuid


class ReportElementTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "report_elements"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    label: str = Field(nullable=False)
    type: str = Field(nullable=False)  # "chart" or "markdown"

    # Data source
    data_table: Optional[str] = Field(default=None)  # "aggregates"

    # Chart configuration
    chart_type: Optional[str] = Field(default=None)  # "bar", "line", "scatter", "area", "pie"
    x_axis_variable: Optional[str] = Field(default=None)
    y_axis_variable: Optional[str] = Field(default=None)
    group_by: Optional[str] = Field(default=None)
    color_by: Optional[str] = Field(default=None)
    size_by: Optional[str] = Field(default=None)

    # Markdown specific
    markdown_content: Optional[str] = Field(default=None)

    # Metadata
    report_id: Optional[str] = Field(default=None, foreign_key="reports.id")
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    position: Optional[int] = Field(default=None)
    visible: Optional[bool] = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


report_element_table_link = TableLink(
    model_cls=ReportElement,
    table_cls=ReportElementTable,
)