from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
from .parameter import Parameter


class ParameterValue(BaseModel):
    id: str = str(uuid4())
    parameter: Parameter
    value: float | int | str | bool | list | None = None
    start_date: datetime
    end_date: datetime | None = None
