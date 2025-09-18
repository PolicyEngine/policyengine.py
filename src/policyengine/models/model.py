from pydantic import BaseModel
from typing import Callable


class Model(BaseModel):
    id: str
    name: str
    description: str | None = None
    simulation_function: Callable
