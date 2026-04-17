from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .parameter import Parameter


class ParameterValue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    parameter: "Optional[Parameter]" = None
    value: Optional[Union[float, int, str, bool, list]] = None
    start_date: datetime
    end_date: Optional[datetime] = None
