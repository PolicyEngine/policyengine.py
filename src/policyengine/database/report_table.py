import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from policyengine.models.report import Report

from .link import TableLink


class ReportTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "reports"

    id: str = Field(
        primary_key=True, default_factory=lambda: str(uuid.uuid4())
    )
    label: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


report_table_link = TableLink(
    model_cls=Report,
    table_cls=ReportTable,
)
