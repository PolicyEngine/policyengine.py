from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field


class ParameterTable(SQLModel, table=True):
    __tablename__ = "parameters"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    parent_id: int | None = Field(default=None, foreign_key="parameters.id")
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    # Store the type name string (e.g. "float", "int")
    data_type: str
    country: str | None = None

    # No ORM relationship wiring


class ParameterValueTable(SQLModel, table=True):
    __tablename__ = "parameter_values"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign keys
    policy_id: int | None = Field(default=None, foreign_key="policies.id")
    dynamics_id: int | None = Field(default=None, foreign_key="dynamics.id")
    parameter_id: int = Field(foreign_key="parameters.id")
    model_version: str

    # Time period for this change
    start_date: datetime
    end_date: datetime | None = None

    # The actual change
    value: Any = Field(sa_type=JSON)
    country: str | None = None

    # No ORM relationship wiring
