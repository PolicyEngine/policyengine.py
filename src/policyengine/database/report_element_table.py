import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from policyengine.models.report_element import ReportElement

from .link import TableLink


class ReportElementTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "report_elements"

    id: str = Field(
        primary_key=True, default_factory=lambda: str(uuid.uuid4())
    )
    label: str = Field(nullable=False)
    type: str = Field(nullable=False)  # "chart" or "markdown"

    # Data source
    data_table: str | None = Field(default=None)  # "aggregates"

    # Chart configuration
    chart_type: str | None = Field(
        default=None
    )  # "bar", "line", "scatter", "area", "pie"
    x_axis_variable: str | None = Field(default=None)
    y_axis_variable: str | None = Field(default=None)
    group_by: str | None = Field(default=None)
    color_by: str | None = Field(default=None)
    size_by: str | None = Field(default=None)

    # Markdown specific
    markdown_content: str | None = Field(default=None)

    # Metadata
    report_id: str | None = Field(default=None, foreign_key="reports.id")
    user_id: str | None = Field(default=None, foreign_key="users.id")
    position: int | None = Field(default=None)
    visible: bool | None = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


report_element_table_link = TableLink(
    model_cls=ReportElement,
    table_cls=ReportElementTable,
)
