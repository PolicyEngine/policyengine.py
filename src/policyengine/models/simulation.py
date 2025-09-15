from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
from .policy import Policy
from .dynamic import Dynamic
from .dataset import Dataset
from .model import ModelVersion
from typing import Any

class Simulation(BaseModel):
    id: str = str(uuid4())
    name: str
    description: str | None = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    policy: Policy | None = None
    dynamic: Dynamic | None = None
    dataset: Dataset

    model_version: ModelVersion | None = None
    result: Any | None = None