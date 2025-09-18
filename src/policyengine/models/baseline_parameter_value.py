from pydantic import BaseModel
from .parameter import Parameter
from .model import Model
from datetime import datetime

class BaselineParameterValue(BaseModel):
    parameter: Parameter
    model: Model
    value: float | int | str | bool | list | None = None
    start_date: datetime
    end_date: datetime | None = None
