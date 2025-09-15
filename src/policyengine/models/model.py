from pydantic import BaseModel
from datetime import datetime
from typing import Callable

class Model(BaseModel):
    id: str
    name: str
    description: str | None = None
    simulation_function: Callable


class ModelVersion(BaseModel):
    model: Model
    version: str
    description: str | None = None
    created_at: datetime = datetime.now()
