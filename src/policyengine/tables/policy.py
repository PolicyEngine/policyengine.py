from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


class PolicyTable(SQLModel, table=True):
    __tablename__ = "policies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str | None = None
    description: str | None = None
    country: str | None = None

    # No ORM relationships in this minimal layer
