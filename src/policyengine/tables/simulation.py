from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field, Relationship

from policyengine.models.enums import OperationStatus


class SimulationTable(SQLModel, table=True):
    __tablename__ = "simulations"

    id: Optional[int] = Field(default=None, primary_key=True)

    dataset_id: int | None = Field(default=None, foreign_key="datasets.id")
    policy_id: int | None = Field(default=None, foreign_key="policies.id")
    dynamics_id: int | None = Field(default=None, foreign_key="dynamics.id")

    # Store result dataset as a dataset row to keep consistency
    result_dataset_id: int | None = Field(
        default=None, foreign_key="datasets.id"
    )
    model_version: str | None = None
    country: str

    status: OperationStatus = OperationStatus.PENDING
    created_at: datetime = datetime.now()
    completed_at: datetime | None = None

    # Relationships omitted to avoid ambiguity (two FKs to datasets)
