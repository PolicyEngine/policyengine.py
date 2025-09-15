from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
from .model import Model

class Parameter(BaseModel):
    id: str = str(uuid4())
    description: str
    data_type: type
    model: Model | None = None

class ParameterValue(BaseModel):
    id: str = str(uuid4())
    parameter: Parameter
    value: float
    start_date: datetime
    end_date: datetime | None = None
