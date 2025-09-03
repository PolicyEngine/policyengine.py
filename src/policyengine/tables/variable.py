from __future__ import annotations

from typing import Optional

from sqlmodel import SQLModel, Field


class VariableTable(SQLModel, table=True):
    __tablename__ = "variables"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    # Variable metadata
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    data_type: str
    entity: str
    definition_period: str | None = None
    country: str | None = None

