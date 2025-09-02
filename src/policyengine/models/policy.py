"""Policy model for PolicyEngine.

Contains the `Policy` pydantic model representing policy changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:  # Avoid runtime imports/cycles
    from .parameter import ParameterValue


class Policy(BaseModel):
    """Modifications made to baseline tax-benefit rules."""

    name: str | None = None

    # Metadata
    description: str | None = None

    parameter_values: list[ParameterValue] | None = None
    simulation_modifier: Any | None = None
    country: str | None = None
