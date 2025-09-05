"""Dynamics model for PolicyEngine.

Encapsulates modifications to baseline tax-benefit dynamics.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from uuid import UUID

if TYPE_CHECKING:  # For type checking only
    from .parameter import ParameterValue


class Dynamics(BaseModel):
    """Modifications made to baseline tax-benefit dynamics."""

    id: UUID | None = None
    name: str | None = None

    # Parent dynamics reference
    parent_dynamics: Dynamics | None = None

    # Metadata
    description: str | None = None
    created_at: datetime | None = None
    # Should automatically be current datetime
    updated_at: datetime | None = None

    parameter_values: list[ParameterValue] | None = None
    simulation_modifier: Any | None = None
    country: str | None = None
