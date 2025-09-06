from __future__ import annotations

from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


class PolicyTable(SQLModel, table=True):
    __tablename__ = "policies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str | None = None
    description: str | None = None
    country: str | None = None
    # Pickled simulation modifier function (if provided)
    simulation_modifier_bytes: bytes | None = None

    # No ORM relationships in this minimal layer
