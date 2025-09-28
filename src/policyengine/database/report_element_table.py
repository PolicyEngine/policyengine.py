import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel
from typing import TYPE_CHECKING

from policyengine.models.report_element import ReportElement

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


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

    @classmethod
    def convert_from_model(cls, model: ReportElement, database: "Database" = None) -> "ReportElementTable":
        """Convert a ReportElement instance to a ReportElementTable instance."""
        return cls(
            id=model.id,
            label=model.label,
            type=model.type,
            data_table=model.data_table,
            chart_type=model.chart_type,
            x_axis_variable=model.x_axis_variable,
            y_axis_variable=model.y_axis_variable,
            group_by=model.group_by,
            color_by=model.color_by,
            size_by=model.size_by,
            markdown_content=model.markdown_content,
            report_id=model.report_id,
            user_id=model.user_id,
            position=model.position,
            visible=model.visible,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def convert_to_model(self, database: "Database" = None) -> ReportElement:
        """Convert this ReportElementTable instance to a ReportElement instance."""
        return ReportElement(
            id=self.id,
            label=self.label,
            type=self.type,
            data_table=self.data_table,
            chart_type=self.chart_type,
            x_axis_variable=self.x_axis_variable,
            y_axis_variable=self.y_axis_variable,
            group_by=self.group_by,
            color_by=self.color_by,
            size_by=self.size_by,
            markdown_content=self.markdown_content,
            report_id=self.report_id,
            user_id=self.user_id,
            position=self.position,
            visible=self.visible,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


report_element_table_link = TableLink(
    model_cls=ReportElement,
    table_cls=ReportElementTable,
)
