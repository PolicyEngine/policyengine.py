from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


class DynamicTable(SQLModel, table=True):
    __tablename__ = "dynamic"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str | None = None
    parent_id: UUID | None = Field(default=None, foreign_key="dynamic.id")
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    country: str | None = None

    # No ORM relationship wiring
