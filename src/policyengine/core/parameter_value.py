from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .parameter import Parameter


class ParameterValue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    parameter: "Parameter | None" = None
    value: float | int | str | bool | list | None = None
    start_date: datetime
    end_date: datetime | None = None
