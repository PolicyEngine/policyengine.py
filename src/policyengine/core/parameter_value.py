from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .parameter import Parameter


class ParameterValue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    parameter: Parameter | None = None
    value: float | int | str | bool | list | None = None
    start_date: datetime
    end_date: datetime | None = None
