from datetime import datetime

from pydantic import BaseModel

from .model_version import ModelVersion
from .parameter import Parameter


class BaselineParameterValue(BaseModel):
    parameter: Parameter
    model_version: ModelVersion
    value: float | int | str | bool | list | None = None
    start_date: datetime
    end_date: datetime | None = None
