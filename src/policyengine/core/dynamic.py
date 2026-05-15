from collections.abc import Callable
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from .parameter_value import ParameterValue


class Dynamic(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    parameter_values: list[ParameterValue] = []
    simulation_modifier: Optional[Callable] = None
    affects_labor_supply_response: Optional[bool] = Field(
        default=None,
        description=(
            "Whether this dynamic should materialize labor-supply response "
            "outputs. None preserves conservative detection for unmarked "
            "simulation modifiers."
        ),
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def __add__(self, other: "Dynamic") -> "Dynamic":
        """Combine two dynamics by appending parameter values and chaining simulation modifiers."""
        if not isinstance(other, Dynamic):
            return NotImplemented

        # Combine simulation modifiers
        combined_modifier = None
        if (
            self.simulation_modifier is not None
            and other.simulation_modifier is not None
        ):

            def combined_modifier(sim):
                sim = self.simulation_modifier(sim)
                sim = other.simulation_modifier(sim)
                return sim

        elif self.simulation_modifier is not None:
            combined_modifier = self.simulation_modifier
        elif other.simulation_modifier is not None:
            combined_modifier = other.simulation_modifier

        affects_labor_supply_response = None
        if (
            self.affects_labor_supply_response is True
            or other.affects_labor_supply_response is True
        ):
            affects_labor_supply_response = True
        elif (
            self.affects_labor_supply_response is False
            and other.affects_labor_supply_response is False
        ):
            affects_labor_supply_response = False

        return Dynamic(
            name=f"{self.name} + {other.name}",
            description=f"Combined dynamic: {self.name} and {other.name}",
            parameter_values=self.parameter_values + other.parameter_values,
            simulation_modifier=combined_modifier,
            affects_labor_supply_response=affects_labor_supply_response,
        )
