from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .model_version import ModelVersion
from .parameter import Parameter


class BaselineParameterValue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    parameter: Parameter
    model_version: ModelVersion
    value: float | int | str | bool | list | None = None
    start_date: datetime
    end_date: datetime | None = None
