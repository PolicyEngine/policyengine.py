from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field

from policyengine.models.enums import OperationStatus


class ReportTable(SQLModel, table=True):
    __tablename__ = "reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    description: str | None = None
    country: str | None = None

    # No ORM relationship wiring


class ReportElementTable(SQLModel, table=True):
    __tablename__ = "report_elements"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str | None = None
    description: str | None = None
    report_id: UUID | None = Field(default=None, foreign_key="reports.id")
    status: OperationStatus = OperationStatus.PENDING
    country: str | None = None

    # No ORM relationship wiring
