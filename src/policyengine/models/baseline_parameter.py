"""Baseline parameter value model for PolicyEngine.

Defines `BaselineParameterValue` pydantic model for storing baseline tax-benefit parameter values.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from uuid import UUID

if TYPE_CHECKING:  # Import to satisfy type checkers without runtime cycles
    from .parameter import Parameter


class BaselineParameterValue(BaseModel):
    """Baseline parameter value for a specific parameter and model version."""

    id: UUID | None = None

    # Parameter identification
    parameter: Parameter
    model_version: str

    # Time period for this value
    start_date: datetime
    end_date: datetime | None = None

    # The actual value
    value: Any  # JSON-serializable value
    country: str | None = None
