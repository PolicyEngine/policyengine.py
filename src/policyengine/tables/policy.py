from __future__ import annotations

from typing import Optional

from sqlmodel import SQLModel, Field


class PolicyTable(SQLModel, table=True):
    __tablename__ = "policies"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str | None = None
    description: str | None = None
    country: str | None = None

    # No ORM relationships in this minimal layer
