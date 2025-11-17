from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .parameter_value import ParameterValue


class Dynamic(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    parameter_values: list[ParameterValue] = []
    simulation_modifier: Callable | None = None
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

        return Dynamic(
            name=f"{self.name} + {other.name}",
            description=f"Combined dynamic: {self.name} and {other.name}",
            parameter_values=self.parameter_values + other.parameter_values,
            simulation_modifier=combined_modifier,
        )
