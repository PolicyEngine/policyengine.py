from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, Index


class DynamicTable(SQLModel, table=True):
    __tablename__ = "dynamics"
    __table_args__ = (
        UniqueConstraint("name", "country", name="uq_dynamic_name_country"),
        Index("ix_dynamic_name_country", "name", "country"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str | None = None
    parent_id: UUID | None = Field(default=None, foreign_key="dynamics.id")
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    country: str | None = None
    # Pickled simulation modifier function (if provided)
    simulation_modifier_bytes: bytes | None = None

    # No ORM relationship wiring
