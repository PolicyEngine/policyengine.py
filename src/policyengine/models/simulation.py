from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .dataset import Dataset
from .dynamic import Dynamic
from .model import Model
from .model_version import ModelVersion
from .policy import Policy


class Simulation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    policy: Policy | None = None
    dynamic: Dynamic | None = None
    dataset: Dataset

    model: Model
    model_version: ModelVersion
    result: Any | None = None

    def run(self):
        self.result = self.model.simulation_function(
            dataset=self.dataset,
            policy=self.policy,
            dynamic=self.dynamic,
        )
        self.updated_at = datetime.now()
        return self.result
