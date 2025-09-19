from pydantic import BaseModel
from uuid import uuid4
from .model import Model


class Parameter(BaseModel):
    id: str = str(uuid4())
    description: str | None = None
    data_type: type | None = None
    model: Model | None = None
