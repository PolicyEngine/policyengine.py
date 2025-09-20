from sqlmodel import SQLModel, Field
from policyengine.models.report import Report
from typing import Optional
from datetime import datetime
from .link import TableLink
import uuid


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
