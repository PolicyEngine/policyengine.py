from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class DynamicsTable(SQLModel, table=True):
    __tablename__ = "dynamics"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str | None = None
    parent_id: int | None = Field(default=None, foreign_key="dynamics.id")
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    country: str | None = None

    # No ORM relationship wiring
