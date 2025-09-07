from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, Index


class VariableTable(SQLModel, table=True):
    __tablename__ = "variables"
    __table_args__ = (
        UniqueConstraint("name", "country", name="uq_variables_name_country"),
        Index("ix_variables_name_country", "name", "country"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str

    # Variable metadata
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    data_type: str
    entity: str
    definition_period: str | None = None
    country: str | None = None
