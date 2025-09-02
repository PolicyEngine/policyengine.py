"""Parameter models for PolicyEngine.

Defines `Parameter` and `ParameterValue` pydantic models.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:  # Import to satisfy type checkers without runtime cycles
    from .dynamics import Dynamics
    from .policy import Policy


class Parameter(BaseModel):
    """Policy parameter of the country package model."""

    name: str
    parent: Parameter | None = None  # For hierarchical parameters

    # Parameter metadata
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    data_type: type  # "float", "int", "bool", "string"
    country: str | None = None


class ParameterValue(BaseModel):
    """Individual parameter value for some point in time."""

    # Foreign keys
    policy: Policy | None = None
    dynamics: Dynamics | None = None
    parameter: Parameter
    model_version: str

    # Time period for this change
    start_date: datetime
    end_date: datetime | None = None

    # The actual change
    value: Any  # JSON-serializable value
    country: str | None = None
