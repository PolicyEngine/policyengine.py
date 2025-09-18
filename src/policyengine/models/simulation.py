from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
from .policy import Policy
from .dynamic import Dynamic
from .dataset import Dataset
from .model_version import ModelVersion
from .model import Model
from typing import Any


class Simulation(BaseModel):
    id: str = str(uuid4())
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

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
