from pydantic import BaseModel
from typing import Callable
from uuid import uuid4
from datetime import datetime
from .parameter_value import ParameterValue


class Policy(BaseModel):
    id: str = str(uuid4())
    name: str
    description: str | None = None
    parameter_values: list[ParameterValue] = []
    simulation_modifier: Callable | None = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
