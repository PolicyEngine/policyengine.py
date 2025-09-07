from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field
from sqlalchemy import Index


class BaselineParameterValueTable(SQLModel, table=True):
    __tablename__ = "baseline_parameter_values"
    __table_args__ = (
        Index("ix_baseline_param_values_model_version", "model_version"),
        Index("ix_baseline_param_values_country", "country"),
        Index("ix_baseline_param_values_param_id", "parameter_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys - either policy or dynamic, not both
    policy_id: UUID | None = Field(default=None, foreign_key="policies.id")
    dynamic_id: UUID | None = Field(default=None, foreign_key="dynamics.id")
    
    # Parameter identification
    parameter_id: UUID = Field(foreign_key="parameters.id")
    model_version: str
    
    # Time period for this value
    start_date: datetime
    end_date: datetime | None = None
    
    # The actual value
    value: Any = Field(sa_type=JSON)
    country: str | None = None