from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .parameter_value import ParameterValue


class Policy(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    parameter_values: list[ParameterValue] = []
    simulation_modifier: Callable | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
