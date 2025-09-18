from pydantic import BaseModel
from .parameter import Parameter
from .model_version import ModelVersion
from datetime import datetime

class BaselineParameterValue(BaseModel):
    parameter: Parameter
    model_version: ModelVersion
    value: float | int | str | bool | list | None = None
    start_date: datetime
    end_date: datetime | None = None
