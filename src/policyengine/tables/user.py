from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


class UserTable(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    email: str

    # Relationships omitted for simplicity in this layer


class UserPolicyTable(SQLModel, table=True):
    __tablename__ = "user_policies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    policy_id: UUID = Field(foreign_key="policies.id")
    label: str | None = None
    description: str | None = None

    # No ORM relationship wiring


class UserSimulationTable(SQLModel, table=True):
    __tablename__ = "user_simulations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    simulation_id: UUID = Field(foreign_key="simulations.id")
    label: str | None = None
    description: str | None = None

    # No ORM relationship wiring


class UserReportTable(SQLModel, table=True):
    __tablename__ = "user_reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    report_id: UUID = Field(foreign_key="reports.id")
    label: str | None = None
    description: str | None = None

    # No ORM relationship wiring


class UserReportElementTable(SQLModel, table=True):
    __tablename__ = "user_report_elements"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    report_element_id: UUID = Field(foreign_key="report_elements.id")
    label: str | None = None
    description: str | None = None

    # No ORM relationship wiring
