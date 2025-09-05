"""Parameter models for PolicyEngine.

Defines `Parameter` and `ParameterValue` pydantic models.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from uuid import UUID

if TYPE_CHECKING:  # Import to satisfy type checkers without runtime cycles
    from .dynamic import Dynamic
    from .policy import Policy


class Parameter(BaseModel):
    """Policy parameter of the country package model."""

    id: UUID | None = None
    name: str
    parent: Parameter | None = None  # For hierarchical parameters

    # Parameter metadata
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    data_type: type | None  # "float", "int", "bool", "string"
    country: str | None = None


class ParameterValue(BaseModel):
    """Individual parameter value for some point in time."""

    id: UUID | None = None
    # Foreign keys
    policy: Policy | None = None
    dynamic: Dynamic | None = None
    parameter: Parameter
    model_version: str

    # Time period for this change
    start_date: datetime
    end_date: datetime | None = None

    # The actual change
    value: Any  # JSON-serializable value
    country: str | None = None
