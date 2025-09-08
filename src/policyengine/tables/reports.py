from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, Index

from policyengine.models.enums import OperationStatus


class ReportTable(SQLModel, table=True):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("name", "country", name="uq_reports_name_country"),
        Index("ix_reports_name_country", "name", "country"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    description: str | None = None
    country: str | None = None

    # No ORM relationship wiring


class ReportElementTable(SQLModel, table=True):
    __tablename__ = "report_elements"
    __table_args__ = (
        UniqueConstraint(
            "name", "country", name="uq_report_elements_name_country"
        ),
        Index("ix_report_elements_name_country", "name", "country"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str | None = None
    description: str | None = None
    report_id: UUID | None = Field(default=None, foreign_key="reports.id")
    status: OperationStatus = OperationStatus.PENDING
    country: str | None = None

    # No ORM relationship wiring
