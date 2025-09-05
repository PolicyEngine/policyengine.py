"""Dynamic model for PolicyEngine.

Encapsulates modifications to baseline tax-benefit dynamic.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from uuid import UUID

if TYPE_CHECKING:  # For type checking only
    from .parameter import ParameterValue


class Dynamic(BaseModel):
    """Modifications made to baseline tax-benefit dynamic."""

    id: UUID | None = None
    name: str | None = None

    # Parent dynamic reference
    parent_dynamic: Dynamic | None = None

    # Metadata
    description: str | None = None
    created_at: datetime | None = None
    # Should automatically be current datetime
    updated_at: datetime | None = None

    parameter_values: list[ParameterValue] | None = None
    simulation_modifier: Any | None = None
    country: str | None = None
