from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, Index


class ParameterTable(SQLModel, table=True):
    __tablename__ = "parameters"
    __table_args__ = (
        UniqueConstraint("name", "country", name="uq_parameters_name_country"),
        Index("ix_parameters_name_country", "name", "country"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    parent_id: UUID | None = Field(default=None, foreign_key="parameters.id")
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    # Store the type name string (e.g. "float", "int")
    data_type: str
    country: str | None = None

    # No ORM relationship wiring


class ParameterValueTable(SQLModel, table=True):
    __tablename__ = "parameter_values"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    policy_id: UUID | None = Field(default=None, foreign_key="policies.id")
    dynamic_id: UUID | None = Field(default=None, foreign_key="dynamics.id")
    parameter_id: UUID = Field(foreign_key="parameters.id")
    model_version: str

    # Time period for this change
    start_date: datetime
    end_date: datetime | None = None

    # The actual change
    value: Any = Field(sa_type=JSON)
    country: str | None = None

    # No ORM relationship wiring
